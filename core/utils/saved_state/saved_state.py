import torch
import pickle
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import json
import logging

logger = logging.getLogger(__name__)


def save_training_state(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    epoch: int,
    history: Dict[str, list],
    best_val_loss: float,
    model_name: str = "model"
):
    """
    Сохраняет полное состояние обучения с поддержкой GradScaler.
    
    Args:
        model: Модель PyTorch
        optimizer: Оптимизатор
        scaler: GradScaler для AMP
        epoch: Текущая эпоха
        history: История обучения
        best_val_loss: Лучшая ошибка на валидации
        model_name: Имя модели (для имени файла)
    """
    try:
        # Определяем пути
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        model_dir = project_root / "res" / "model"
        train_state_dir = project_root / "res" / "train_state"
        
        # Создаем директории если их нет
        model_dir.mkdir(parents=True, exist_ok=True)
        train_state_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Сохраняем модель
        model_path = model_dir / f"{model_name}.pth"
        torch.save(model.state_dict(), model_path)
        logger.info(f"Модель сохранена: {model_path}")
        
        # 2. Сохраняем состояние обучения (включая scaler)
        checkpoint = {
            'epoch': epoch,
            'optimizer_state_dict': optimizer.state_dict(),
            'scaler_state_dict': scaler.state_dict(),  # ВАЖНО: сохраняем состояние scaler
            'history': history,
            'best_val_loss': best_val_loss,
            'model_class': model.__class__.__name__,
            'amp_enabled': True,  # Флаг использования AMP
        }
        
        # Сохраняем pickle
        checkpoint_path = train_state_dir / f"{model_name}_checkpoint.pkl"
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(checkpoint, f)
        
        # Сохраняем JSON с метаданными
        json_checkpoint = {
            'epoch': epoch,
            'best_val_loss': best_val_loss,
            'model_class': model.__class__.__name__,
            'history_lengths': {k: len(v) for k, v in history.items()},
            'scaler_state': {
                'scale': float(scaler.get_scale()),  # Текущий коэффициент масштабирования
                'growth_factor': scaler._growth_factor,  # Доступ к внутренним параметрам
                'backoff_factor': scaler._backoff_factor,
                'growth_interval': scaler._growth_interval,
            },
            'amp_enabled': True,
            'saved_at': str(Path(__file__).stat().st_mtime),  # Временная метка
        }
        
        json_path = train_state_dir / f"{model_name}_checkpoint.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_checkpoint, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Состояние обучения сохранено:")
        logger.info(f"  - Эпоха: {epoch}")
        logger.info(f"  - Лучшая val_loss: {best_val_loss:.6f}")
        logger.info(f"  - AMP Scale: {json_checkpoint['scaler_state']['scale']:.1f}")
        logger.info(f"  - История: {json_checkpoint['history_lengths']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояния: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def load_training_state(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: Optional[torch.amp.GradScaler] = None,  # Теперь опционально
    model_name: str = "model",
    device: str = 'cpu'
) -> Tuple[bool, Optional[int], Optional[Dict[str, list]], Optional[float]]:
    """
    Загружает полное состояние обучения с поддержкой GradScaler.
    
    Args:
        model: Модель PyTorch
        optimizer: Оптимизатор
        scaler: GradScaler для AMP (опционально)
        model_name: Имя модели
        device: Устройство для загрузки
    
    Returns:
        Tuple[success, epoch, history, best_val_loss]
    """
    try:
        # Определяем пути
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        model_dir = project_root / "res" / "model"
        train_state_dir = project_root / "res" / "train_state"
        
        model_path = model_dir / f"{model_name}.pth"
        checkpoint_path = train_state_dir / f"{model_name}_checkpoint.pkl"
        
        # Проверяем существование файлов
        if not model_path.exists():
            logger.warning(f"Файл модели не найден: {model_path}")
            return False, None, None, None
        
        if not checkpoint_path.exists():
            logger.warning(f"Файл состояния не найден: {checkpoint_path}")
            return False, None, None, None
        
        # 1. Загружаем модель
        model.load_state_dict(torch.load(model_path, map_location=device))
        logger.info(f"Модель загружена: {model_path}")
        
        # 2. Загружаем состояние обучения
        with open(checkpoint_path, 'rb') as f:
            checkpoint = pickle.load(f)
        
        # Восстанавливаем состояние оптимизатора
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        # ВАЖНО: Восстанавливаем состояние scaler, если он предоставлен
        if scaler is not None and 'scaler_state_dict' in checkpoint:
            try:
                scaler.load_state_dict(checkpoint['scaler_state_dict'])
                logger.info(f"  - Scaler восстановлен, scale={scaler.get_scale():.1f}")
            except Exception as e:
                logger.warning(f"Не удалось восстановить scaler: {e}")
                logger.warning("  Будет использован новый scaler с начальным scale")
        
        epoch = checkpoint['epoch']
        history = checkpoint['history']
        best_val_loss = checkpoint['best_val_loss']
        
        logger.info(f"Состояние обучения загружено:")
        logger.info(f"  - Эпоха: {epoch}")
        logger.info(f"  - Лучшая val_loss: {best_val_loss:.6f}")
        logger.info(f"  - История: { {k: len(v) for k, v in history.items()} }")
        
        return True, epoch, history, best_val_loss
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке состояния: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None, None, None


