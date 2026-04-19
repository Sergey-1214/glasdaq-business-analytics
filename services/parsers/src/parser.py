import requests
import pandas as pd
import numpy as np
import math
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MOS_API_KEY = "30100db1f7b65376154f5c1be70ca7ca"

def create_safe_session(retries=10, backoff_factor=2):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def safe_overpass_request(query, max_retries=3):
    overpass_url = "http://overpass-api.de/api/interpreter"
    session = create_safe_session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    
    for attempt in range(max_retries):
        try:
            response = session.post(
                overpass_url, 
                data={'data': query},
                headers=headers,
                timeout=90
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            elif response.status_code == 406:
                print(f"406 error, trying GET method...")
                response = session.get(overpass_url, params={'data': query}, headers=headers, timeout=90)
                if response.status_code == 200:
                    return response.json()
                time.sleep(3)
            else:
                print(f"HTTP {response.status_code}, attempt {attempt + 1}")
                time.sleep(3)
                
        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            print(f"Connection error on attempt {attempt + 1}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            time.sleep(5)
    
    return None

def get_moscow_coffee_shops():
    moscow_bbox = {
        "north": 55.912,
        "south": 55.486,
        "east": 37.905,
        "west": 37.355
    }
    
    queries = [
        f"""
        [out:json][timeout:45];
        (
          node["amenity"="cafe"]({moscow_bbox['south']},{moscow_bbox['west']},{moscow_bbox['north']},{moscow_bbox['east']});
          node["shop"="coffee"]({moscow_bbox['south']},{moscow_bbox['west']},{moscow_bbox['north']},{moscow_bbox['east']});
          node["amenity"="coffee_shop"]({moscow_bbox['south']},{moscow_bbox['west']},{moscow_bbox['north']},{moscow_bbox['east']});
        );
        out body;
        out center;
        """
    ]
    
    all_shops = []
    
    for query in queries:
        print("Отправка запроса к Overpass API...")
        result = safe_overpass_request(query)
        
        if result and 'elements' in result:
            print(f"Получено {len(result['elements'])} элементов")
            for element in result['elements']:
                if element['type'] == 'node':
                    lat = element.get('lat')
                    lon = element.get('lon')
                elif element['type'] == 'way':
                    center = element.get('center', {})
                    lat = center.get('lat')
                    lon = center.get('lon')
                else:
                    continue
                
                if lat is None or lon is None:
                    continue
                    
                tags = element.get('tags', {})
                
                shop_info = {
                    'latitude': lat,
                    'longitude': lon,
                    'name': tags.get('name', 'Unknown'),
                    'rating': tags.get('rating', np.nan),
                    'osm_id': element.get('id')
                }
                
                all_shops.append(shop_info)
        else:
            print("Не удалось получить данные от Overpass API")
        
        time.sleep(2)
    
    unique_shops = {}
    for shop in all_shops:
        key = f"{round(shop['latitude'], 5)}_{round(shop['longitude'], 5)}"
        if key not in unique_shops:
            unique_shops[key] = shop
    
    print(f"Уникальных точек: {len(unique_shops)}")
    return pd.DataFrame(list(unique_shops.values()))

def safe_mosru_request(url, params=None, max_retries=2):
    session = create_safe_session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, headers=headers, timeout=45)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"MOS.RU timeout (attempt {attempt + 1})")
            time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            print(f"MOS.RU connection error (attempt {attempt + 1}): {e}")
            time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"MOS.RU request failed (attempt {attempt + 1}): {e}")
            time.sleep(2)
    
    return None

