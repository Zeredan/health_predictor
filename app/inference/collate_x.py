from typing import List, Dict, Any, Optional, Union
import torch
from torch.nn.utils.rnn import pad_sequence

def collate_inference(batch: List[Dict[str, Any]],
                      vocabs: Dict[str, Any],
                      normalization_stats: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, Any]:
    """
    Collate функция для инференса - обрабатывает только окна, без целевых значений.
    
    Args:
        batch: Список примеров от Dataset (только история, без target)
        vocabs: Агрегированные справочники
        normalization_stats: Статистики для нормализации числовых признаков.
            Формат: {'age': {'mean': float, 'std': float}, ...}
            Если None, используется нормализация по умолчанию (Z-score с mean=40.2, std=21.0)
    
    Returns:
        Словарь с нормализованными тензорами окон для предсказания
    """
    # Константы
    MAX_DIAGS_ALLOWED = 15  # Максимум диагнозов на случай
    
    # Значения нормализации по умолчанию
    default_stats = {
        'age': {'mean': 40.2, 'std': 21.0},
        'sex': {'min': 0.0, 'max': 1.0},
        'is_dead': {'min': 0.0, 'max': 1.0},
    }
    
    if normalization_stats is None:
        normalization_stats = default_stats
    else:
        # Объединяем с дефолтными значениями
        for key in default_stats:
            if key not in normalization_stats:
                normalization_stats[key] = default_stats[key]
    
    # 1. Сортируем по убыванию длины последовательности
    batch.sort(key=lambda x: len(x['window_age']), reverse=True)
    seq_lengths = [len(x['window_age']) for x in batch]
    batch_size = len(batch)
    max_seq_len = max(seq_lengths) if seq_lengths else 0
    
    # 2. Находим максимальное количество диагнозов в батче
    max_diags_in_batch = 0
    for example in batch:
        for case_diagnoses in example['window_diagnosis']:
            max_diags_in_batch = max(max_diags_in_batch, len(case_diagnoses))
    
    # 3. Ограничиваем если слишком много
    if max_diags_in_batch > MAX_DIAGS_ALLOWED:
        print(f"⚠ В батче найдены случаи с {max_diags_in_batch} диагнозами. Обрезаем до {MAX_DIAGS_ALLOWED}")
        max_diags_in_batch = MAX_DIAGS_ALLOWED
    
    # Инициализируем структуры для окна
    window_data = {
        # Числовые признаки (будут нормализованы)
        'age': [],
        'sex': [],
        'is_dead': [],
        
        # Категориальные признаки
        'season': [],
        
        # Диагнозы (будут тензоры [B, S, max_diags])
        'diagnosis_letter': [],
        'diagnosis_hierarchy': [],
        'diagnosis_full': [],
        'diagnosis_mask': [],
        
        # Услуги
        'service_letter': [],
        'service_hierarchy': [],
        'service_full': [],
        
        # Остальные категориальные
        'group': [],
        'profile': [],
        'result': [],
        'type': [],
        'form': [],
        
        # Метаданные
        'lengths': torch.tensor(seq_lengths, dtype=torch.long),
        
        # Дополнительная информация для идентификации примеров (если есть)
        'enps': [x.get('enp', idx) for idx, x in enumerate(batch)],  # сохраняем ID если есть
    }
    
    # 4. Обрабатываем каждый пример
    for example in batch:
        seq_len = len(example['window_age'])
        
        # НОРМАЛИЗАЦИЯ числовых признаков окна
        age_stats = normalization_stats['age']
        sex_stats = normalization_stats['sex']
        is_dead_stats = normalization_stats['is_dead']
        
        # Возраст: Z-score нормализация
        window_age_norm = [(a - age_stats['mean']) / age_stats['std'] for a in example['window_age']]
        window_data['age'].append(torch.tensor(window_age_norm, dtype=torch.float32))
        
        # Пол: Min-max нормализация
        window_sex_float = [float(s) for s in example['window_sex']]
        window_sex_norm = [(s - sex_stats['min']) / (sex_stats['max'] - sex_stats['min']) 
                          for s in window_sex_float]
        window_data['sex'].append(torch.tensor(window_sex_norm, dtype=torch.float32))
        
        # Is_dead: Min-max нормализация
        window_is_dead_float = [float(d) for d in example['window_is_dead']]
        window_is_dead_norm = [(d - is_dead_stats['min']) / (is_dead_stats['max'] - is_dead_stats['min'])
                              for d in window_is_dead_float]
        window_data['is_dead'].append(torch.tensor(window_is_dead_norm, dtype=torch.float32))
        
        # Сезон: категориальный признак
        window_data['season'].append(torch.tensor(example['window_season'], dtype=torch.long))
        
        # Диагнозы: создаем тензоры [seq_len, max_diags]
        diag_letter_seq = []
        diag_hierarchy_seq = []
        diag_full_seq = []
        diag_mask_seq = []
        
        for case_diagnoses in example['window_diagnosis']:
            num_diags = len(case_diagnoses)
            
            # Кодируем реальные диагнозы
            case_letter = []
            case_hierarchy = []
            case_full = []
            
            for diag in case_diagnoses[:max_diags_in_batch]:  # обрезаем если нужно
                case_letter.append(vocabs['diagnosis_letter'].get(diag, 1))
                case_hierarchy.append(vocabs['diagnosis_hierarchy'].get(diag, 1))
                case_full.append(vocabs['diagnosis_full'].get(diag, 1))
            
            # Дополняем PAD если нужно
            if num_diags < max_diags_in_batch:
                pad_count = max_diags_in_batch - num_diags
                case_letter.extend([0] * pad_count)      # PAD = 0
                case_hierarchy.extend([0] * pad_count)
                case_full.extend([0] * pad_count)
            
            # Маска: 1 для реальных диагнозов, 0 для PAD
            case_mask = [1] * min(num_diags, max_diags_in_batch) + \
                       [0] * max(0, max_diags_in_batch - num_diags)
            
            diag_letter_seq.append(case_letter)
            diag_hierarchy_seq.append(case_hierarchy)
            diag_full_seq.append(case_full)
            diag_mask_seq.append(case_mask)
        
        # Преобразуем в тензоры
        window_data['diagnosis_letter'].append(torch.tensor(diag_letter_seq, dtype=torch.long))
        window_data['diagnosis_hierarchy'].append(torch.tensor(diag_hierarchy_seq, dtype=torch.long))
        window_data['diagnosis_full'].append(torch.tensor(diag_full_seq, dtype=torch.long))
        window_data['diagnosis_mask'].append(torch.tensor(diag_mask_seq, dtype=torch.float32))
        
        # Услуги (одна услуга на случай)
        service_letter_seq = []
        service_hierarchy_seq = []
        service_full_seq = []
        
        for service in example['window_service']:
            service_letter_seq.append(vocabs['service_letter'].get(service, 1))
            service_hierarchy_seq.append(vocabs['service_hierarchy'].get(service, 1))
            service_full_seq.append(vocabs['service_full'].get(service, 1))
        
        window_data['service_letter'].append(torch.tensor(service_letter_seq, dtype=torch.long))
        window_data['service_hierarchy'].append(torch.tensor(service_hierarchy_seq, dtype=torch.long))
        window_data['service_full'].append(torch.tensor(service_full_seq, dtype=torch.long))
        
        # Категориальные признаки
        for cat_name in ['group', 'profile', 'result', 'type', 'form']:
            key = f'window_{cat_name}'
            coded = [vocabs[cat_name].get(str(val), 1) for val in example[key]]
            window_data[cat_name].append(torch.tensor(coded, dtype=torch.long))
    
    # 5. Делаем паддинг последовательностей (по оси S)
    def pad_batch(sequences, padding_value=0):
        if not sequences:  # пустой батч
            return torch.tensor([])
        return pad_sequence(sequences, batch_first=True, padding_value=padding_value)
    
    # Обрабатываем окно
    processed_window = {}
    
    # Числовые признаки (уже нормализованы)
    for key in ['age', 'sex', 'is_dead']:
        padded = pad_batch(window_data[key], padding_value=0.0)
        processed_window[key] = padded.unsqueeze(-1) if padded.dim() == 2 else padded
    
    # Категориальные признаки
    processed_window['season'] = pad_batch(window_data['season'], padding_value=0)
    
    # Диагнозы (уже имеют размер [seq_len, max_diags], нужно только по оси S)
    for key in ['diagnosis_letter', 'diagnosis_hierarchy', 'diagnosis_full', 'diagnosis_mask']:
        processed_window[key] = pad_batch(window_data[key], padding_value=0)
    
    # Услуги
    for key in ['service_letter', 'service_hierarchy', 'service_full']:
        processed_window[key] = pad_batch(window_data[key], padding_value=0)
    
    # Остальные категориальные
    for cat_name in ['group', 'profile', 'result', 'type', 'form']:
        processed_window[cat_name] = pad_batch(window_data[cat_name], padding_value=0)
    
    processed_window['lengths'] = window_data['lengths']
    
    # 6. Формируем результат
    result = {
        'window': processed_window,
        'batch_size': batch_size,
        'max_seq_len': max_seq_len,
        'max_diags': max_diags_in_batch,
        'normalization_stats': normalization_stats,
        'metadata': {
            'seq_lengths': seq_lengths,
            'max_diags': max_diags_in_batch,
            'enps': window_data['enps'],  # сохраняем для идентификации результатов
        }
    }
    
    return result