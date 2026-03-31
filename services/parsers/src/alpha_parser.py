import requests
import pandas as pd
import numpy as np
import time
import json
import logging
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Tuple, List, Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------
# 1. Базовые функции
# -------------------------------

def haversine(lon1, lat1, lon2, lat2):
    """Расчет расстояния в метрах между двумя точками"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000
    return c * r

# Границы Москвы
MOSCOW_BBOX = (55.49, 37.35, 55.92, 37.85)

def safe_overpass_request(query: str, retries: int = 3, delay: int = 2) -> Optional[dict]:
    """Безопасный запрос к Overpass API с повторными попытками"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    for attempt in range(retries):
        try:
            logger.info(f"Отправка запроса к Overpass API (попытка {attempt + 1}/{retries})")
            response = requests.post(overpass_url, data=query, timeout=60)
            response.raise_for_status()
            
            # Проверяем, что ответ не пустой
            if not response.text or response.text.strip() == '':
                logger.warning("Получен пустой ответ от API")
                continue
                
            data = response.json()
            logger.info(f"Успешно получено {len(data.get('elements', []))} элементов")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Ответ API: {response.text[:200] if response.text else 'пустой'}")
        
        if attempt < retries - 1:
            logger.info(f"Повторная попытка через {delay} секунд...")
            time.sleep(delay)
            delay *= 2
    
    logger.error("Не удалось выполнить запрос после всех попыток")
    return None

# -------------------------------
# 2. Сбор данных из OpenStreetMap с разбивкой по регионам
# -------------------------------

def split_bbox(bbox: Tuple[float, float, float, float], parts: int = 4) -> List[Tuple[float, float, float, float]]:
    """Разбивает bounding box на части для уменьшения нагрузки на API"""
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_step = (max_lat - min_lat) / parts
    lon_step = (max_lon - min_lon) / parts
    
    bboxes = []
    for i in range(parts):
        for j in range(parts):
            bboxes.append((
                min_lat + i * lat_step,
                min_lon + j * lon_step,
                min_lat + (i + 1) * lat_step,
                min_lon + (j + 1) * lon_step
            ))
    return bboxes

def get_coffee_shops_osm() -> pd.DataFrame:
    """Сбор кофеен из OSM с разбивкой по частям"""
    all_shops = []
    bboxes = split_bbox(MOSCOW_BBOX, parts=3)
    
    for i, bbox in enumerate(bboxes):
        logger.info(f"Загрузка кофеен, часть {i+1}/{len(bboxes)}")
        
        query = f"""
        [out:json][timeout:60];
        (
          node["amenity"="cafe"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["amenity"="restaurant"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["amenity"="fast_food"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["shop"="coffee"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
        );
        out body;
        """
        
        data = safe_overpass_request(query)
        if not data:
            continue
            
        for element in data.get('elements', []):
            if element.get('type') == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if lat and lon:
                    tags = element.get('tags', {})
                    all_shops.append({
                        'osm_id': element['id'],
                        'name': tags.get('name', ''),
                        'lat': lat,
                        'lon': lon,
                        'category': tags.get('amenity', tags.get('shop', '')),
                        'address': tags.get('addr:full', '')
                    })
        
        time.sleep(1)  # Пауза между запросами
    
    logger.info(f"Всего найдено кофеен: {len(all_shops)}")
    return pd.DataFrame(all_shops)

