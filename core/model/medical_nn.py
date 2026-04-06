import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MedicalLSTM(nn.Module):
    def __init__(self, config):
        super(MedicalLSTM, self).__init__()
        
        self.config = config
        
        # Конфигурация
        self.lstm_hidden = config['lstm_hidden']
        self.mlp_hidden = config['mlp_hidden']
        self.dropout_rate = config.get('dropout', 0.2)
        
        # 1. ВСЕ ПРОСТЫЕ КАТЕГОРИАЛЬНЫЕ ПРИЗНАКИ (6 штук)
        self.simple_features = ['group', 'profile', 'result', 'type', 'form', 'season']
        self.embeddings_simple = nn.ModuleDict()
        
        for feat in self.simple_features:
            vocab_size = config['vocab_sizes'][feat]
            embed_dim = config['embedding_dims'][feat]
            self.embeddings_simple[f'feat_{feat}'] = nn.Embedding(
                vocab_size, embed_dim, padding_idx=0
            )
        
        # 2. ЭМБЕДДИНГИ ДЛЯ ДИАГНОЗОВ (3 уровня)
        self.diag_levels = ['diagnosis_letter', 'diagnosis_hierarchy', 'diagnosis_full']
        self.embeddings_diagnosis = nn.ModuleDict()
        
        for level in self.diag_levels:
            vocab_size = config['vocab_sizes'][level]
            embed_dim = config['embedding_dims'][level]
            # Уменьшаем размерность для больших словарей
            if vocab_size > 10000:
                embed_dim = min(embed_dim, 64)  # Ограничиваем размерность
            self.embeddings_diagnosis[f'feat_{level}'] = nn.Embedding(
                vocab_size, embed_dim, padding_idx=0
            )
        
        # Пересчитываем размерность с учетом ограничений
        diag_embed_dims = []
        for level in self.diag_levels:
            vocab_size = config['vocab_sizes'][level]
            embed_dim = config['embedding_dims'][level]
            if vocab_size > 10000:
                diag_embed_dims.append(min(embed_dim, 64))
            else:
                diag_embed_dims.append(embed_dim)
        
        self.diag_embed_total = sum(diag_embed_dims)
        
        # 3. ЭМБЕДДИНГИ ДЛЯ УСЛУГ (3 уровня)
        self.service_levels = ['service_letter', 'service_hierarchy', 'service_full']
        self.embeddings_service = nn.ModuleDict()
        
        for level in self.service_levels:
            vocab_size = config['vocab_sizes'][level]
            embed_dim = config['embedding_dims'][level]
            if vocab_size > 5000:
                embed_dim = min(embed_dim, 64)
            self.embeddings_service[f'feat_{level}'] = nn.Embedding(
                vocab_size, embed_dim, padding_idx=0
            )
        
        # Размерность услуг
        service_embed_dims = []
        for level in self.service_levels:
            vocab_size = config['vocab_sizes'][level]
            embed_dim = config['embedding_dims'][level]
            if vocab_size > 5000:
                service_embed_dims.append(min(embed_dim, 64))
            else:
                service_embed_dims.append(embed_dim)
        
        service_embed_total = sum(service_embed_dims)
        
        # 4. ATTENTION ДЛЯ ДИАГНОЗОВ (с улучшенной стабильностью)
        num_features = 3  # age, sex, is_dead
        self.diag_attention = nn.Sequential(
            nn.Linear(self.diag_embed_total + num_features, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(64, 32),
            nn.GELU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(32, 1)
        )
        
        # 5. MLP ПЕРЕД LSTM
        # Вычисляем общую размерность входных признаков
        simple_embed_total = sum(
            config['embedding_dims'][feat] for feat in self.simple_features
        )
        
        # ИТОГОВАЯ РАЗМЕРНОСТЬ ВХОДА
        total_input_dim = (
            simple_embed_total +      # все простые категории (6 признаков)
            self.diag_embed_total +   # диагнозы после attention
            service_embed_total +     # услуги
            num_features              # числовые признаки
        )
        
        # 5.4 MLP слои с остаточными соединениями
        self.mlp_input = nn.Linear(total_input_dim, self.mlp_hidden)
        self.mlp_norm1 = nn.LayerNorm(self.mlp_hidden)
        self.mlp_linear1 = nn.Linear(self.mlp_hidden, self.mlp_hidden)
        self.mlp_norm2 = nn.LayerNorm(self.mlp_hidden)
        self.mlp_dropout = nn.Dropout(self.dropout_rate)
        
        # 6. LSTM с улучшенной инициализацией
        self.lstm = nn.LSTM(
            input_size=self.mlp_hidden,
            hidden_size=self.lstm_hidden,
            num_layers=1,
            batch_first=True,
            bidirectional=False,
            dropout=0.0  # Для однослойной LSTM dropout не работает
        )
        
        # 7. НОРМАЛИЗАЦИЯ после LSTM
        self.lstm_norm = nn.LayerNorm(self.lstm_hidden)
        
        # 8. ВЫХОДНЫЕ ГОЛОВЫ с нормализацией
        
        # 8.1 Регрессия
        self.head_age = nn.Sequential(
            nn.Linear(self.lstm_hidden, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(64, 1)
        )
        
        self.head_death = nn.Sequential(
            nn.Linear(self.lstm_hidden, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(64, 1)
        )
        
        # 8.2 Диагнозы (3 уровня) - с уменьшенной размерностью
        self.head_diagnosis = nn.ModuleDict()
        for level in self.diag_levels:
            vocab_size = config['vocab_sizes'][level]
            # Для больших словарей используем промежуточный слой
            self.head_diagnosis[f'feat_{level}'] = nn.Sequential(
                nn.Linear(self.lstm_hidden, 256),
                nn.LayerNorm(256),
                nn.GELU(),
                nn.Dropout(self.dropout_rate * 2),  # Больше dropout для больших классов
                nn.Linear(256, vocab_size)
            )
        
        # 8.3 Услуги (3 уровня)
        self.head_service = nn.ModuleDict()
        for level in self.service_levels:
            vocab_size = config['vocab_sizes'][level]
            self.head_service[f'feat_{level}'] = nn.Sequential(
                nn.Linear(self.lstm_hidden, 128),
                nn.LayerNorm(128),
                nn.GELU(),
                nn.Dropout(self.dropout_rate * 1.5),
                nn.Linear(128, vocab_size)
            )
        
        # 8.4 Все простые категории (6 признаков)
        self.head_simple = nn.ModuleDict()
        for feat in self.simple_features:
            vocab_size = config['vocab_sizes'][feat]
            self.head_simple[f'feat_{feat}'] = nn.Sequential(
                nn.Linear(self.lstm_hidden, 64),
                nn.LayerNorm(64),
                nn.GELU(),
                nn.Dropout(self.dropout_rate),
                nn.Linear(64, vocab_size)
            )
        
        # 9. ИНИЦИАЛИЗАЦИЯ ВЕСОВ
        self._init_weights()
        
        # 10. СЧЕТЧИК ДЛЯ ОТЛАДКИ
        self.forward_counter = 0
    
    def _init_weights(self):
        """Улучшенная инициализация весов."""
        for name, module in self.named_modules():
            if isinstance(module, nn.Linear):
                # Разная инициализация в зависимости от размера слоя
                if module.out_features > 5000:  # Очень большие выходные слои
                    nn.init.normal_(module.weight, mean=0.0, std=0.005)
                elif module.out_features > 1000:  # Большие выходные слои
                    nn.init.normal_(module.weight, mean=0.0, std=0.01)
                else:
                    nn.init.xavier_uniform_(module.weight, gain=0.5)  # Меньший gain
                
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            
            elif isinstance(module, nn.Embedding):
                # Для больших эмбеддингов - меньшая инициализация
                vocab_size = module.num_embeddings
                if vocab_size > 10000:
                    nn.init.normal_(module.weight, mean=0.0, std=0.01)
                else:
                    nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.padding_idx is not None:
                    with torch.no_grad():
                        module.weight[module.padding_idx].fill_(0)
            
            elif isinstance(module, nn.LSTM):
                for name_param, param in module.named_parameters():
                    if 'weight_ih' in name_param:
                        nn.init.xavier_uniform_(param.data)
                    elif 'weight_hh' in name_param:
                        nn.init.orthogonal_(param.data)
                    elif 'bias' in name_param:
                        # Инициализация bias для forget gate (помогает LSTM)
                        n = param.size(0)
                        param.data[n//4:n//2].fill_(1.0)  # forget gate bias
                        param.data[n//2:].fill_(0)  # остальные
    
    def _process_diagnoses(self, diag_tensors, num_tensors, mask):
        """Обработка диагнозов с attention механизмом (стабильная версия)."""
        B, S, max_diags = mask.shape
        
        # 1. Применяем эмбеддинги к каждому уровню диагнозов
        diag_embeds = []
        for level in self.diag_levels:
            embedded = self.embeddings_diagnosis[f'feat_{level}'](diag_tensors[level])
            # Проверка на NaN
            if torch.isnan(embedded).any():
                embedded = torch.nan_to_num(embedded, nan=0.0)
            diag_embeds.append(embedded)
        
        # 2. Конкатенируем
        diag_concat = torch.cat(diag_embeds, dim=-1)
        
        # 3. Стабилизация: нормализуем эмбеддинги
        diag_concat = F.layer_norm(diag_concat, [diag_concat.size(-1)])
        
        # 4. Добавляем числовые признаки
        num_expanded = num_tensors.unsqueeze(2).expand(-1, -1, max_diags, -1)
        num_expanded = F.layer_norm(num_expanded, [num_expanded.size(-1)])
        
        diag_with_features = torch.cat([diag_concat, num_expanded], dim=-1)
        
        # 5. Вычисляем веса attention
        attention_logits = self.diag_attention(diag_with_features).squeeze(-1)
        
        # 6. Применяем маску
        mask_bool = (mask == 0)
        attention_logits = attention_logits.masked_fill(mask_bool, -10000.0)  # Используем большое отрицательное
        
        # 7. Стабильный softmax
        attention_weights = F.softmax(attention_logits, dim=-1)
        
        # 8. Взвешенная сумма
        weights_expanded = attention_weights.unsqueeze(-1)
        weighted_diag = (diag_concat * weights_expanded).sum(dim=2)
        
        return weighted_diag, attention_weights
    
    def _stabilize_logits(self, logits):
        """Стабилизация логитов для предотвращения NaN."""
        # Вычитаем максимум для численной стабильности
        logits = logits - logits.max(dim=-1, keepdim=True).values
        
        # Мягкое ограничение
        logits = torch.clamp(logits, -50.0, 50.0)        
        
        return logits
    
    def forward(self, batch, return_attention=False):
        """Улучшенный прямой проход с проверками."""
        self.forward_counter += 1
        
        B, S = batch['age'].shape[:2]
        
        # 1. ЧИСЛОВЫЕ ПРИЗНАКИ с нормализацией
        numeric_features = torch.stack([
            batch['age'].squeeze(-1),
            batch['sex'].squeeze(-1),
            batch['is_dead'].squeeze(-1)
        ], dim=-1)
        
        # Нормализуем числовые признаки
        numeric_features = F.layer_norm(numeric_features, [numeric_features.size(-1)])
        
        # 2. ПРОСТЫЕ КАТЕГОРИАЛЬНЫЕ ПРИЗНАКИ
        simple_embeds = []
        for feat in self.simple_features:
            embedded = self.embeddings_simple[f'feat_{feat}'](batch[feat])
            # Проверка и фикс NaN
            if torch.isnan(embedded).any():
                embedded = torch.nan_to_num(embedded, nan=0.0)
            simple_embeds.append(embedded)
        
        simple_concat = torch.cat(simple_embeds, dim=-1)
        simple_concat = F.layer_norm(simple_concat, [simple_concat.size(-1)])
        
        # 3. ДИАГНОЗЫ С ATTENTION
        diag_tensors = {
            'diagnosis_letter': batch['diagnosis_letter'],
            'diagnosis_hierarchy': batch['diagnosis_hierarchy'],
            'diagnosis_full': batch['diagnosis_full']
        }
        
        diag_processed, attention_weights = self._process_diagnoses(
            diag_tensors,
            numeric_features,
            batch['diagnosis_mask']
        )
        
        # 4. УСЛУГИ
        service_embeds = []
        for level in self.service_levels:
            embedded = self.embeddings_service[f'feat_{level}'](batch[level])
            if torch.isnan(embedded).any():
                embedded = torch.nan_to_num(embedded, nan=0.0)
            service_embeds.append(embedded)
        
        service_concat = torch.cat(service_embeds, dim=-1)
        service_concat = F.layer_norm(service_concat, [service_concat.size(-1)])
        
        # 5. ОБЪЕДИНЕНИЕ ВСЕХ ПРИЗНАКОВ
        combined = torch.cat([
            simple_concat,
            diag_processed,
            service_concat,
            numeric_features
        ], dim=-1)
        
        # 6. MLP ПРЕОБРАЗОВАНИЕ с остаточными соединениями
        mlp_out = self.mlp_input(combined)
        mlp_out = self.mlp_norm1(mlp_out)
        
        residual = mlp_out
        mlp_out = F.gelu(self.mlp_linear1(mlp_out))
        mlp_out = self.mlp_norm2(mlp_out)
        mlp_out = self.mlp_dropout(mlp_out)
        mlp_out = mlp_out + residual  # Residual connection
        
        # 7. LSTM ОБРАБОТКА
        lengths = batch['lengths'].cpu()
        
        # Упаковываем последовательности
        packed_input = nn.utils.rnn.pack_padded_sequence(
            mlp_out,
            lengths,
            batch_first=True,
            enforce_sorted=False
        )
        
        packed_output, (hn, cn) = self.lstm(packed_input)
        
        # Берем последний скрытый состояние для каждого batch
        last_hidden = hn[-1]
        
        # Нормализация после LSTM
        last_hidden = self.lstm_norm(last_hidden)
        last_hidden = F.dropout(last_hidden, p=self.dropout_rate, training=self.training)
        
        # 8. ПРЕДСКАЗАНИЯ со стабилизацией
        predictions = {}
        
        # Регрессия
        predictions['age'] = self.head_age(last_hidden)
        predictions['death_logits'] = self.head_death(last_hidden)
        
        # Диагнозы с стабилизацией логитов
        for level in self.diag_levels:
            logits = self.head_diagnosis[f'feat_{level}'](last_hidden)
            logits = self._stabilize_logits(logits)
            predictions[f'{level}_logits'] = logits
        
        # Услуги
        for level in self.service_levels:
            logits = self.head_service[f'feat_{level}'](last_hidden)
            logits = self._stabilize_logits(logits)
            predictions[f'{level}_logits'] = logits
        
        # Простые категории
        for feat in self.simple_features:
            predictions[f'{feat}_logits'] = self.head_simple[f'feat_{feat}'](last_hidden)
        
        # Отладка: периодически выводим статистику
        if self.training and self.forward_counter % 50 == 0:
            print(f"\n[Forward #{self.forward_counter}] Statistics:")
            for key, value in predictions.items():
                if 'logits' in key or 'age' in key:
                    print(f"  {key}: mean={value.mean():.4f}, std={value.std():.4f}, "
                          f"min={value.min():.4f}, max={value.max():.4f}")
        
        if return_attention:
            return predictions, attention_weights
        
        return predictions
    
    
    def get_total_params(self):
        """Возвращает общее количество параметров модели."""
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        # Детализация по компонентам
        print("\n" + "="*60)
        print("MODEL PARAMETER COUNT:")
        print("="*60)
        
        components = {
            'Embeddings (Simple)': sum(p.numel() for n, p in self.named_parameters() 
                                     if 'embeddings_simple' in n),
            'Embeddings (Diagnosis)': sum(p.numel() for n, p in self.named_parameters() 
                                        if 'embeddings_diagnosis' in n),
            'Embeddings (Service)': sum(p.numel() for n, p in self.named_parameters() 
                                      if 'embeddings_service' in n),
            'MLP Layers': sum(p.numel() for n, p in self.named_parameters() 
                            if 'mlp' in n and 'embeddings' not in n),
            'LSTM': sum(p.numel() for n, p in self.named_parameters() 
                       if 'lstm' in n),
            'Head (Diagnosis)': sum(p.numel() for n, p in self.named_parameters() 
                                  if 'head_diagnosis' in n),
            'Head (Service)': sum(p.numel() for n, p in self.named_parameters() 
                                if 'head_service' in n),
            'Head (Simple)': sum(p.numel() for n, p in self.named_parameters() 
                               if 'head_simple' in n),
            'Head (Regression)': sum(p.numel() for n, p in self.named_parameters() 
                                   if 'head_age' in n or 'head_death' in n),
        }
        
        for name, count in components.items():
            if count > 0:
                print(f"{name:25s}: {count:,}")
        
        print("-"*60)
        print(f"{'TOTAL':25s}: {total:,}")
        print(f"{'TRAINABLE':25s}: {trainable:,}")
        print("="*60)
        
        return total, trainable