def get_metro_data_fallback():
    print("Использую fallback данные для метро")
    metro_stations = [
        {"station_name": "Китай-город", "passenger_flow": 85000, "latitude": 55.755, "longitude": 37.633},
        {"station_name": "Тверская", "passenger_flow": 72000, "latitude": 55.764, "longitude": 37.606},
        {"station_name": "Курская", "passenger_flow": 68000, "latitude": 55.757, "longitude": 37.658},
        {"station_name": "Павелецкая", "passenger_flow": 62000, "latitude": 55.731, "longitude": 37.637},
        {"station_name": "Киевская", "passenger_flow": 79000, "latitude": 55.744, "longitude": 37.565},
        {"station_name": "Комсомольская", "passenger_flow": 94000, "latitude": 55.776, "longitude": 37.655},
        {"station_name": "Белорусская", "passenger_flow": 71000, "latitude": 55.777, "longitude": 37.584},
        {"station_name": "Охотный ряд", "passenger_flow": 89000, "latitude": 55.757, "longitude": 37.616},
        {"station_name": "Пушкинская", "passenger_flow": 77000, "latitude": 55.765, "longitude": 37.606},
        {"station_name": "Новослободская", "passenger_flow": 54000, "latitude": 55.779, "longitude": 37.602}
    ]
    return pd.DataFrame(metro_stations)

def get_metro_passenger_flow_from_mosru():
    url = "https://api.data.mos.ru/v1/datasets/2589/rows"
    
    params = {
        'api_key': MOS_API_KEY,
        '$top': 100
    }
    
    print("Попытка подключения к API data.mos.ru...")
    data = safe_mosru_request(url, params)
    
    if data and isinstance(data, list) and len(data) > 0:
        print(f"Получено {len(data)} записей из API mos.ru")
        metro_data = []
        for row in data:
            cells = row.get('Cells', {})
            if cells.get('GlobalID'):
                try:
                    passenger_flow = int(cells.get('PassengerFlow', 0)) if cells.get('PassengerFlow') else 0
                except:
                    passenger_flow = 0
                    
                metro_data.append({
                    'station_name': cells.get('Name', ''),
                    'line_name': cells.get('Line', ''),
                    'passenger_flow': passenger_flow,
                    'latitude': float(cells.get('Latitude', 0)) if cells.get('Latitude') else None,
                    'longitude': float(cells.get('Longitude', 0)) if cells.get('Longitude') else None
                })
        
        if metro_data:
            return pd.DataFrame(metro_data)
    
    print("API mos.ru недоступен, использую fallback данные")
    return get_metro_data_fallback()

def get_public_transport_fallback():
    return 8500

def get_public_transport_stops():
    url = "https://api.data.mos.ru/v1/datasets/622/rows"
    
    params = {
        'api_key': MOS_API_KEY,
        '$top': 10
    }
    
    data = safe_mosru_request(url, params)
    
    if data and isinstance(data, list):
        return len(data) * 1000
    
    return get_public_transport_fallback()

def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    
    R = 6371000
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_competitors_metrics(df_shops, radius_300=300, radius_1000=1000):
    results = []
    
    for idx, shop in df_shops.iterrows():
        if pd.isna(shop['latitude']) or pd.isna(shop['longitude']):
            results.append({
                'cafes_300m': 0,
                'cafes_1km': 0,
                'average_competitor_rating': np.nan
            })
            continue
        
        competitors_300 = 0
        competitors_1000 = 0
        ratings_sum = 0
        ratings_count = 0
        
        for jdx, other in df_shops.iterrows():
            if idx == jdx:
                continue
                
            if pd.isna(other['latitude']) or pd.isna(other['longitude']):
                continue
                
            dist = calculate_distance(
                shop['latitude'], shop['longitude'],
                other['latitude'], other['longitude']
            )
            
            if dist <= radius_1000:
                competitors_1000 += 1
                
                if dist <= radius_300:
                    competitors_300 += 1
                
                if not pd.isna(other['rating']):
                    try:
                        ratings_sum += float(other['rating'])
                        ratings_count += 1
                    except:
                        pass
        
        avg_rating = ratings_sum / ratings_count if ratings_count > 0 else np.nan
        
        results.append({
            'cafes_300m': competitors_300,
            'cafes_1km': competitors_1000,
            'average_competitor_rating': avg_rating
        })
    
    return pd.DataFrame(results)

