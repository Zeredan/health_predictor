import pandas as pd
import numpy as np
from torch.utils.data import IterableDataset
import torch
from typing import List, Tuple, Dict, Any, Iterator, Optional
from pathlib import Path
from datetime import datetime
import time
import hashlib
import json


class PatientSequenceDataset(IterableDataset):
    """
    Dataset для работы с последовательностями случаев пациентов.
    Читает данные из TSV потоково, не загружая все в память.
    Генерирует окна с равномерным stride по обеим осям:
    [start:start+size] -> start+size, где size ∈ [min_len, max_len] с шагом window_stride
    """
    
    def __init__(
        self,
        tsv_path: str,
        min_sequence_length: int = 5,
        max_sequence_length: Optional[int] = None,
        window_stride: int = 1,
        chunk_size: int = 10000,
        presetted_windows_count: Optional[int] = None,
        presetted_patients_count: Optional[int] = None,
    ):
        self.tsv_path = tsv_path
        self.min_sequence_length = min_sequence_length
        self.max_sequence_length = max_sequence_length
        self.window_stride = window_stride
        self.chunk_size = chunk_size
        
        # Кэш в памяти
        self._total_windows_cache = presetted_windows_count
        self._total_patients_cache = presetted_patients_count
        
        # Проверяем существование файла
        self._validate_file()
        
    
    def _validate_file(self):
        """Проверяет существование файла и наличие необходимых колонок."""
        try:
            with open(self.tsv_path, 'r', encoding='utf-8') as f:
                self.columns = f.readline().strip().split('\t')
            print(f"✓ Файл найден: {self.tsv_path}")
            print(f"  Колонок в файле: {len(self.columns)}")
            print(f"  Первые 5 колонок: {self.columns[:5]}")
        except FileNotFoundError:
            print(f"✗ ОШИБКА: Файл не найден: {self.tsv_path}")
            raise
        
        self.expected_columns = [
            'ENP', 'SEX', 'CASE_START_DATE', 'AGE', 'DIAGNOSIS', 
            'SERVICE', 'GROUP', 'PROFILE', 'RESULT', 'TYPE', 'FORM', 'IS_DEAD'
        ]
        
        missing_cols = [col for col in self.expected_columns if col not in self.columns]
        
        if missing_cols:
            print(f"  ⚠ Предупреждение: Отсутствуют колонки: {missing_cols}")
        else:
            print("  ✓ Все ожидаемые колонки присутствуют")
        
        print()
    
    def _read_patient_data(self) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Генератор, читает TSV потоково и группирует по пациентам."""
        chunk_reader = pd.read_csv(
            self.tsv_path,
            sep='\t',
            chunksize=self.chunk_size,
            dtype={
                'ENP': str,
                'SEX': 'category',
                'AGE': float,
                'DIAGNOSIS': str,
                'SERVICE': str,
                'GROUP': 'category',
                'PROFILE': 'category',
                'RESULT': 'category',
                'TYPE': 'category',
                'FORM': 'category',
                'IS_DEAD': 'category'
            },
            parse_dates=['CASE_START_DATE'],
            dayfirst=True,
            encoding='utf-8'
        )
        
        current_patient = None
        patient_records = []
        
        for chunk in chunk_reader:
            chunk = chunk.sort_values(['ENP', 'CASE_START_DATE'])
            
            for _, row in chunk.iterrows():
                enp = str(row['ENP'])
                
                if current_patient is None:
                    current_patient = enp
                    patient_records.append(row)
                elif enp == current_patient:
                    patient_records.append(row)
                else:
                    if patient_records:
                        df_patient = pd.DataFrame(patient_records)
                        yield current_patient, df_patient
                    
                    current_patient = enp
                    patient_records = [row]
        
        if patient_records:
            df_patient = pd.DataFrame(patient_records)
            yield current_patient, df_patient
    
    def _process_diagnosis_string(self, diagnosis_str: str) -> List[str]:
        """Обрабатывает строку диагнозов."""
        if pd.isna(diagnosis_str) or diagnosis_str == '':
            return []
        diagnosis_str = str(diagnosis_str).strip()
        diagnoses = diagnosis_str.split()
        return [d.strip() for d in diagnoses if d.strip()]
    
    def _get_season_from_date(self, date) -> int:
        """Определяет сезон по дате."""
        if pd.isna(date):
            return 1
        
        if isinstance(date, str):
            try:
                date = datetime.strptime(date, '%d.%m.%Y')
            except ValueError:
                try:
                    date = pd.to_datetime(date, dayfirst=True, errors='coerce')
                    if pd.isna(date):
                        return 1
                except:
                    return 1
        
        month = date.month
        if month in [12, 1, 2]:
            return 2
        elif month in [3, 4, 5]:
            return 3
        elif month in [6, 7, 8]:
            return 4
        else:
            return 5
    
    def _count_windows_for_patient_analytic(self, n_cases: int) -> int:
        """
        АНАЛИТИЧЕСКИЙ подсчет количества окон для пациента.
        Формула для случая с равномерным stride по обеим осям.
        """
        if n_cases <= self.min_sequence_length:
            return 0
        
        # Определяем максимальную длину окна
        max_len = self.max_sequence_length if self.max_sequence_length else n_cases - 1
        max_len = min(max_len, n_cases - 1)
        
        # Количество возможных стартовых позиций
        max_start = n_cases - self.min_sequence_length - 1
        if max_start < 0:
            return 0
        
        n_starts = (max_start // self.window_stride) + 1
        
        total_windows = 0
        for start_idx in range(0, max_start + 1, self.window_stride):
            # Максимальный размер окна для этой стартовой позиции
            max_size_for_start = min(max_len, n_cases - start_idx - 1)
            
            if max_size_for_start < self.min_sequence_length:
                continue
            
            # Количество размеров окна для этой стартовой позиции
            n_sizes = ((max_size_for_start - self.min_sequence_length) // self.window_stride) + 1
            total_windows += n_sizes
        
        return total_windows
    
    def _generate_windows_for_patient(self, patient_df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.Series]]:
        """
        Генерирует окна с равномерным stride по обеим осям.
        Окна: [start:start+size] -> start+size, где size ∈ [min_len, max_len] с шагом window_stride
        """
        windows = []
        n_cases = len(patient_df)
        
        if n_cases <= self.min_sequence_length:
            return windows
        
        max_len = self.max_sequence_length if self.max_sequence_length else n_cases - 1
        max_len = min(max_len, n_cases - 1)
        
        # Перебираем стартовые позиции с шагом stride
        for start_idx in range(0, n_cases - self.min_sequence_length, self.window_stride):
            # Перебираем размеры окна с тем же stride
            for window_size in range(self.min_sequence_length, 
                                    min(max_len, n_cases - start_idx) + 1, 
                                    self.window_stride):
                
                end_idx = start_idx + window_size
                target_idx = end_idx
                
                if target_idx < n_cases:
                    window_df = patient_df.iloc[start_idx:end_idx].copy()
                    target_row = patient_df.iloc[target_idx].copy()
                    windows.append((window_df, target_row))
        
        return windows
    
    def count_total_windows_analytic(self, verbose: bool = True, force_recount: bool = False) -> int:
        """
        АНАЛИТИЧЕСКИЙ подсчет количества окон (быстрый, по формуле).
        Результат кэшируется и сохраняется на диск.
        
        Args:
            verbose: Выводить ли прогресс
            force_recount: Принудительно пересчитать даже если есть кэш
        """
        # Используем кэш если есть и не требуем пересчета
        if not force_recount and self._total_windows_cache is not None:
            if verbose:
                print(f"✓ Использую кэшированное значение: {self._total_windows_cache:,} окон")
            return self._total_windows_cache
        
        if verbose:
            print("=" * 70)
            print("АНАЛИТИЧЕСКИЙ ПОДСЧЕТ КОЛИЧЕСТВА ОКОН")
            print("=" * 70)
            print(f"Параметры:")
            print(f"  - min_sequence_length: {self.min_sequence_length}")
            print(f"  - max_sequence_length: {self.max_sequence_length or '∞'}")
            print(f"  - window_stride: {self.window_stride}")
            print(f"  - tsv_path: {self.tsv_path}")
            print("-" * 70)
            print("Начинаем быстрый аналитический подсчет...")
            print()
        
        total_windows = 0
        patient_count = 0
        start_time = time.time()
        
        for patient_idx, (enp, patient_df) in enumerate(self._read_patient_data()):
            patient_count += 1
            n_cases = len(patient_df)
            windows_for_patient = self._count_windows_for_patient_analytic(n_cases)
            total_windows += windows_for_patient
            
            if verbose and (patient_count % 1000 == 0 or patient_count < 10):
                print(f"  Пациентов: {patient_count:6d} | Окон: {total_windows:10,d} | "
                      f"Текущий: {n_cases:3d} случаев -> {windows_for_patient:4d} окон")
        
        elapsed = time.time() - start_time
        
        self._total_windows_cache = total_windows
        self._total_patients_cache = patient_count
        
        
        if verbose:
            print("-" * 70)
            print(f"ИТОГОВАЯ СТАТИСТИКА:")
            print(f"  Всего пациентов: {patient_count:,}")
            print(f"  Всего окон: {total_windows:,}")
            print(f"  Среднее окон на пациента: {total_windows/patient_count:.2f}")
            print(f"  Время подсчета: {elapsed:.2f} сек")
            print(f"  Скорость: {patient_count/elapsed:.0f} пациентов/сек")
            print("=" * 70)
            print()
        
        return total_windows
    
    def count_total_windows_actual(self, verbose: bool = True, max_samples: Optional[int] = None) -> int:
        """
        ФАКТИЧЕСКИЙ подсчет количества окон путем реальной итерации по датасету.
        Используется для верификации аналитического метода.
        
        Args:
            verbose: Выводить ли прогресс
            max_samples: Максимальное количество окон для подсчета
        """
        
        if verbose:
            print("=" * 70)
            print("ФАКТИЧЕСКИЙ ПОДСЧЕТ КОЛИЧЕСТВА ОКОН")
            print("=" * 70)
            print("Начинаем полную итерацию по датасету...")
            print("⚠  Это может занять значительное время!")
            print()
        
        start_time = time.time()
        count = 0
        
        for i, _ in enumerate(self):
            count += 1
            
            if max_samples is not None and count >= max_samples:
                break
            
            if verbose and count % 50000 == 0:
                elapsed = time.time() - start_time
                speed = count / elapsed if elapsed > 0 else 0
                print(f"  Обработано окон: {count:10,d} | Время: {elapsed:6.1f}с | "
                      f"Скорость: {speed:6.0f} окон/с")
        
        elapsed = time.time() - start_time
        
        if verbose:
            print("-" * 70)
            print(f"ИТОГОВАЯ СТАТИСТИКА:")
            print(f"  Всего окон: {count:,}")
            print(f"  Время подсчета: {elapsed:.2f} сек")
            print(f"  Скорость: {count/elapsed:.0f} окон/сек")
            print("=" * 70)
            print()
        
        return count
    
    def verify_window_count(self, sample_size: int = 100) -> bool:
        """
        ВЕРИФИКАЦИЯ: сравнивает аналитический и фактический подсчет на нескольких пациентах.
        """
        print("=" * 70)
        print("ВЕРИФИКАЦИЯ ПОДСЧЕТА ОКОН")
        print("=" * 70)
        print(f"Проверяем на {sample_size} пациентах...")
        print(f"Параметры: min_len={self.min_sequence_length}, "
              f"max_len={self.max_sequence_length}, stride={self.window_stride}")
        print()
        
        patient_generator = self._read_patient_data()
        matches = 0
        mismatches = []
        
        for patient_idx, (enp, patient_df) in enumerate(patient_generator):
            if patient_idx >= sample_size:
                break
            
            n_cases = len(patient_df)
            
            # Аналитический подсчет
            analytic_count = self._count_windows_for_patient_analytic(n_cases)
            
            # Фактический подсчет
            windows = self._generate_windows_for_patient(patient_df)
            actual_count = len(windows)
            
            if analytic_count == actual_count:
                matches += 1
            else:
                mismatches.append({
                    'enp': enp,
                    'n_cases': n_cases,
                    'analytic': analytic_count,
                    'actual': actual_count,
                    'diff': analytic_count - actual_count
                })
                print(f"  ⚠ НЕСОВПАДЕНИЕ: Пациент {enp[:8]}..., "
                      f"случаев={n_cases:3d}, "
                      f"аналитика={analytic_count:4d}, "
                      f"факт={actual_count:4d}")
            
            if (patient_idx + 1) % 20 == 0:
                print(f"  Проверено пациентов: {patient_idx + 1:3d}/{sample_size}, "
                      f"совпадений: {matches:3d}")
        
        print()
        print("-" * 70)
        print(f"РЕЗУЛЬТАТ ВЕРИФИКАЦИИ:")
        print(f"  Проверено пациентов: {sample_size}")
        print(f"  Совпадений: {matches} ({matches/sample_size*100:.1f}%)")
        
        if mismatches:
            print(f"  Несовпадений: {len(mismatches)}")
            print("\n  Примеры несовпадений:")
            for m in mismatches[:5]:
                print(f"    ENP={m['enp'][:8]}..., случаев={m['n_cases']:3d}: "
                      f"аналитика={m['analytic']:4d}, факт={m['actual']:4d}, "
                      f"разница={m['diff']:4d}")
        else:
            print(f"  ✅ ПОЛНОЕ СОВПАДЕНИЕ! Аналитический подсчет работает правильно")
        
        print("=" * 70)
        print()
        
        return len(mismatches) == 0
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Итератор по датасету."""
        patient_generator = self._read_patient_data()
        
        for patient_idx, (enp, patient_df) in enumerate(patient_generator):
            windows = self._generate_windows_for_patient(patient_df)
            
            for window_idx, (window_df, target_row) in enumerate(windows):
                window_seasons = [self._get_season_from_date(date) for date in window_df['CASE_START_DATE']]
                target_season = self._get_season_from_date(target_row['CASE_START_DATE'])
                
                window_data = {
                    'enp': enp,
                    'patient_idx': patient_idx,
                    'window_idx': window_idx,
                    
                    'window_sex': window_df['SEX'].values.tolist(),
                    'window_age': window_df['AGE'].values.tolist(),
                    'window_diagnosis': [self._process_diagnosis_string(d) for d in window_df['DIAGNOSIS'].values],
                    'window_service': window_df['SERVICE'].values.tolist(),
                    'window_group': window_df['GROUP'].values.tolist(),
                    'window_profile': window_df['PROFILE'].values.tolist(),
                    'window_result': window_df['RESULT'].values.tolist(),
                    'window_type': window_df['TYPE'].values.tolist(),
                    'window_form': window_df['FORM'].values.tolist(),
                    'window_is_dead': window_df['IS_DEAD'].values.tolist(),
                    'window_dates': window_df['CASE_START_DATE'].values.tolist(),
                    'window_season': window_seasons,
                    
                    'target_sex': target_row['SEX'],
                    'target_age': float(target_row['AGE']),
                    'target_diagnosis': self._process_diagnosis_string(target_row['DIAGNOSIS']),
                    'target_service': target_row['SERVICE'],
                    'target_group': target_row['GROUP'],
                    'target_profile': target_row['PROFILE'],
                    'target_result': target_row['RESULT'],
                    'target_type': target_row['TYPE'],
                    'target_form': target_row['FORM'],
                    'target_is_dead': target_row['IS_DEAD'],
                    'target_date': target_row['CASE_START_DATE'],
                    'target_season': target_season,
                }
                
                yield window_data
    
    def __len__(self) -> int:
        """
        Возвращает количество окон в датасете.
        Использует ленивое кэширование - вычисляется только один раз.
        """
        if self._total_windows_cache is None:
            # Тихий подсчет без вывода
            self._total_windows_cache = self.count_total_windows_analytic(
                verbose=False, 
                force_recount=False
            )
        return self._total_windows_cache
    
    def get_config(self) -> Dict[str, Any]:
        """Возвращает текущую конфигурацию датасета."""
        return {
            'tsv_path': str(self.tsv_path),
            'min_sequence_length': self.min_sequence_length,
            'max_sequence_length': self.max_sequence_length,
            'window_stride': self.window_stride,
            'total_windows': self._total_windows_cache,
            'total_patients': self._total_patients_cache,
        }


# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def calculate_batch_info(dataset: PatientSequenceDataset, 
                        batch_size: int, 
                        num_workers: int = 0,
                        drop_last: bool = False,
                        verify: bool = False) -> Dict[str, Any]:
    """
    Рассчитывает информацию о батчах.
    
    Args:
        dataset: Объект PatientSequenceDataset
        batch_size: Размер батча
        num_workers: Количество воркеров DataLoader
        drop_last: Отбрасывать ли последний неполный батч
        verify: Запустить ли верификацию подсчета
        
    Returns:
        Dict: Словарь с информацией о батчах
    """
    print("\n" + "="*70)
    print("РАСЧЕТ ПАРАМЕТРОВ DATALOADER")
    print("="*70)
    
    # Получаем общее количество окон (из кэша)
    total_windows = len(dataset)
    total_patients = dataset._total_patients_cache
    
    print(f"\n📊 ИНФОРМАЦИЯ О ДАТАСЕТЕ:")
    print(f"  Всего окон: {total_windows:,}")
    print(f"  Всего пациентов: {total_patients:,}")
    print(f"  Параметры: min_len={dataset.min_sequence_length}, "
          f"max_len={dataset.max_sequence_length}, stride={dataset.window_stride}")
    
    # Верификация если запрошена
    if verify:
        print("\n🔍 ВЕРИФИКАЦИЯ ПОДСЧЕТА:")
        dataset.verify_window_count(sample_size=100)
    
    # Расчет батчей
    if drop_last:
        n_batches = total_windows // batch_size
        last_batch_size = batch_size if total_windows % batch_size == 0 else 0
    else:
        n_batches = (total_windows + batch_size - 1) // batch_size
        last_batch_size = total_windows % batch_size
        if last_batch_size == 0:
            last_batch_size = batch_size
    
    info = {
        'total_windows': total_windows,
        'total_patients': total_patients,
        'batch_size': batch_size,
        'drop_last': drop_last,
        'num_batches': n_batches,
        'full_batches': total_windows // batch_size,
        'last_batch_size': last_batch_size,
        'steps_per_epoch': n_batches,
        'avg_windows_per_batch': total_windows / n_batches if n_batches > 0 else 0,
        'config': dataset.get_config(),
    }
    
    print(f"\n📈 ПАРАМЕТРЫ DATALOADER:")
    print(f"  Размер батча: {batch_size}")
    print(f"  Drop last: {drop_last}")
    print(f"  Количество батчей: {n_batches:,}")
    print(f"  Полных батчей: {info['full_batches']:,}")
    print(f"  Размер последнего батча: {last_batch_size}")
    print(f"  Шагов на эпоху: {n_batches:,}")
    print(f"  Среднее окон на батч: {info['avg_windows_per_batch']:.2f}")
    print("="*70 + "\n")
    
    return info


