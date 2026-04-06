import torch
import torch.nn as nn

class SimpleMultiTaskLoss(nn.Module):
    def __init__(self, loss_weights=None, reduction='mean'):
        super().__init__()
        self.loss_weights = loss_weights or {}
        self.reduction = reduction
        
        # Loss функции
        self.mse_loss = nn.MSELoss(reduction=reduction)
        self.bce_loss = nn.BCEWithLogitsLoss(reduction=reduction)
        
        # Для CrossEntropy с большим числом классов используем стабильную версию
        self.ce_loss = nn.CrossEntropyLoss(
            reduction=reduction,
            ignore_index=0
        )
    
    def forward(self, predictions, targets, model=None):
        total_loss = 0
        loss_dict = {}
        
        # ОГРАНИЧИМ ЛОГИТЫ ДЛЯ БОЛЬШИХ СЛОВАРЕЙ
        logit_clip_value = 50.0  # Экспериментируйте с этим значением
        
        #print("=" * 60)
        #print("РАСЧЕТ ПОТЕРЬ:")
        #print("-" * 60)
        
        # 1. Возраст
        if 'age' in predictions:
            age_pred = predictions['age'].squeeze(-1)
            age_target = targets['age'].squeeze(-1)
            
            # Проверка на NaN
            if torch.isnan(age_pred).any():
                print("WARNING: age_pred contains NaN")
                age_pred = torch.nan_to_num(age_pred, nan=0.0)
            
            age_loss = self.mse_loss(age_pred, age_target)
            weight = self.loss_weights.get('age', 1.0)
            weighted_loss = weight * age_loss
            total_loss += weighted_loss
            
            loss_dict['loss_age'] = age_loss.item()
            
            #print(f"Возраст (age):")
            #print(f"  Weighted loss: {weighted_loss.item():.6f}")
            #print("-" * 40)
        
        # 2. Смерть
        if 'death_logits' in predictions:
            death_pred = predictions['death_logits'].squeeze(-1)
            death_target = targets['is_dead'].float().squeeze(-1)
            
            death_loss = self.bce_loss(death_pred, death_target)
            weight = self.loss_weights.get('death', 1.0)
            weighted_loss = weight * death_loss
            total_loss += weighted_loss
            
            loss_dict['loss_death'] = death_loss.item()
            
            #print(f"Смерть (death):")
            #print(f"  Weighted loss: {weighted_loss.item():.6f}")
            #print("-" * 40)
        
        # 3. Диагнозы (с ограничением логитов)
        diag_levels = ['diagnosis_letter', 'diagnosis_hierarchy', 'diagnosis_full']
        for level in diag_levels:
            logits_key = f'{level}_logits'
            if logits_key in predictions:
                logits = predictions[logits_key]
                targets_tensor = targets[level]
                
                # Ограничиваем логиты для стабильности
                logits = torch.clamp(logits, -logit_clip_value, logit_clip_value)
                
                ce_loss = self.ce_loss(logits, targets_tensor)
                weight = self.loss_weights.get(level, 1.0)
                weighted_loss = weight * ce_loss
                total_loss += weighted_loss
                
                loss_dict[f'loss_{level}'] = ce_loss.item()
                
                #print(f"Диагноз ({level}):")
                #print(f"  Weighted loss: {weighted_loss.item():.6f}")
                #print("-" * 40)
        
        # Вывод итогов
        #print("=" * 60)
        #print(f"ИТОГО:")
        #print(f"Общая сумма взвешенных потерь: {total_loss.item():.6f}")
        #print("=" * 60)
        
        # Проверяем итоговый loss
        if torch.isnan(total_loss):
            print("\n⚠️  ВНИМАНИЕ: total_loss содержит NaN!")
            # Возвращаем маленькое значение вместо NaN
            total_loss = torch.tensor(1e-6, requires_grad=True)
            print(f"Заменено на: {total_loss.item():.6f}")
            print("=" * 60)
        
        return total_loss, loss_dict