def get_available_checkpoints() -> Dict[str, Dict[str, Any]]:
    """Возвращает информацию о доступных чекпоинтах с поддержкой AMP."""
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        train_state_dir = project_root / "res" / "train_state"
        model_dir = project_root / "res" / "model"
        
        if not train_state_dir.exists():
            return {}
        
        checkpoints_info = {}
        
        for json_file in train_state_dir.glob("*_checkpoint.json"):
            model_name = json_file.name.replace("_checkpoint.json", "")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                model_path = model_dir / f"{model_name}.pth"
                checkpoint_path = train_state_dir / f"{model_name}_checkpoint.pkl"
                
                if model_path.exists() and checkpoint_path.exists():
                    checkpoint_info = {
                        'epoch': info['epoch'],
                        'best_val_loss': info['best_val_loss'],
                        'history_lengths': info['history_lengths'],
                        'model_class': info.get('model_class', 'Unknown'),
                        'model_path': model_path,
                        'checkpoint_path': checkpoint_path,
                        'json_path': json_file,
                    }
                    
                    # Добавляем информацию о AMP если есть
                    if 'scaler_state' in info:
                        checkpoint_info['amp_enabled'] = info.get('amp_enabled', False)
                        checkpoint_info['scaler_scale'] = info['scaler_state']['scale']
                    else:
                        checkpoint_info['amp_enabled'] = False
                        checkpoint_info['scaler_scale'] = None
                    
                    checkpoints_info[model_name] = checkpoint_info
                    
            except Exception as e:
                logger.warning(f"Не удалось прочитать {json_file}: {e}")
        
        logger.info(f"Найдено чекпоинтов: {len(checkpoints_info)}")
        for name, info in checkpoints_info.items():
            amp_info = f", AMP scale: {info['scaler_scale']:.1f}" if info['scaler_scale'] else ", без AMP"
            logger.info(f"  {name}: эпоха {info['epoch']}, val_loss {info['best_val_loss']:.6f}{amp_info}")
        
        return checkpoints_info
        
    except Exception as e:
        logger.error(f"Ошибка при поиске чекпоинтов: {e}")
        return {}


def save_emergency_backup(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    epoch: int,
    loss: float,
    model_name: str = "model"
):
    """
    Аварийное сохранение состояния (например, при переполнении градиентов).
    """
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        backup_dir = project_root / "res" / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_name = f"{model_name}_emergency_epoch_{epoch}"
        
        checkpoint = {
            'epoch': epoch,
            'loss': loss,
            'optimizer_state_dict': optimizer.state_dict(),
            'scaler_state_dict': scaler.state_dict(),
            'model_state_dict': model.state_dict(),
            'timestamp': str(Path(__file__).stat().st_mtime),
        }
        
        backup_path = backup_dir / f"{backup_name}.pkl"
        with open(backup_path, 'wb') as f:
            pickle.dump(checkpoint, f)
        
        logger.warning(f"⚠ Аварийное сохранение: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка аварийного сохранения: {e}")
        return False


