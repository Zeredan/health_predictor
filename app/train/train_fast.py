"""
train.py - Тренировочный пайплайн для MedicalLSTM
С исправлениями для AMP и FP16 стабильности
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
import json
from pathlib import Path
import sys
from datetime import datetime
import time
import os
from typing import Dict, List, Tuple, Any, Optional

from app.train.dataset import PatientSequenceDataset
from app.train.collate_x_y import collate_train
from core.model.medical_nn import MedicalLSTM
from core.model.config import get_model_config
from core.model.multi_task_loss import SimpleMultiTaskLoss
from core.utils.handbooks.retrieve_handbooks import aggregate_all_vocabs
from core.utils.stats.age_stats import get_age_stats
from core.utils.saved_state.saved_state import save_training_state, load_training_state, save_epoch_metrics


# Настраиваем окружение
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
os.environ['TORCH_CUDNN_V8_API_ENABLED'] = '1'

# ВАЖНО: Отключаем TF32 для стабильности (опционально)
# os.environ['TORCH_ALLOW_TF32_CUBLAS_OVERRIDE'] = '0'

sys.path.append('.')
sys.path.append('./src')
sys.path.append('./core')


class FastCollate:
    """Быстрый collate wrapper с поддержкой pickle"""
    def __init__(self, vocabs, normalization_stats):
        self.vocabs = vocabs
        self.normalization_stats = normalization_stats
    
    def __call__(self, batch):
        return collate_train(batch, self.vocabs, self.normalization_stats)
    
    def __getstate__(self):
        return self.__dict__.copy()
    
    def __setstate__(self, state):
        self.__dict__.update(state)


def initialize_config():
    """Инициализация конфигурации"""
    
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    
    base_config = get_model_config()
    
    # 2. Добавляем тренировочные параметры
    config = {
        **base_config,  # все гиперпараметры модели + vocab_sizes
        
        # Пути
        'res_dir': project_root / "res",
        'datasets_dir': project_root / "res" / "datasets",
        'handbooks_dir': project_root / "res" / "handbooks",
        'model_dir': project_root / "res" / "model",
        'train_state_dir': project_root / "res" / "train_state",
        
        # Имена файлов
        'train_dataset': "train_dataset.tsv",
        'val_dataset': "validation_dataset.tsv",
        'test_dataset': "test_dataset.tsv",
        
        # Размеры данных
        'max_seq_len': 30,
        'max_diags': 15,  # не используется напрямую
        'min_seq_len': 10,
        
        # Гиперпараметры тренировки
        'batch_size': 128,
        'learning_rate': 0.001,
        'weight_decay': 1e-5,
        'num_epochs': 100,
        'patience': 10,
        
        # Веса для loss функций
        'loss_weights': {
            'age': 0.05,
            'death': 0.1,
            'diagnosis_letter': 0.02,
            'diagnosis_hierarchy': 0.02,
            'diagnosis_full': 0.02,
            'service_letter': 0.02,
            'service_hierarchy': 0.02,
            'service_full': 0.02,
            'group': 0.05,
            'profile': 0.05,
            'result': 0.08,
            'type': 0.05,
            'form': 0.05,
            'season': 0.05
        },
        
        # Устройство
        'device': torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        
        # Параметры DataLoader
        'use_amp': True,
        'num_workers': 0,
        'pin_memory': True,
        
        # Параметры для FP16 стабильности
        'amp_dtype': torch.float16,
        'grad_scaler_init': 2.0 ** 16,
        'grad_scaler_growth_interval': 2000,
        'clip_grad_norm': 1.0,
        
        # Логирование
        'log_interval': 50,
        'save_interval': 5,
    }
    
    return config


def compute_metrics_fast(predictions: Dict[str, torch.Tensor], 
                        targets: Dict[str, torch.Tensor]) -> Dict[str, float]:
    """Расширенное вычисление метрик"""
    metrics = {}
    
    # Возраст - MAE, MSE, R2
    if 'age' in predictions and 'age' in targets:
        with torch.no_grad():
            age_pred = predictions['age'].squeeze(-1)
            age_true = targets['age'].squeeze(-1)
            
            mae = torch.abs(age_pred - age_true).mean().item()
            mse = ((age_pred - age_true) ** 2).mean().item()
            
            ss_res = ((age_true - age_pred) ** 2).sum().item()
            ss_tot = ((age_true - age_true.mean()) ** 2).sum().item()
            r2 = 1 - ss_res / (ss_tot + 1e-10)
            
            metrics['age_mae'] = mae
            metrics['age_mse'] = mse
            metrics['age_r2'] = r2
    
    # Смерть - Precision, Recall, F1, Accuracy, Specificity
    if 'death_logits' in predictions and 'is_dead' in targets:
        with torch.no_grad():
            death_probs = torch.sigmoid(predictions['death_logits'].float())
            death_pred = (death_probs > 0.5).int()
            death_true = targets['is_dead'].int()
            
            tp = ((death_pred == 1) & (death_true == 1)).sum().item()
            tn = ((death_pred == 0) & (death_true == 0)).sum().item()
            fp = ((death_pred == 1) & (death_true == 0)).sum().item()
            fn = ((death_pred == 0) & (death_true == 1)).sum().item()
            
            precision = tp / (tp + fp + 1e-10)
            recall = tp / (tp + fn + 1e-10)
            specificity = tn / (tn + fp + 1e-10)
            accuracy = (tp + tn) / (tp + tn + fp + fn + 1e-10)
            f1 = 2 * precision * recall / (precision + recall + 1e-10)
            
            metrics['death_precision'] = precision
            metrics['death_recall'] = recall
            metrics['death_specificity'] = specificity
            metrics['death_accuracy'] = accuracy
            metrics['death_f1'] = f1
    
    # Accuracy и Weighted Recall для ключевых признаков
    key_features = ['group', 'profile', 'result', 'diagnosis_full', 'service_full']
    for feat in key_features:
        logits_key = f'{feat}_logits'
        if logits_key in predictions and feat in targets:
            with torch.no_grad():
                preds = predictions[logits_key].float().argmax(dim=-1)
                trues = targets[feat]
                mask = trues != 0
                
                if mask.any():
                    acc = (preds[mask] == trues[mask]).float().mean().item()
                    metrics[f'{feat}_acc'] = acc
    
    # Top-3 accuracy для диагнозов
    if 'diagnosis_full_logits' in predictions and 'diagnosis_full' in targets:
        with torch.no_grad():
            logits = predictions['diagnosis_full_logits'].float()
            trues = targets['diagnosis_full']
            mask = trues != 0
            
            if mask.any():
                top3_pred = torch.topk(logits, k=min(3, logits.size(-1)), dim=-1).indices
                trues_masked = trues[mask]
                top3_matches = torch.stack([(top3_pred[mask] == t).any(dim=-1) for t in trues_masked]).any(dim=0)
                top3_acc = top3_matches.float().mean().item()
                metrics['diagnosis_full_top3_acc'] = top3_acc
    
    return metrics


def train_epoch(model, loader, optimizer, loss_fn, device, config, epoch, scaler):
    """Одна эпоха тренировки с исправленным AMP"""
    model.train()
    total_loss = 0.0
    epoch_start_time = time.time()
    batch_times = []
    
    for batch_idx, batch in enumerate(loader):
        batch_start = time.time()
        
        # Перемещаем данные на устройство
        window = {k: v.to(device, non_blocking=True) 
                 if torch.is_tensor(v) else v for k, v in batch['window'].items()}
        target = {k: v.to(device, non_blocking=True) 
                 if torch.is_tensor(v) else v for k, v in batch['target'].items()}
        
        optimizer.zero_grad(set_to_none=True)
        
        # ИСПРАВЛЕНО: Новый API AMP
        with torch.amp.autocast('cuda', dtype=config['amp_dtype'], enabled=config['use_amp']):
            predictions = model(window)
            loss, loss_dict = loss_fn(predictions, target)
        
        # ИСПРАВЛЕНО: Scaler backward
        scaler.scale(loss).backward()
        
        # ИСПРАВЛЕНО: Unscale перед clip
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=config['clip_grad_norm'])
        
        scaler.step(optimizer)
        scaler.update()
        
        total_loss += loss.item()
        
        batch_time = time.time() - batch_start
        batch_times.append(batch_time)
        
        # Логирование
        if (batch_idx + 1) % config['log_interval'] == 0:
            avg_batch_time = np.mean(batch_times[-config['log_interval']:])
            print(f"  Batch {batch_idx + 1:4d}/{len(loader)} | "
                  f"Loss: {loss.item():.4f} | "
                  f"Time: {batch_time:.3f}s | "
                  f"Avg: {avg_batch_time:.3f}s | "
                  f"Scale: {scaler.get_scale():.1f}")  # Показываем scale для отладки
        #if (batch_idx > 100):
        #    break
    
    epoch_time = time.time() - epoch_start_time
    avg_loss = total_loss / len(loader)
    
    print(f"\n  Epoch {epoch} completed: {epoch_time:.1f}s, Avg Loss: {avg_loss:.4f}")
    
    return avg_loss

@torch.no_grad()
def validate_epoch(model, loader, loss_fn, device, config, epoch):
    model.eval()
    total_loss = 0.0
    all_metrics = []
    
    val_start_time = time.time()
    
    for batch_idx, batch in enumerate(loader):
        window = {k: v.to(device, non_blocking=True) 
                 if torch.is_tensor(v) else v for k, v in batch['window'].items()}
        target = {k: v.to(device, non_blocking=True) 
                 if torch.is_tensor(v) else v for k, v in batch['target'].items()}
        
        with torch.amp.autocast('cuda', dtype=config['amp_dtype'], enabled=config['use_amp']):
            predictions = model(window)
            loss, _ = loss_fn(predictions, target)
        
        total_loss += loss.item()
        
        metrics = compute_metrics_fast(predictions, target)
        all_metrics.append(metrics)
        
        if (batch_idx + 1) % (len(loader) // 4) == 0:
        #if (batch_idx + 1) % (101 // 4) == 0:
            print(f"  Val batch {batch_idx + 1:4d}/{len(loader)} | Loss: {loss.item():.4f}")
            #print(f"  Val batch {batch_idx + 1:4d}/{101} | Loss: {loss.item():.4f}")
        #if (batch_idx > 100):
        #    break
    
    val_time = time.time() - val_start_time
    
    epoch_metrics = {}
    if all_metrics:
        for key in all_metrics[0].keys():
            values = [m[key] for m in all_metrics if key in m]
            epoch_metrics[key] = np.mean(values) if values else 0.0
    
    epoch_metrics['loss'] = total_loss / len(loader)
    
    print(f"  Validation completed: {val_time:.1f}s, Avg Loss: {epoch_metrics['loss']:.4f}")
    
    return epoch_metrics


def print_epoch_summary(epoch: int, 
                       train_loss: float,
                       val_metrics: Dict[str, float],
                       is_best: bool = False,
                       epoch_time: float = 0):
    """Краткая сводка по эпохе"""
    print("\n" + "="*70)
    print(f"EPOCH {epoch:03d} SUMMARY | Time: {epoch_time:.1f}s")
    print("="*70)
    
    print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_metrics.get('loss', 0):.4f}")
    
    if 'age_mae' in val_metrics:
        print(f"Age MAE: {val_metrics['age_mae']:.4f}")
    if 'death_recall' in val_metrics:
        print(f"Death Recall: {val_metrics['death_recall']:.4f} | F1: {val_metrics.get('death_f1', 0):.4f}")
    
    acc_metrics = []
    for feat in ['group', 'profile', 'result', 'diagnosis_full', 'service_full']:
        key = f'{feat}_acc'
        if key in val_metrics:
            acc_metrics.append(f"{feat}: {val_metrics[key]:.3f}")
    
    if acc_metrics:
        print("Acc: " + " | ".join(acc_metrics))
    
    if is_best:
        print(f"⭐ NEW BEST! Val Loss: {val_metrics.get('loss', 0):.4f}")
    
    print("="*70 + "\n")

def main():
    print("="*70)
    print("MEDICAL LSTM TRAINING")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    config = initialize_config()
    device = config['device']
    
    print(f"\nDevice: {device}")
    print(f"Batch size: {config['batch_size']}")
    print(f"AMP: {config['use_amp']} (dtype: {config['amp_dtype']})")
    print(f"Log interval: every {config['log_interval']} batches")
    
    config['model_dir'].mkdir(exist_ok=True, parents=True)
    config['train_state_dir'].mkdir(exist_ok=True, parents=True)
    
    metrics_dir = config['train_state_dir'] / "metrics"
    metrics_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n[1] Loading handbooks...")
    vocabs = aggregate_all_vocabs(str(config['handbooks_dir']))
    print(f"    Loaded {len(vocabs)} vocabularies")
    
    print("\n[2] Loading statistics...")
    train_tsv_path = config['datasets_dir'] / config['train_dataset']
    
    if train_tsv_path.exists():
        age_mean, age_std, _ = get_age_stats(str(train_tsv_path), sample_size=100000)
        normalization_stats = {
            'age': {'mean': age_mean, 'std': age_std},
            'sex': {'min': 0.0, 'max': 1.0},
            'is_dead': {'min': 0.0, 'max': 1.0}
        }
        print(f"    Age stats: mean={age_mean:.2f}, std={age_std:.2f}")
    else:
        print(f"    Warning: train dataset not found, using defaults")
        normalization_stats = {
            'age': {'mean': 40.0, 'std': 20.0},
            'sex': {'min': 0.0, 'max': 1.0},
            'is_dead': {'min': 0.0, 'max': 1.0}
        }
    
    print("\n[3] Creating datasets...")
    
    train_dataset = PatientSequenceDataset(
        tsv_path=str(config['datasets_dir'] / config['train_dataset']),
        min_sequence_length=config['min_seq_len'],
        max_sequence_length=config['max_seq_len'],
        window_stride=5,
        chunk_size=50000,
        presetted_patients_count=98_433,
        presetted_windows_count=3_326_419
    )
    
    val_dataset = PatientSequenceDataset(
        tsv_path=str(config['datasets_dir'] / config['val_dataset']),
        min_sequence_length=config['min_seq_len'],
        max_sequence_length=config['max_seq_len'],
        window_stride=5,
        chunk_size=50000,
        presetted_patients_count=21_263,
        presetted_windows_count=642_136
    )
    
    print(f"    Train dataset ready")
    print(f"    Val dataset ready")
    
    print("\n[4] Creating dataloaders...")
    
    collate_func = FastCollate(vocabs, normalization_stats)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        collate_fn=collate_func,
        num_workers=0,
        pin_memory=config['pin_memory'],
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        collate_fn=collate_func,
        num_workers=0,
        pin_memory=config['pin_memory'],
    )
    
    print(f"    Train loader: {len(train_loader)} batches")
    print(f"    Val loader: {len(val_loader)} batches")
    
    print("\n[5] Initializing model...")
    
    model = MedicalLSTM(config).to(device)
    
    total_params, trainable_params = model.get_total_params()
    print(f"    Model: MedicalLSTM")
    print(f"    Parameters: {total_params:,} total, {trainable_params:,} trainable")
    
    print("\n[6] Initializing optimizer...")
    
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config['learning_rate'],
        weight_decay=config['weight_decay'],
        betas=(0.9, 0.999),
        eps=1e-8
    )
    
    loss_fn = SimpleMultiTaskLoss(
        loss_weights=config['loss_weights']
    ).to(device)
    
    scaler = torch.amp.GradScaler(
        'cuda',
        init_scale=config['grad_scaler_init'],
        growth_interval=config['grad_scaler_growth_interval']
    )
    
    print(f"    Optimizer: AdamW, lr={config['learning_rate']}")
    
    print("\n[7] Checking checkpoint...")
    
    checkpoint_path = config['train_state_dir'] / "model_last_checkpoint.pkl"
    
    start_epoch = 0
    train_history = {}
    val_history = {}
    best_val_loss = float('inf')
    
    if checkpoint_path.exists():
        response = input("    Found checkpoint. Load? (y/n): ").lower()
        if response == 'y':
            success, loaded_epoch, loaded_history, loaded_best_loss = load_training_state(
                model, optimizer, scaler,
                model_name="model_last",
            )
            
            if success:
                start_epoch = loaded_epoch + 1
                train_history = loaded_history.get('train', {})
                val_history = loaded_history.get('val', {})
                best_val_loss = loaded_best_loss
                print(f"    Loaded checkpoint, resuming from epoch {start_epoch}")
            else:
                print(f"    Failed to load, starting from scratch")
        else:
            print(f"    Starting from scratch")
    else:
        print(f"    No checkpoint found, starting from scratch")
    
    print("\n" + "="*70)
    print("STARTING TRAINING")
    print("="*70)
    print(f"Epochs: {config['num_epochs']}, Start epoch: {start_epoch}")
    print(f"Patience: {config['patience']}")
    print("="*70 + "\n")
    
    patience_counter = 0
    
    for epoch in range(start_epoch, config['num_epochs']):
        epoch_start_time = time.time()
        
        print(f"\n>>> EPOCH {epoch} <<<")
        
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, 
                                device, config, epoch, scaler)
        
        val_metrics = validate_epoch(model, val_loader, loss_fn, device, config, epoch)
        
        epoch_time = time.time() - epoch_start_time
        
        train_history.setdefault('loss', []).append(train_loss)
        for key, value in val_metrics.items():
            val_history.setdefault(key, []).append(value)
        
        is_best = val_metrics['loss'] < best_val_loss
        if is_best:
            best_val_loss = val_metrics['loss']
            patience_counter = 0
        else:
            patience_counter += 1
        
        save_epoch_metrics(epoch, train_loss, val_metrics, epoch_time, is_best, metrics_dir)
        
        history = {
            'train': train_history,
            'val': val_history,
            'config': config,
            'vocab_sizes': config['vocab_sizes'],
            'normalization_stats': normalization_stats
        }
        
        save_training_state(
            model=model,
            optimizer=optimizer,
            scaler=scaler,
            epoch=epoch,
            history=history,
            best_val_loss=best_val_loss,
            model_name="model_last",
        )
        
        if is_best:
            save_training_state(
                model=model,
                optimizer=optimizer,
                scaler=scaler,
                epoch=epoch,
                history=history,
                best_val_loss=best_val_loss,
                model_name="model_best",
            )
            print(f"    💾 Saved best model (val_loss: {best_val_loss:.4f})")
        
        if patience_counter >= config['patience']:
            print(f"\n>>> EARLY STOPPING at epoch {epoch} <<<")
            print(f"    No improvement for {config['patience']} epochs")
            break
    
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"Total epochs: {epoch + 1}")
    print(f"Best val loss: {best_val_loss:.4f}")
    
    if val_history and 'loss' in val_history:
        best_epoch = np.argmin(val_history['loss'])
        print(f"\nBest epoch: {best_epoch}")
        
        key_metrics = ['age_mae', 'age_r2', 'death_recall', 'death_f1']
        for metric in key_metrics:
            if metric in val_history and len(val_history[metric]) > best_epoch:
                print(f"  {metric}: {val_history[metric][best_epoch]:.4f}")
    
    save_training_state(
        model=model,
        optimizer=optimizer,
        scaler=scaler,
        epoch=epoch,
        history=history,
        best_val_loss=best_val_loss,
        model_name="model_final",
    )
    
    print(f"\n💾 Final model saved")
    print(f"📊 All metrics saved to {metrics_dir}/training_metrics.json")
    print("="*70)


if __name__ == "__main__":
    total_start = time.time()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ TRAINING INTERRUPTED")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    total_time = time.time() - total_start
    print(f"\nTotal execution time: {total_time:.1f}s")
    print("="*70)