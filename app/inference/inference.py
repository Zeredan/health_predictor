"""
inference_server.py - Мини-сервер для инференса MedicalLSTM
Использует общий конфиг из core.model.config и существующие утилиты
"""

import torch
import torch.nn.functional as F
from flask import Flask, request, jsonify
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path
import sys
import logging
from datetime import datetime
import traceback
import argparse

# Добавляем пути для импорта
sys.path.append('.')
sys.path.append('./src')
sys.path.append('./core')

from core.model.medical_nn import MedicalLSTM
from core.model.config import get_model_config
from core.utils.handbooks.retrieve_handbooks import aggregate_all_vocabs
from core.utils.stats.age_stats import get_age_stats
from app.inference.collate_x import collate_inference

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class InferenceService:
    """Сервис для инференса модели"""
    
    def __init__(self, model_name: str = "model_best.pth", device: str = None):
        """
        Args:
            model_name: Имя файла модели (model_best.pth, model_last.pth, model_final.pth)
            device: Устройство для инференса (cuda/cpu). Если None, определяется автоматически
        """
        # Определяем устройство
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"🚀 Инициализация InferenceService на устройстве: {self.device}")
        
        # Определяем пути
        self.project_root = Path(__file__).parent.parent.parent
        self.handbooks_dir = self.project_root / "res" / "handbooks"
        self.model_dir = self.project_root / "res" / "model"
        self.datasets_dir = self.project_root / "res" / "datasets"
        
        # 1. Загружаем справочники (нужны для конфига и обратного преобразования)
        logger.info("📚 Загрузка справочников...")
        self.vocabs = aggregate_all_vocabs(str(self.handbooks_dir))
        logger.info(f"   Загружено {len(self.vocabs)} справочников")
        
        # 2. Получаем конфиг модели (уже содержит vocab_sizes из справочников)
        logger.info("⚙️  Загрузка конфига модели...")
        self.config = get_model_config()
        logger.info(f"   Конфиг загружен: mlp_hidden={self.config['mlp_hidden']}, "
                   f"lstm_hidden={self.config['lstm_hidden']}")
        
        # 3. Загружаем статистики нормализации
        logger.info("📊 Загрузка статистик нормализации...")
        self.normalization_stats = self._load_normalization_stats()
        
        # 4. Загружаем модель
        logger.info(f"🧠 Загрузка модели {model_name}...")
        self.model = self._load_model(model_name)
        self.model.eval()
        
        # 5. Создаем reverse mapping для обратного преобразования
        logger.info("🔄 Создание reverse mapping для справочников...")
        self.reverse_vocabs = self._create_reverse_mapping()
        
        logger.info("✅ InferenceService готов к работе")
    
    def _load_normalization_stats(self) -> Dict[str, Dict[str, float]]:
        """Загружает статистики нормализации из тренировочного датасета"""
        try:
            # Ищем тренировочный датасет
            train_dataset_path = self.datasets_dir / "train_dataset.tsv"
            
            if train_dataset_path.exists():
                # Используем существующую функцию из core.utils.stats
                age_mean, age_std, _ = get_age_stats(
                    str(train_dataset_path), 
                    sample_size=100000
                )
                
                stats = {
                    'age': {'mean': age_mean, 'std': age_std},
                    'sex': {'min': 0.0, 'max': 1.0},
                    'is_dead': {'min': 0.0, 'max': 1.0}
                }
                logger.info(f"   Возраст: mean={age_mean:.2f}, std={age_std:.2f}")
            else:
                # Дефолтные значения на случай отсутствия датасета
                logger.warning("   Тренировочный датасет не найден, используются дефолтные статистики")
                stats = {
                    'age': {'mean': 40.2, 'std': 21.0},
                    'sex': {'min': 0.0, 'max': 1.0},
                    'is_dead': {'min': 0.0, 'max': 1.0}
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"   Ошибка загрузки статистик: {e}")
            logger.warning("   Используются дефолтные статистики")
            return {
                'age': {'mean': 40.2, 'std': 21.0},
                'sex': {'min': 0.0, 'max': 1.0},
                'is_dead': {'min': 0.0, 'max': 1.0}
            }
    
    def _load_model(self, model_name: str) -> torch.nn.Module:
        """Загружает веса модели"""
        model_path = self.model_dir / model_name
        
        if not model_path.exists():
            # Пробуем другие варианты
            alternatives = ["model_best.pth", "model_last.pth", "model_final.pth"]
            for alt in alternatives:
                alt_path = self.model_dir / alt
                if alt_path.exists():
                    model_path = alt_path
                    logger.info(f"   Найдена альтернативная модель: {alt}")
                    break
            else:
                raise FileNotFoundError(
                    f"Модель не найдена в {self.model_dir}. "
                    f"Искали: {model_name}, {alternatives}"
                )
        
        # Создаем модель с конфигом
        model = MedicalLSTM(self.config).to(self.device)
        
        # Загружаем веса
        state_dict = torch.load(model_path, map_location=self.device)
        model.load_state_dict(state_dict)
        
        logger.info(f"   Модель загружена из: {model_path.name}")
        logger.info(f"   Параметров: {sum(p.numel() for p in model.parameters()):,}")
        
        return model
    
    def _create_reverse_mapping(self) -> Dict[str, Dict[int, str]]:
        """Создает обратные словари {индекс: код} для декодирования предсказаний"""
        reverse = {}
        
        for name, vocab in self.vocabs.items():
            # Инвертируем словарь
            reverse[name] = {idx: code for code, idx in vocab.items()}
            
        return reverse
    
    def _logits_to_probs(self, logits: torch.Tensor, temperature: float = 1.0) -> torch.Tensor:
        """Конвертирует логиты в вероятности"""
        with torch.no_grad():
            probs = F.softmax(logits / temperature, dim=-1)
            return probs
    
    def _denormalize_age(self, age_norm: torch.Tensor) -> float:
        """Обратная нормализация возраста"""
        mean = self.normalization_stats['age']['mean']
        std = self.normalization_stats['age']['std']
        age = age_norm * std + mean
        return float(age.item())
    
    def _denormalize_binary(self, value_norm: torch.Tensor, feature: str) -> int:
        """Обратная нормализация бинарных признаков (sex, is_dead)"""
        min_val = self.normalization_stats[feature]['min']
        max_val = self.normalization_stats[feature]['max']
        value = value_norm * (max_val - min_val) + min_val
        return int(round(float(value.item())))
    
    def _get_top_k_predictions(self, probs: torch.Tensor, reverse_vocab: Dict[int, str], 
                                k: int = 5, threshold: float = 0.01) -> List[Dict[str, Any]]:
        """Возвращает top-k предсказаний с вероятностями"""
        top_probs, top_indices = torch.topk(probs, min(k, probs.size(0)))
        
        predictions = []
        for prob, idx in zip(top_probs, top_indices):
            idx_val = int(idx.item())
            prob_val = float(prob.item())
            
            # Пропускаем PAD и UNK если вероятность ниже порога
            if idx_val <= 1 and prob_val < threshold:
                continue
                
            code = reverse_vocab.get(idx_val, f"<UNK_{idx_val}>")
            
            predictions.append({
                'code': code,
                'probability': prob_val,
                'index': idx_val
            })
        
        return predictions
    
    @torch.no_grad()
    def predict(self, patient_histories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Основной метод для предсказания
        
        Args:
            patient_histories: Список историй пациентов в формате Dataset
        
        Returns:
            Список предсказаний для каждого пациента
        """
        try:
            # 1. Подготавливаем батч через collate_inference
            batch = collate_inference(
                patient_histories,
                self.vocabs,
                self.normalization_stats
            )
            
            # 2. Перемещаем на устройство
            window = {}
            for key, value in batch['window'].items():
                if torch.is_tensor(value):
                    window[key] = value.to(self.device)
                else:
                    window[key] = value
            
            # 3. Инференс модели
            predictions = self.model(window)
            
            # 4. Обрабатываем результаты для каждого пациента
            results = []
            batch_size = len(patient_histories)
            
            for i in range(batch_size):
                patient_result = {
                    'patient_id': patient_histories[i].get('enp', i),
                    'predictions': {},
                    'probabilities': {},
                    'top_k_predictions': {}
                }
                
                # === РЕГРЕССИЯ ===
                if 'age' in predictions:
                    age_norm = predictions['age'][i]
                    patient_result['predictions']['age'] = self._denormalize_age(age_norm)
                
                if 'death_logits' in predictions:
                    death_logit = predictions['death_logits'][i]
                    death_prob = torch.sigmoid(death_logit).item()
                    patient_result['predictions']['is_dead'] = 1 if death_prob > 0.5 else 0
                    patient_result['probabilities']['death'] = death_prob
                
                # === ДИАГНОЗЫ (3 уровня) ===
                for level in ['diagnosis_letter', 'diagnosis_hierarchy', 'diagnosis_full']:
                    logits_key = f'{level}_logits'
                    if logits_key in predictions:
                        logits = predictions[logits_key][i]
                        probs = self._logits_to_probs(logits, temperature=0.7)
                        
                        pred_idx = int(probs.argmax().item())
                        pred_code = self.reverse_vocabs[level].get(pred_idx, f"<UNK_{pred_idx}>")
                        patient_result['predictions'][level] = pred_code
                        
                        patient_result['top_k_predictions'][level] = self._get_top_k_predictions(
                            probs, 
                            self.reverse_vocabs[level],
                            k=5
                        )
                
                # === УСЛУГИ (3 уровня) ===
                for level in ['service_letter', 'service_hierarchy', 'service_full']:
                    logits_key = f'{level}_logits'
                    if logits_key in predictions:
                        logits = predictions[logits_key][i]
                        probs = self._logits_to_probs(logits, temperature=0.8)
                        
                        pred_idx = int(probs.argmax().item())
                        pred_code = self.reverse_vocabs[level].get(pred_idx, f"<UNK_{pred_idx}>")
                        patient_result['predictions'][level] = pred_code
                        
                        patient_result['top_k_predictions'][level] = self._get_top_k_predictions(
                            probs, 
                            self.reverse_vocabs[level],
                            k=5
                        )
                
                # === ПРОСТЫЕ КАТЕГОРИИ ===
                simple_features = ['group', 'profile', 'result', 'type', 'form', 'season']
                for feat in simple_features:
                    logits_key = f'{feat}_logits'
                    if logits_key in predictions:
                        logits = predictions[logits_key][i]
                        
                        if feat == 'season':
                            # Для сезона просто argmax (это 0-3)
                            pred_idx = int(logits.argmax().item())
                            patient_result['predictions'][feat] = pred_idx
                        else:
                            pred_idx = int(logits.argmax().item())
                            pred_code = self.reverse_vocabs[feat].get(pred_idx, f"<UNK_{pred_idx}>")
                            patient_result['predictions'][feat] = pred_code
                            
                            # Для важных признаков добавляем вероятности
                            if feat in ['group', 'profile', 'result']:
                                probs = F.softmax(logits, dim=-1)
                                patient_result['top_k_predictions'][feat] = self._get_top_k_predictions(
                                    probs,
                                    self.reverse_vocabs[feat],
                                    k=3
                                )
                
                # Метаданные
                patient_result['metadata'] = {
                    'sequence_length': int(batch['window']['lengths'][i].item()),
                    'max_diags': batch['max_diags'],
                    'inference_time': datetime.now().isoformat()
                }
                
                results.append(patient_result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инференсе: {e}")
            logger.error(traceback.format_exc())
            raise


# Глобальный экземпляр сервиса
inference_service = None


@app.route('/predict', methods=['POST'])
def predict():
    """Эндпоинт для предсказаний"""
    try:
        if inference_service is None:
            return jsonify({'error': 'Service not initialized'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Извлекаем список историй
        if 'patients' in data:
            patient_histories = data['patients']
        elif isinstance(data, list):
            patient_histories = data
        else:
            patient_histories = [data]
        
        if not patient_histories:
            return jsonify({'error': 'Empty patient list'}), 400
        
        logger.info(f"📩 Получен запрос на {len(patient_histories)} пациентов")
        
        # Выполняем предсказание
        predictions = inference_service.predict(patient_histories)
        
        response = {
            'success': True,
            'predictions': predictions,
            'count': len(predictions),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Успешно обработано {len(predictions)} пациентов")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки запроса: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def initialize_service(model_name: str = "model_best.pth", device: str = None):
    """Инициализация сервиса при запуске"""
    global inference_service
    
    try:
        inference_service = InferenceService(model_name, device)
        logger.info(f"🚀 Сервис инициализирован с моделью: {model_name}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации сервиса: {e}")
        raise


if __name__ == '__main__':
    # Конфигурация сервера (можно менять прямо здесь)
    MODEL_NAME = "model_best.pth"  # или "model_last.pth", "model_final.pth"
    HOST = "0.0.0.0"
    PORT = 5000
    DEVICE = "cuda"  # Явно указываем CUDA
    
    print("\n" + "="*60)
    print("🏥 MEDICAL LSTM INFERENCE SERVER")
    print("="*60)
    print(f"Model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print("="*60)
    
    # Инициализируем сервис
    initialize_service(MODEL_NAME, DEVICE)
    
    # Запускаем сервер
    print(f"\n🌍 Сервер запущен на {HOST}:{PORT}")
    print(f"📡 Эндпоинты:")
    print(f"   POST /predict - предсказание")
    print(f"   GET  /health  - проверка состояния")
    print(f"   GET  /vocab_info - информация о справочниках")
    print("\n" + "="*60)
    
    app.run(host=HOST, port=PORT, debug=False)