def quick_count_windows(dataset: PatientSequenceDataset, max_patients: int = 10) -> int:
    """
    Быстрый тестовый подсчет окон на нескольких пациентах.
    """
    print("\n" + "="*70)
    print("БЫСТРЫЙ ТЕСТОВЫЙ ПОДСЧЕТ")
    print("="*70)
    print(f"Параметры: min_len={dataset.min_sequence_length}, "
          f"max_len={dataset.max_sequence_length}, stride={dataset.window_stride}")
    print()
    
    total = 0
    patient_generator = dataset._read_patient_data()
    
    for i, (enp, patient_df) in enumerate(patient_generator):
        if i >= max_patients:
            break
        
        windows = dataset._generate_windows_for_patient(patient_df)
        count = len(windows)
        analytic = dataset._count_windows_for_patient_analytic(len(patient_df))
        total += count
        
        status = "✅" if count == analytic else "⚠"
        print(f"  {status} Пациент {i+1:2d}: {len(patient_df):3d} случаев -> "
              f"{count:4d} окон (аналитика: {analytic:4d})")
    
    print(f"\n  ИТОГО за {max_patients} пациентов: {total} окон")
    print(f"  В среднем: {total/max_patients:.1f} окон на пациента")
    print("="*70 + "\n")
    
    return total


