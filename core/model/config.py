"""
config.py - Базовый конфиг модели MedicalLSTM
Содержит только гиперпараметры модели, без тренировочных параметров
"""

from typing import Dict, Any
from core.utils.handbooks.retrieve_handbooks import aggregate_all_vocabs
from pathlib import Path


def get_model_config() -> Dict[str, Any]:
    """
    Возвращает конфигурацию модели MedicalLSTM.
    
    Args:
        handbooks_dir: Путь к директории со справочниками.
                      Если None, используется стандартный путь.
    
    Returns:
        Dict с конфигурацией модели
    """
    # 1. Базовые гиперпараметры модели
    config = {
        # Размерности эмбеддингов для всех признаков
        'embedding_dims': {
            # Простые категориальные признаки
            'group': 50,
            'profile': 30,
            'result': 20,
            'type': 30,
            'form': 25,
            'season': 10,
            
            # Диагнозы (3 уровня детализации)
            'diagnosis_letter': 20,      # Буква/раздел (например, "I")
            'diagnosis_hierarchy': 100,   # Иерархия (например, "I10")
            'diagnosis_full': 200,        # Полный код с подкодами
            
            # Услуги (3 уровня детализации)
            'service_letter': 20,         # Тип услуги
            'service_hierarchy': 100,      # Иерархия услуги
            'service_full': 150            # Полный код услуги
        },
        
        # Размеры MLP и LSTM
        'mlp_hidden': 256,      # Размер скрытого слоя MLP
        'lstm_hidden': 128,      # Размер скрытого состояния LSTM
        'dropout': 0.3,          # Dropout rate
        
        # Дополнительные настройки
        'use_layer_norm': True,   # Использовать LayerNorm
    }
    
    # 2. Загружаем справочники
    try:
        vocabs = aggregate_all_vocabs()
        
        # 3. Добавляем размеры словарей
        vocab_sizes = {k: len(v) for k, v in vocabs.items()}
        # Сезон - специальный случай (его нет в справочниках)
        vocab_sizes["season"] = 6  # 4 сезона
        
        config['vocab_sizes'] = vocab_sizes
        
        # Для отладки - выводим информацию
        print("\n📊 Model Config:")
        print(f"   - Embedding dims: {config['embedding_dims']}")
        print(f"   - MLP hidden: {config['mlp_hidden']}")
        print(f"   - LSTM hidden: {config['lstm_hidden']}")
        print(f"   - Dropout: {config['dropout']}")
        print(f"\n📚 Vocabulary sizes:")
        for name, size in sorted(vocab_sizes.items()):
            print(f"   - {name:25}: {size:5} tokens")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not load vocabularies: {e}")
        print("   Using default vocabulary sizes (will cause errors if not set later)")
        # Заглушки на случай ошибки
        config['vocab_sizes'] = {
            'group': 100, 'profile': 100, 'result': 100, 
            'type': 100, 'form': 100, 'season': 4,
            'diagnosis_letter': 100, 'diagnosis_hierarchy': 1000, 
            'diagnosis_full': 5000,
            'service_letter': 100, 'service_hierarchy': 500, 
            'service_full': 2000
        }
    
    return config


# Для тестирования
if __name__ == "__main__":
    print("="*50)
    print("Testing Model Config")
    print("="*50)
    
    project_root = Path(__file__).parent.parent.parent

    config = get_model_config()
    
    print("\n✅ Config created successfully")
    print("="*50)