def get_metro_stations_osm() -> pd.DataFrame:
    """Сбор станций метро из OSM"""
    all_stations = []
    
    query = f"""
    [out:json][timeout:60];
    (
      node["railway"="subway_entrance"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
      node["station"="subway"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
      node["subway"="yes"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    
    data = safe_overpass_request(query)
    if data:
        for element in data.get('elements', []):
            if element.get('type') == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if lat and lon:
                    tags = element.get('tags', {})
                    all_stations.append({
                        'metro_id': element['id'],
                        'name': tags.get('name', ''),
                        'lat': lat,
                        'lon': lon
                    })
    
    # Удаляем дубликаты по координатам
    stations_df = pd.DataFrame(all_stations)
    if not stations_df.empty:
        stations_df = stations_df.drop_duplicates(subset=['lat', 'lon'])
    
    logger.info(f"Найдено станций метро: {len(stations_df)}")
    return stations_df

def get_public_transport_stops_osm() -> pd.DataFrame:
    """Сбор остановок общественного транспорта с упрощенным запросом"""
    all_stops = []
    
    # Упрощенный запрос - только автобусные остановки
    query = f"""
    [out:json][timeout:30];
    (
      node["highway"="bus_stop"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    
    data = safe_overpass_request(query)
    if data:
        for element in data.get('elements', []):
            if element.get('type') == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if lat and lon:
                    all_stops.append({'stop_lat': lat, 'stop_lon': lon})
    
    logger.info(f"Найдено остановок транспорта: {len(all_stops)}")
    return pd.DataFrame(all_stops)

def get_office_buildings_osm() -> pd.DataFrame:
    """Сбор офисных зданий"""
    all_offices = []
    
    query = f"""
    [out:json][timeout:60];
    (
      node["office"="yes"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
      node["building"="office"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    
    data = safe_overpass_request(query)
    if data:
        for element in data.get('elements', []):
            if element.get('type') == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if lat and lon:
                    all_offices.append({'office_lat': lat, 'office_lon': lon})
    
    logger.info(f"Найдено офисных зданий: {len(all_offices)}")
    return pd.DataFrame(all_offices)

# -------------------------------
# 3. Данные Mos.ru
# -------------------------------

def get_mosru_data(api_key: Optional[str] = None) -> dict:
    """Получение данных с Mos.ru"""
    results = {'metro_passenger_flow': {}}
    
    if api_key:
        metro_flow_url = "https://apidata.mos.ru/v1/datasets/1199/rows"
        try:
            response = requests.get(metro_flow_url, params={'api_key': api_key, '$top': 500}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for row in data:
                    cells = row.get('Cells', {})
                    station_name = cells.get('Station', '')
                    flow = cells.get('Passengers', 0)
                    if station_name and flow:
                        results['metro_passenger_flow'][station_name] = flow
                logger.info(f"Загружен пассажиропоток для {len(results['metro_passenger_flow'])} станций")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных Mos.ru: {e}")
    else:
        logger.warning("API ключ Mos.ru не предоставлен, пропускаем загрузку пассажиропотока")
    
    return results

# -------------------------------
# 4. Расчет метрик
# -------------------------------

def calculate_all_location_metrics(coffee_df: pd.DataFrame, metro_df: pd.DataFrame, 
                                   stops_df: pd.DataFrame, mosru_data: dict) -> pd.DataFrame:
    """Расчет всех метрик для каждой кофейни"""
    metrics = []
    
    logger.info("Начало расчета метрик для каждой локации...")
    
    for idx, cafe in coffee_df.iterrows():
        target_lon, target_lat = cafe['lon'], cafe['lat']
        
        # Конкуренты в радиусе 300м и 1км
        competitors_300m = 0
        competitors_1km = 0
        
        for _, comp in coffee_df.iterrows():
            if comp['osm_id'] == cafe['osm_id']:
                continue
            dist = haversine(target_lon, target_lat, comp['lon'], comp['lat'])
            if dist < 300:
                competitors_300m += 1
            if dist < 1000:
                competitors_1km += 1
        
        # Расстояние до ближайшего метро и пассажиропоток
        min_metro_dist = None
        nearest_metro_name = None
        
        if not metro_df.empty:
            for _, metro in metro_df.iterrows():
                dist = haversine(target_lon, target_lat, metro['lon'], metro['lat'])
                if min_metro_dist is None or dist < min_metro_dist:
                    min_metro_dist = dist
                    nearest_metro_name = metro['name']
        
        # Количество остановок транспорта рядом (радиус 500м)
        stops_count = 0
        if not stops_df.empty:
            for _, stop in stops_df.iterrows():
                dist = haversine(target_lon, target_lat, stop['stop_lon'], stop['stop_lat'])
                if dist < 500:
                    stops_count += 1
        
        # Пассажиропоток ближайшей станции метро
        metro_flow = None
        if nearest_metro_name:
            metro_flow = mosru_data.get('metro_passenger_flow', {}).get(nearest_metro_name)
        
        # Расчетный пешеходный поток
        pedestrian_traffic = 0
        if metro_flow:
            pedestrian_traffic += int(metro_flow * 0.3)
        if stops_count > 0:
            pedestrian_traffic += stops_count * 500
        
        metrics.append({
            'cafes_300m': competitors_300m,
            'cafes_1km': competitors_1km,
            'distance_to_metro': min_metro_dist,
            'nearest_metro': nearest_metro_name,
            'metro_passenger_flow': metro_flow,
            'public_transport_stops_count': stops_count,
            'pedestrian_traffic_estimate': pedestrian_traffic,
            'average_competitor_rating': None
        })
        
        if idx % 500 == 0 and idx > 0:
            logger.info(f"Обработано {idx}/{len(coffee_df)} локаций")
    
    metrics_df = pd.DataFrame(metrics)
    result_df = pd.concat([coffee_df.reset_index(drop=True), metrics_df], axis=1)
    
    logger.info("Расчет метрик завершен")
    return result_df

def calculate_office_density(coffee_df: pd.DataFrame, offices_df: pd.DataFrame) -> List[int]:
    """Расчет количества офисов в радиусе 500м"""
    office_counts = []
    
    if offices_df.empty:
        logger.warning("Нет данных об офисах")
        return [0] * len(coffee_df)
    
    logger.info("Расчет офисной плотности...")
    
    for idx, cafe in coffee_df.iterrows():
        count = 0
        for _, office in offices_df.iterrows():
            dist = haversine(cafe['lon'], cafe['lat'], office['office_lon'], office['office_lat'])
            if dist < 500:
                count += 1
        office_counts.append(count)
        
        if idx % 500 == 0 and idx > 0:
            logger.info(f"Обработано {idx}/{len(coffee_df)} локаций")
    
    return office_counts

# -------------------------------
# 5. Данные по районам
# -------------------------------

def load_district_data() -> Tuple[dict, dict]:
    """Загрузка данных по районам"""
    district_data = {
        'ЦАО': {'population_density': 12500, 'median_income': 110000},
        'САО': {'population_density': 9800, 'median_income': 95000},
        'СВАО': {'population_density': 10200, 'median_income': 92000},
        'ВАО': {'population_density': 8900, 'median_income': 88000},
        'ЮВАО': {'population_density': 8500, 'median_income': 85000},
        'ЮАО': {'population_density': 9100, 'median_income': 87000},
        'ЮЗАО': {'population_density': 10500, 'median_income': 98000},
        'ЗАО': {'population_density': 8800, 'median_income': 96000},
        'СЗАО': {'population_density': 9200, 'median_income': 94000},
        'ЗелАО': {'population_density': 7600, 'median_income': 89000},
        'ТиНАО': {'population_density': 3200, 'median_income': 85000}
    }
    
    rent_data = {
        'ЦАО': {'avg_rent_m2': 45000, 'available_spaces': 342},
        'САО': {'avg_rent_m2': 28000, 'available_spaces': 187},
        'СВАО': {'avg_rent_m2': 25000, 'available_spaces': 156},
        'ВАО': {'avg_rent_m2': 23000, 'available_spaces': 203},
        'ЮВАО': {'avg_rent_m2': 21000, 'available_spaces': 178},
        'ЮАО': {'avg_rent_m2': 24000, 'available_spaces': 192},
        'ЮЗАО': {'avg_rent_m2': 29000, 'available_spaces': 165},
        'ЗАО': {'avg_rent_m2': 27000, 'available_spaces': 149},
        'СЗАО': {'avg_rent_m2': 26000, 'available_spaces': 134},
        'ЗелАО': {'avg_rent_m2': 20000, 'available_spaces': 89},
        'ТиНАО': {'avg_rent_m2': 18000, 'available_spaces': 245}
    }
    
    return district_data, rent_data

def assign_district_by_coords(lat: float, lon: float) -> str:
    """Определение района по координатам"""
    if 55.70 <= lat <= 55.80 and 37.55 <= lon <= 37.70:
        return 'ЦАО'
    elif lat > 55.80:
        if lon < 37.60:
            return 'СЗАО'
        elif lon > 37.70:
            return 'СВАО'
        return 'САО'
    elif lat > 55.75:
        if lon > 37.70:
            return 'СВАО'
        return 'САО'
    elif lat < 55.60 and lon > 37.65:
        return 'ЮВАО'
    elif lat < 55.65:
        if lon < 37.55:
            return 'ЮЗАО'
        return 'ЮАО'
    elif lat < 55.70 and lon < 37.55:
        return 'ЮЗАО'
    elif lon < 37.45:
        return 'ЗАО'
    elif lon > 37.75:
        if lat < 55.65:
            return 'ВАО'
        return 'ВАО'
    else:
        return 'ЦАО'

# -------------------------------
# 6. Главная функция
# -------------------------------

def main() -> pd.DataFrame:
    """Главная функция сборки всех данных"""
    logger.info("=== Сбор всех данных для анализа кофеен Москвы ===\n")
    
    # Шаг 1: Сбор кофеен
    logger.info("1. Загрузка кофеен из OpenStreetMap...")
    coffee_df = get_coffee_shops_osm()
    if coffee_df.empty:
        logger.error("Не удалось загрузить данные о кофейнях")
        return pd.DataFrame()
    logger.info(f"   Найдено {len(coffee_df)} заведений")
    
    # Шаг 2: Сбор транспорта
    logger.info("\n2. Загрузка станций метро...")
    metro_df = get_metro_stations_osm()
    logger.info(f"   Найдено {len(metro_df)} станций метро")
    
    logger.info("\n3. Загрузка остановок транспорта...")
    stops_df = get_public_transport_stops_osm()
    logger.info(f"   Найдено {len(stops_df)} остановок")
    
    logger.info("\n4. Загрузка офисных зданий...")
    offices_df = get_office_buildings_osm()
    logger.info(f"   Найдено {len(offices_df)} офисных зданий")
    
    # Шаг 3: Данные Mos.ru
    logger.info("\n5. Загрузка данных с Mos.ru...")
    mosru_data = get_mosru_data(api_key=None)
    
    # Шаг 4: Расчет метрик локации
    logger.info("\n6. Расчет метрик для каждой локации...")
    enriched_df = calculate_all_location_metrics(coffee_df, metro_df, stops_df, mosru_data)
    
    # Шаг 5: Добавление демографических данных
    logger.info("\n7. Добавление демографических данных...")
    district_data, rent_data = load_district_data()
    
    districts = [assign_district_by_coords(row['lat'], row['lon']) for _, row in enriched_df.iterrows()]
    
    enriched_df['district'] = districts
    enriched_df['population_density'] = enriched_df['district'].map(
        lambda d: district_data.get(d, {}).get('population_density', 8000))
    enriched_df['median_income'] = enriched_df['district'].map(
        lambda d: district_data.get(d, {}).get('median_income', 90000))
    enriched_df['average_rent_m2'] = enriched_df['district'].map(
        lambda d: rent_data.get(d, {}).get('avg_rent_m2', 25000))
    enriched_df['available_commercial_spaces'] = enriched_df['district'].map(
        lambda d: rent_data.get(d, {}).get('available_spaces', 150))
    
    # Шаг 6: Офисная плотность
    logger.info("\n8. Расчет офисной плотности...")
    enriched_df['office_density'] = calculate_office_density(enriched_df, offices_df)
    
    # Шаг 7: Сохранение
    logger.info("\n9. Сохранение результатов...")
    
    final_columns = [
        'name', 'lat', 'lon', 'district', 'address',
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
        'available_commercial_spaces'
    ]
    
    existing_columns = [col for col in final_columns if col in enriched_df.columns]
    final_df = enriched_df[existing_columns]
    
    # Сохраняем в CSV
    output_file = 'moscow_coffee_shops_full_analysis.csv'
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    logger.info(f"\n=== ГОТОВО ===")
    logger.info(f"Собрано {len(final_df)} кофеен")
    logger.info(f"Сохранено в: {output_file}")
    
    # Статистика
    logger.info("\n=== Статистика по метрикам ===")
    if 'pedestrian_traffic_estimate' in final_df.columns:
        logger.info(f"Средний пешеходный поток (оценка): {final_df['pedestrian_traffic_estimate'].mean():.0f} чел/день")
    if 'population_density' in final_df.columns:
        logger.info(f"Средняя плотность населения: {final_df['population_density'].mean():.0f} чел/км²")
    if 'median_income' in final_df.columns:
        logger.info(f"Средний доход: {final_df['median_income'].mean():.0f} руб/мес")
    if 'average_rent_m2' in final_df.columns:
        logger.info(f"Средняя аренда: {final_df['average_rent_m2'].mean():.0f} руб/м²")
    
    return final_df

if __name__ == "__main__":
    df = main()