def clear_training_state(model_name: str = "model") -> bool:
    """Удаляет сохраненное состояние."""
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        model_dir = project_root / "res" / "model"
        train_state_dir = project_root / "res" / "train_state"
        
        files_to_remove = [
            model_dir / f"{model_name}.pth",
            train_state_dir / f"{model_name}_checkpoint.pkl",
            train_state_dir / f"{model_name}_checkpoint.json",
        ]
        
        removed = []
        for file_path in files_to_remove:
            if file_path.exists():
                file_path.unlink()
                removed.append(file_path.name)
        
        if removed:
            logger.info(f"Удалены файлы: {removed}")
            return True
        else:
            logger.warning(f"Файлы для модели '{model_name}' не найдены")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при удалении состояния: {e}")
        return False


# Пример использования в тренировочном цикле
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("ТЕСТ ФУНКЦИЙ СОХРАНЕНИЯ/ЗАГРУЗКИ С GRADSCALER")
    print("=" * 60)
    
    # Тестовая модель
    class SimpleModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layer = torch.nn.Linear(10, 1)
        
        def forward(self, x):
            return self.layer(x)
    
    # 1. СОЗДАЕМ МОДЕЛЬ И SCALER
    print("\n1. СОЗДАНИЕ МОДЕЛИ И SCALER:")
    
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scaler = torch.amp.GradScaler('cuda')  # Создаем scaler
    
    print(f"  ✓ Scaler создан, начальный scale: {scaler.get_scale()}")
    
    # 2. СОХРАНЯЕМ СОСТОЯНИЕ
    print("\n2. СОХРАНЕНИЕ СОСТОЯНИЯ:")
    
    test_history = {
        'train_loss': [0.5, 0.4, 0.3],
        'val_loss': [0.6, 0.5, 0.4],
    }
    
    success = save_training_state(
        model=model,
        optimizer=optimizer,
        scaler=scaler,
        epoch=10,
        history=test_history,
        best_val_loss=0.35,
        model_name="test_model_amp"
    )
    
    if success:
        print("  ✓ Состояние с GradScaler сохранено")
        
        # 3. ЗАГРУЖАЕМ СОСТОЯНИЕ
        print("\n3. ЗАГРУЗКА СОСТОЯНИЯ:")
        
        new_model = SimpleModel()
        new_optimizer = torch.optim.Adam(new_model.parameters(), lr=0.001)
        new_scaler = torch.amp.GradScaler('cuda')  # Новый scaler
        
        print(f"  Новый scaler до загрузки: scale={new_scaler.get_scale()}")
        
        load_success, epoch, history, best_loss = load_training_state(
            model=new_model,
            optimizer=new_optimizer,
            scaler=new_scaler,  # Передаем scaler для восстановления
            model_name="test_model_amp"
        )
        
        if load_success:
            print(f"\n  ✓ Состояние загружено:")
            print(f"     Эпоха: {epoch}")
            print(f"     Лучший val loss: {best_loss}")
            print(f"     Scaler после загрузки: scale={new_scaler.get_scale()}")
        
        # 4. ПРОВЕРЯЕМ ДОСТУПНЫЕ ЧЕКПОИНТЫ
        print("\n4. ДОСТУПНЫЕ ЧЕКПОИНТЫ:")
        checkpoints = get_available_checkpoints()
        
        # 5. ОЧИСТКА (раскомментировать для удаления тестовых файлов)
        # print("\n5. ОЧИСТКА:")
        # clear_success = clear_training_state("test_model_amp")
        # if clear_success:
        #     print("  ✓ Тестовые файлы удалены")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)