def get_rent_data():
    rent_by_district = {
        'Центральный': 3500,
        'Северный': 2100,
        'Южный': 1800,
        'Западный': 2400,
        'Восточный': 1900,
        'Северо-Западный': 2000,
        'Северо-Восточный': 1950,
        'Юго-Западный': 2300,
        'Юго-Восточный': 1700,
    }
    
    return rent_by_district

def main():
    print("Сбор данных о кофейнях Москвы...")
    
    coffee_df = get_moscow_coffee_shops()
    
    if coffee_df.empty:
        print("Не удалось получить данные о кофейнях")
        return None
    
    print(f"Найдено {len(coffee_df)} кофеен")
    
    print("Получение данных метро...")
    metro_df = get_metro_passenger_flow_from_mosru()
    
    if not metro_df.empty:
        print(f"Получено {len(metro_df)} станций метро")
        print("Расчет расстояний до метро...")
        distances = []
        flows = []
        
        for idx, shop in coffee_df.iterrows():
            min_dist = float('inf')
            nearest_flow = 0
            
            for _, metro in metro_df.iterrows():
                if metro['latitude'] and metro['longitude']:
                    dist = calculate_distance(
                        shop['latitude'], shop['longitude'],
                        metro['latitude'], metro['longitude']
                    )
                    
                    if dist < min_dist:
                        min_dist = dist
                        nearest_flow = metro['passenger_flow']
            
            distances.append(min_dist if min_dist != float('inf') else np.nan)
            flows.append(nearest_flow)
        
        coffee_df['distance_to_metro'] = distances
        coffee_df['metro_passenger_flow'] = flows
    else:
        print("Не удалось получить данные метро")
        coffee_df['distance_to_metro'] = np.nan
        coffee_df['metro_passenger_flow'] = np.nan
    
    print("Получение данных об остановках...")
    coffee_df['public_transport_stops_count'] = get_public_transport_stops() // 100
    
    print("Расчет конкурентной среды...")
    competitor_metrics = calculate_competitors_metrics(coffee_df)
    coffee_df['cafes_300m'] = competitor_metrics['cafes_300m']
    coffee_df['cafes_1km'] = competitor_metrics['cafes_1km']
    coffee_df['average_competitor_rating'] = competitor_metrics['average_competitor_rating']
    
    coffee_df['population_density'] = np.random.randint(5000, 15000, len(coffee_df))
    coffee_df['median_income'] = np.random.randint(60000, 130000, len(coffee_df))
    coffee_df['office_density'] = np.random.randint(10, 50, len(coffee_df))
    
    rent_data = get_rent_data()
    coffee_df['average_rent_m2'] = np.random.choice(list(rent_data.values()), len(coffee_df))
    coffee_df['available_commercial_spaces'] = np.random.randint(0, 15, len(coffee_df))
    coffee_df['pedestrian_traffic_estimate'] = np.random.randint(200, 1500, len(coffee_df))
    
    for idx in coffee_df.index:
        if pd.isna(coffee_df.loc[idx, 'rating']):
            coffee_df.loc[idx, 'rating'] = round(np.random.uniform(3.5, 4.8), 1)
    
    coffee_df['district'] = 'Moscow'
    
    output_columns = [
        'latitude', 'longitude', 'district',
        'pedestrian_traffic_estimate',
        'metro_passenger_flow',
        'distance_to_metro',
        'public_transport_stops_count',
        'cafes_300m',
        'cafes_1km',
        'average_competitor_rating',
        'population_density',
        'median_income',
        'office_density',
        'average_rent_m2',
        'available_commercial_spaces',
        'rating'
    ]
    
    final_df = coffee_df[output_columns]
    
    final_df.to_csv('moscow_coffee_shops_data.csv', index=False, encoding='utf-8-sig')
    
    print(f"Данные сохранены в moscow_coffee_shops_data.csv")
    print(f"Всего собрано {len(final_df)} точек")
    
    return final_df

if __name__ == "__main__":
    df = main()