# ============= ПРИМЕР ИСПОЛЬЗОВАНИЯ =============

if __name__ == "__main__":
    # Пример использования
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    
    
    # 1. Создаем датасет с кэшированием
    dataset = PatientSequenceDataset(
        tsv_path=project_root / "res" / "datasets" / "train_dataset.tsv",
        min_sequence_length=10,
        max_sequence_length=30,
        window_stride=5
    )
    
    # 2. Быстрый тест на 10 пациентах
    quick_count_windows(dataset, max_patients=10)
    
    # 3. Получаем общее количество окон (ленивое кэширование)
    print(f"📊 Всего окон в датасете: {len(dataset):,}")
    
    # 4. Расчет параметров DataLoader
    batch_info = calculate_batch_info(
        dataset=dataset,
        batch_size=128,
        num_workers=0,
        drop_last=False,
        verify=True  # Верификация на 100 пациентах
    )
    
    # 5. Конфиг для тренировки
    config = {
        'batch_size': 128,
        'steps_per_epoch': batch_info['steps_per_epoch'],
        'total_windows': batch_info['total_windows'],
        'num_batches': batch_info['num_batches'],
        'dataset_config': batch_info['config'],
    }
    
    print(f"\n🎯 КОНФИГ ДЛЯ ТРЕНИРОВКИ:")
    print(f"  batch_size: {config['batch_size']}")
    print(f"  steps_per_epoch: {config['steps_per_epoch']:,}")
    print(f"  total_windows: {config['total_windows']:,}")
    print(f"  num_batches: {config['num_batches']:,}")