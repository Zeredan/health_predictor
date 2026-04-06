import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from pathlib import Path


def get_handbooks(file_path: str, *handbook_names: str) -> Dict[str, Dict[str, int]]:
    """
    Универсальная функция для загрузки справочников из CSV файла.
    
    Добавляет токены <PAD>: 0 и <UNK>: 1 к каждому справочнику.
    
    Args:
        file_path: Путь к CSV файлу
        *handbook_names: Имена справочников:
            - N имен: для каждого имени берется соответствующая колонка из CSV
            (0-я колонка - код, 1-я колонка - первый справочник, 2-я - второй и т.д.)
    
    Returns:
        Словарь справочников: {имя_справочника: {код: индекс}}
    """
    #print(f"📁 Загрузка: {Path(file_path).name}")
    
    try:
        df = pd.read_csv(file_path)
       # print(f"   Колонки: {list(df.columns)}")
        #print(f"   Строк: {len(df)}")
        
        result = {}
        
        if len(df.columns) < len(handbook_names) + 1:
            raise ValueError(f"Нужно минимум {len(handbook_names) + 1} колонок, а есть {len(df.columns)}")
        
        # Первая колонка всегда содержит коды
        code_col = df.columns[0]
        
        # Создаем справочник для каждого имени
        for i, name in enumerate(handbook_names, 1):
            if i >= len(df.columns):
                raise ValueError(f"Нет колонки для справочника '{name}' (индекс {i})")
            
            value_col = df.columns[i]
            
            # Создаем словарь {код: индекс}
            vocab = {}
            for _, row in df.iterrows():
                code = str(row[code_col]).strip()
                if code and not pd.isna(row[value_col]):
                    value = str(row[value_col]).strip()
                    if value:
                        # Предполагаем, что в колонке уже правильный индекс
                        # (начинается с 2, так как 0 и 1 зарезервированы)
                        try:
                            idx = int(value)
                            vocab[code] = idx
                        except ValueError:
                            # Если не число, генерируем индекс на основе уникальности
                            pass
            
            # Добавляем PAD и UNK в начало
            vocab_with_special = {"<PAD>": 0, "<UNK>": 1}
            vocab_with_special.update(vocab)
            
            result[name] = vocab_with_special
            #print(f"   ✓ {name}: {len(vocab_with_special)} элементов")
        
        return result
        
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise


def aggregate_all_vocabs(
        vocabs_dir: str = Path(__file__).parent.parent.parent.parent / "res" / "handbooks"
) -> Dict[str, Any]:
    """
    Агрегирует все справочники из директории.
    
    Returns:
        {
            'diagnosis_letter': {код: индекс},
            'diagnosis_hierarchy': {код: индекс},
            'diagnosis': {код: индекс},
            'service_letter': {код: индекс},
            'service_hierarchy': {код: индекс},
            'service': {код: индекс},
            'group': {код: индекс},
            'profile': {код: индекс},
            'result': {код: индекс},
            'type': {код: индекс},
            'form': {код: индекс}
        }
    """
    #print("=" * 50)
    #print("АГРЕГАЦИЯ СПРАВОЧНИКОВ")
    #print("=" * 50)
    
    vocabs_dir = Path(vocabs_dir)
    if not vocabs_dir.exists():
        print(f"✗ Директория не существует: {vocabs_dir}")
        return {}
    
    all_vocabs = {}
    
    # Загружаем иерархические справочники
    mkb_path = vocabs_dir / "mkb_handbook.csv"
    if mkb_path.exists():
        #print(f"\nДиагнозы ({mkb_path.name}):")
        # Предполагаем формат: код, индекс_буквы, буква, индекс_иерархии, иерархия, индекс_кода, код_полный
        diagnosis_vocabs = get_handbooks(
            str(mkb_path),
            "diagnosis_letter",
            "diagnosis_hierarchy", 
            "diagnosis_full"
        )
        all_vocabs.update(diagnosis_vocabs)
    
    services_path = vocabs_dir / "services_handbook.csv"
    if services_path.exists():
        #print(f"\nУслуги ({services_path.name}):")
        # Предполагаем аналогичный формат
        service_vocabs = get_handbooks(
            str(services_path),
            "service_letter", # на самом деле это тип а не символ
            "service_hierarchy",
            "service_full"
        )
        all_vocabs.update(service_vocabs)
    
    # Загружаем простые справочники
    simple_files = [
        ('group', 'group_handbook.csv'),
        ('profile', 'profile_handbook.csv'),
        ('result', 'result_handbook.csv'),
        ('type', 'type_handbook.csv'),
        ('form', 'form_handbook.csv')
    ]
    
    for vocab_name, filename in simple_files:
        file_path = vocabs_dir / filename
        if file_path.exists():
            #print(f"\n{vocab_name.title()} ({filename}):")
            # Предполагаем формат: код, индекс
            vocab_dict = get_handbooks(str(file_path), vocab_name)
            all_vocabs.update(vocab_dict)
    
    #print("\n" + "=" * 50)
    #print("ИТОГ:")
    for name in sorted([k for k in all_vocabs.keys() if not k.endswith('_size')]):
        size = len(all_vocabs[name])
        #print(f"  {name:25}: {size:4} элементов")
    #print("=" * 50)
    
    return all_vocabs


# if __name__ == "__main__":
#     print("\n" + "=" * 50)
#     print("ТЕСТ СПРАВОЧНИКОВ")
#     print("=" * 50 + "\n")
#     vocabs = aggregate_all_vocabs()
#     for name, vocab in vocabs.items():
#         print(f"\n{name} ({len(vocab)} элементов):")
#         sample_items = sorted(list(vocab.items()), key=lambda x: x[1], reverse=False)[:50]
#         for code, idx in sample_items:
#             print(f"  {code}: {idx}")
#         print("=" * 60)