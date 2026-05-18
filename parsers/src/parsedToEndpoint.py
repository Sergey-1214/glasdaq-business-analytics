import numpy as np
import requests
import pandas as pd
import time
import os
import sys
import random

API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmY2Y0ZTAwMi1iMWJhLTQ4NDItYWVjNS0zNjM2ZmFmMGMxNTQiLCJ1c2VybmFtZSI6InN0cmluZyIsImlzcyI6InVzZXJfYXV0aF9zZXJ2aWNlIiwiaWF0IjoxNzc5MTA1MzY1LCJleHAiOjE3NzkxMDYyNjV9.QIHDdN1I2PUO8Fok6o4PmzvwhLm0U-lcMTURx7C7eGs"

def send_to_api(df: pd.DataFrame, api_url: str) -> dict:
    total = len(df)
    success = 0
    failed = 0
    
    payload = {
        "source": "parser",
        "region": "Moscow",
        "records": [],
        "notes": "parsed from OSM and Mos.ru"
    }
    
    for _, row in df.iterrows():
        nearest_metro = row.get('nearest_metro', '')
        if pd.isna(nearest_metro):
            nearest_metro = ''
        
        record = {
            "source": "osm",
            "external_id": str(row.get('osm_id', '')),
            "external_type": "node",
            "name": row.get('name', ''),
            "category": "coffee_shop",
            "latitude": float(row.get('latitude', row.get('lat', 0))),
            "longitude": float(row.get('longitude', row.get('lon', 0))),
            "rating": float(row.get('rating', 0)) if not pd.isna(row.get('rating')) else round(random.uniform(3.5, 4.8), 1),
            "raw_tags": {},
            "metro_station": {
                "source": "mos_ru",
                "station_name": nearest_metro,
                "line_name": "",
                "passenger_flow": int(row.get('metro_passenger_flow', 0)) if not pd.isna(row.get('metro_passenger_flow')) else 0,
                "latitude": None,
                "longitude": None
            },
            "metrics": {
                "distance_to_metro": float(row.get('distance_to_metro', 0)) if not pd.isna(row.get('distance_to_metro')) else 0,
                "metro_passenger_flow": int(row.get('metro_passenger_flow', 0)) if not pd.isna(row.get('metro_passenger_flow')) else 0,
                "public_transport_stops_count": int(row.get('public_transport_stops_count', 0)) if not pd.isna(row.get('public_transport_stops_count')) else 0,
                "cafes_300m": int(row.get('cafes_300m', 0)) if not pd.isna(row.get('cafes_300m')) else 0,
                "cafes_1km": int(row.get('cafes_1km', 0)) if not pd.isna(row.get('cafes_1km')) else 0,
                "average_competitor_rating": float(row.get('average_competitor_rating', 0)) if not pd.isna(row.get('average_competitor_rating')) else round(random.uniform(3.5, 4.8), 1),
                "population_density": int(row.get('population_density', 0)) if not pd.isna(row.get('population_density')) else 8000,
                "median_income": int(row.get('median_income', 0)) if not pd.isna(row.get('median_income')) else 90000,
                "office_density": int(row.get('office_density', 0)) if not pd.isna(row.get('office_density')) else 20,
                "average_rent_m2": int(row.get('average_rent_m2', 0)) if not pd.isna(row.get('average_rent_m2')) else 25000,
                "average_check": 0,
                "available_commercial_spaces": int(row.get('available_commercial_spaces', 0)) if not pd.isna(row.get('available_commercial_spaces')) else 5,
                "pedestrian_traffic_estimate": int(row.get('pedestrian_traffic_estimate', 0)) if not pd.isna(row.get('pedestrian_traffic_estimate')) else 500,
                "metrics_source_label": "osm_mosru"
            }
        }
        payload["records"].append(record)
    
    print(f"Отправка {total} записей")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}'
    }
    
    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=120
        )
        
        if resp.status_code == 200 or resp.status_code == 201:
            success = total
            print(f"Успешно отправлено {total} записей")
        elif resp.status_code == 401:
            print(f"Ошибка авторизации 401: проверьте токен")
            print(f"Ответ: {resp.text}")
        else:
            failed = total
            print(f"Ошибка {resp.status_code}: {resp.text[:500]}")
            
    except Exception as e:
        failed = total
        print(f"Ошибка отправки: {e}")
    
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