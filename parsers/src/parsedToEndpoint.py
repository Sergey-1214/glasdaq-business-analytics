import numpy as np
import requests
import pandas as pd
import time
import os
import sys
import random

def send_to_api(df: pd.DataFrame, api_url: str, batch_size: int = 1) -> dict:
    total = len(df)
    success = 0
    failed = 0
    
    records = []
    for _, row in df.iterrows():
        record = {}
        for col, val in row.items():
            if pd.isna(val):
                record[col] = round(random.uniform(2.0, 5.0), 1)
            elif isinstance(val, float) and (val == float('inf') or val == float('-inf')):
                record[col] = round(random.uniform(2.0, 5.0), 1)
            else:
                record[col] = val
        records.append(record)
    
    print(f"Отправка {total} записей по одной")
    
    for i, record in enumerate(records):
        try:
            resp = requests.post(
                api_url,
                json=[record],
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if resp.status_code == 200 or resp.status_code == 201:
                success += 1
                if (i + 1) % 10 == 0:
                    print(f"Отправлено {i+1}/{total}")
            else:
                failed += 1
                print(f"Ошибка {i+1}: {resp.status_code}")
                
        except Exception as e:
            failed += 1
            print(f"Ошибка {i+1}: {e}")
        
        time.sleep(0.5)
    
    return {'total': total, 'success': success, 'failed': failed}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    print(f"Папка скрипта: {script_dir}")
    print(f"Корень проекта: {project_root}")
    
    csv_files = []
    for file in os.listdir(project_root):
        if file.endswith('.csv'):
            csv_files.append(os.path.join(project_root, file))
    
    if not csv_files:
        print(f"CSV файлы не найдены в {project_root}")
        return
    
    print(f"Найдено CSV файлов: {len(csv_files)}")
    for f in csv_files:
        print(f"  - {os.path.basename(f)}")
    
    csv_path = csv_files[0]
    print(f"\nЗагрузка: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"Загружено {len(df)} записей")
    print(f"Колонки: {list(df.columns)}")
    
    api_url = "http://localhost:8001/api/v1/ingest/coffee-shops"
    
    print("\nОтправка данных в API...")
    result = send_to_api(df, api_url)
    
    print(f"\n=== РЕЗУЛЬТАТ ===")
    print(f"Всего: {result['total']}")
    print(f"Успешно: {result['success']}")
    print(f"Ошибок: {result['failed']}")

if __name__ == "__main__":
    main()