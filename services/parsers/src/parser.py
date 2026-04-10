import requests
import pandas as pd
import numpy as np
import time
import logging
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Tuple, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MOSCOW_BBOX = (55.49, 37.35, 55.92, 37.85)

def h_dist(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000
    return c * r

def safe_req(query: str, retries: int = 10, delay: int = 20) -> Optional[dict]:
    url = "https://overpass-api.de/api/interpreter"
    for attempt in range(retries):
        try:
            resp = requests.post(url, data=query, timeout=60)
            resp.raise_for_status()
            if not resp.text or resp.text.strip() == '':
                continue
            return resp.json()
        except Exception as e:
            logger.error(f"req err: {e}")
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    return None

def split_bbox(bbox: Tuple[float, float, float, float], parts: int = 3) -> List[Tuple[float, float, float, float]]:
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

def get_cafes() -> pd.DataFrame:
    all_shops = []
    bboxes = split_bbox(MOSCOW_BBOX, parts=3)
    for i, bbox in enumerate(bboxes):
        logger.info(f"load cafes part {i+1}/{len(bboxes)}")
        q = f"""
        [out:json][timeout:60];
        (
          node["amenity"="cafe"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["amenity"="restaurant"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["amenity"="fast_food"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["shop"="coffee"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
        );
        out body;
        """
        data = safe_req(q)
        if not data:
            continue
        for el in data.get('elements', []):
            if el.get('type') == 'node':
                lat, lon = el.get('lat'), el.get('lon')
                if lat and lon:
                    tags = el.get('tags', {})
                    all_shops.append({
                        'osm_id': el['id'],
                        'name': tags.get('name', ''),
                        'lat': lat,
                        'lon': lon,
                        'category': tags.get('amenity', tags.get('shop', '')),
                        'addr': tags.get('addr:full', '')
                    })
        time.sleep(1)
    logger.info(f"cafes found: {len(all_shops)}")
    return pd.DataFrame(all_shops)

def get_metro() -> pd.DataFrame:
    stations = []
    q = f"""
    [out:json][timeout:60];
    (
      node["railway"="subway_entrance"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
      node["station"="subway"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    data = safe_req(q)
    if data:
        for el in data.get('elements', []):
            if el.get('type') == 'node':
                lat, lon = el.get('lat'), el.get('lon')
                if lat and lon:
                    tags = el.get('tags', {})
                    stations.append({
                        'm_id': el['id'],
                        'name': tags.get('name', ''),
                        'lat': lat,
                        'lon': lon
                    })
    df = pd.DataFrame(stations)
    if not df.empty:
        df = df.drop_duplicates(subset=['lat', 'lon'])
    logger.info(f"metro found: {len(df)}")
    return df

def get_stops() -> pd.DataFrame:
    stops = []
    q = f"""
    [out:json][timeout:30];
    (
      node["highway"="bus_stop"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    data = safe_req(q)
    if data:
        for el in data.get('elements', []):
            if el.get('type') == 'node':
                lat, lon = el.get('lat'), el.get('lon')
                if lat and lon:
                    stops.append({'s_lat': lat, 's_lon': lon})
    logger.info(f"stops found: {len(stops)}")
    return pd.DataFrame(stops)

def get_offices() -> pd.DataFrame:
    offices = []
    q = f"""
    [out:json][timeout:60];
    (
      node["office"="yes"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
      node["building"="office"]({MOSCOW_BBOX[0]},{MOSCOW_BBOX[1]},{MOSCOW_BBOX[2]},{MOSCOW_BBOX[3]});
    );
    out body;
    """
    data = safe_req(q)
    if data:
        for el in data.get('elements', []):
            if el.get('type') == 'node':
                lat, lon = el.get('lat'), el.get('lon')
                if lat and lon:
                    offices.append({'o_lat': lat, 'o_lon': lon})
    logger.info(f"offices found: {len(offices)}")
    return pd.DataFrame(offices)

def get_2gis_ratings(df: pd.DataFrame, api_key: str) -> Dict[int, float]:
    ratings = {}
    url = "https://catalog.api.2gis.com/3.0/items"
    logger.info(f"loading 2gis ratings for {len(df)} places...")
    for idx, row in df.iterrows():
        if not row['name']:
            continue
        params = {
            'q': row['name'],
            'location': f"{row['lon']},{row['lat']}",
            'radius': 100,
            'sort': 'rating',
            'page_size': 1,
            'key': api_key
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get('result') and data['result'].get('items'):
                item = data['result']['items'][0]
                if 'rating' in item:
                    ratings[idx] = float(item['rating'])
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"2gis err for {row['name']}: {e}")
        if idx % 50 == 0 and idx > 0:
            logger.info(f"processed {idx}/{len(df)}, got {len(ratings)} ratings")
    logger.info(f"2gis ratings loaded: {len(ratings)}/{len(df)}")
    return ratings

def calc_comp_rating(df: pd.DataFrame, rts: Dict[int, float]) -> List[Optional[float]]:
    res = []
    logger.info("calc competitor ratings...")
    for idx, cafe in df.iterrows():
        tlon, tlat = cafe['lon'], cafe['lat']
        comp_rates = []
        for cidx, comp in df.iterrows():
            if cidx == idx:
                continue
            dist = h_dist(tlon, tlat, comp['lon'], comp['lat'])
            if dist < 300:
                cr = rts.get(cidx)
                if cr:
                    comp_rates.append(cr)
        if comp_rates:
            res.append(np.mean(comp_rates))
        else:
            res.append(None)
        if idx % 500 == 0 and idx > 0:
            logger.info(f"calc {idx}/{len(df)}")
    return res

def calc_metrics(cafe_df: pd.DataFrame, metro_df: pd.DataFrame, stops_df: pd.DataFrame) -> pd.DataFrame:
    metrics = []
    logger.info("calc location metrics...")
    for idx, cafe in cafe_df.iterrows():
        tlon, tlat = cafe['lon'], cafe['lat']
        c300 = 0
        c1k = 0
        for _, comp in cafe_df.iterrows():
            if comp['osm_id'] == cafe['osm_id']:
                continue
            dist = h_dist(tlon, tlat, comp['lon'], comp['lat'])
            if dist < 300:
                c300 += 1
            if dist < 1000:
                c1k += 1
        min_mdist = None
        if not metro_df.empty:
            for _, metro in metro_df.iterrows():
                dist = h_dist(tlon, tlat, metro['lon'], metro['lat'])
                if min_mdist is None or dist < min_mdist:
                    min_mdist = dist
        scount = 0
        if not stops_df.empty:
            for _, stop in stops_df.iterrows():
                dist = h_dist(tlon, tlat, stop['s_lon'], stop['s_lat'])
                if dist < 500:
                    scount += 1
        metrics.append({
            'c300': c300,
            'c1k': c1k,
            'dist_metro': min_mdist,
            'stops_cnt': scount
        })
        if idx % 500 == 0 and idx > 0:
            logger.info(f"metrics {idx}/{len(cafe_df)}")
    return pd.DataFrame(metrics)

def calc_office_dens(cafe_df: pd.DataFrame, off_df: pd.DataFrame) -> List[int]:
    cnts = []
    if off_df.empty:
        return [0] * len(cafe_df)
    for idx, cafe in cafe_df.iterrows():
        c = 0
        for _, off in off_df.iterrows():
            dist = h_dist(cafe['lon'], cafe['lat'], off['o_lon'], off['o_lat'])
            if dist < 500:
                c += 1
        cnts.append(c)
        if idx % 500 == 0 and idx > 0:
            logger.info(f"offices {idx}/{len(cafe_df)}")
    return cnts

def get_district(lat: float, lon: float) -> str:
    if 55.70 <= lat <= 55.80 and 37.55 <= lon <= 37.70:
        return 'CAO'
    elif lat > 55.80:
        if lon < 37.60:
            return 'SZAO'
        elif lon > 37.70:
            return 'SVAO'
        return 'SAO'
    elif lat > 55.75:
        if lon > 37.70:
            return 'SVAO'
        return 'SAO'
    elif lat < 55.60 and lon > 37.65:
        return 'UVAO'
    elif lat < 55.65:
        if lon < 37.55:
            return 'UZAO'
        return 'UAO'
    elif lat < 55.70 and lon < 37.55:
        return 'UZAO'
    elif lon < 37.45:
        return 'ZAO'
    elif lon > 37.75:
        return 'VAO'
    else:
        return 'CAO'

def load_district_stats() -> Tuple[dict, dict]:
    dist_data = {
        'CAO': {'pop_dens': 12500, 'income': 110000},
        'SAO': {'pop_dens': 9800, 'income': 95000},
        'SVAO': {'pop_dens': 10200, 'income': 92000},
        'VAO': {'pop_dens': 8900, 'income': 88000},
        'UVAO': {'pop_dens': 8500, 'income': 85000},
        'UAO': {'pop_dens': 9100, 'income': 87000},
        'UZAO': {'pop_dens': 10500, 'income': 98000},
        'ZAO': {'pop_dens': 8800, 'income': 96000},
        'SZAO': {'pop_dens': 9200, 'income': 94000}
    }
    rent_data = {
        'CAO': {'rent': 45000, 'avail': 342},
        'SAO': {'rent': 28000, 'avail': 187},
        'SVAO': {'rent': 25000, 'avail': 156},
        'VAO': {'rent': 23000, 'avail': 203},
        'UVAO': {'rent': 21000, 'avail': 178},
        'UAO': {'rent': 24000, 'avail': 192},
        'UZAO': {'rent': 29000, 'avail': 165},
        'ZAO': {'rent': 27000, 'avail': 149},
        'SZAO': {'rent': 26000, 'avail': 134}
    }
    return dist_data, rent_data

def main(api_key_2gis: Optional[str] = None) -> pd.DataFrame:
    logger.info("=== 2GIS COFFEE ANALYTICS ===\n")
    logger.info("1. loading cafes...")
    cafes = get_cafes()
    if cafes.empty:
        logger.error("no cafes found")
        return pd.DataFrame()
    logger.info(f"   found {len(cafes)} cafes")
    
    logger.info("\n2. loading metro...")
    metro = get_metro()
    logger.info(f"   found {len(metro)} stations")
    
    logger.info("\n3. loading stops...")
    stops = get_stops()
    logger.info(f"   found {len(stops)} stops")
    
    logger.info("\n4. loading offices...")
    offices = get_offices()
    logger.info(f"   found {len(offices)} offices")
    
    ratings = {}
    if api_key_2gis:
        logger.info("\n5. loading 2gis ratings...")
        ratings = get_2gis_ratings(cafes, api_key_2gis)
    else:
        logger.warning("\n5. no 2gis api key - ratings skipped")
    
    logger.info("\n6. calc location metrics...")
    mets = calc_metrics(cafes, metro, stops)
    enriched = pd.concat([cafes.reset_index(drop=True), mets], axis=1)
    
    logger.info("\n7. calc competitor ratings...")
    enriched['avg_comp_rating'] = calc_comp_rating(enriched, ratings)
    
    logger.info("\n8. calc office density...")
    enriched['office_dens'] = calc_office_dens(enriched, offices)
    
    logger.info("\n9. add district data...")
    dist_data, rent_data = load_district_stats()
    dists = [get_district(row['lat'], row['lon']) for _, row in enriched.iterrows()]
    enriched['district'] = dists
    enriched['pop_dens'] = enriched['district'].map(lambda d: dist_data.get(d, {}).get('pop_dens', 8000))
    enriched['income'] = enriched['district'].map(lambda d: dist_data.get(d, {}).get('income', 90000))
    enriched['avg_rent'] = enriched['district'].map(lambda d: rent_data.get(d, {}).get('rent', 25000))
    enriched['avail_space'] = enriched['district'].map(lambda d: rent_data.get(d, {}).get('avail', 150))
    
    logger.info("\n10. saving results...")
    out_cols = [
        'name', 'lat', 'lon', 'district', 'addr', 'avg_comp_rating',
        'dist_metro', 'stops_cnt', 'c300', 'c1k', 'pop_dens',
        'income', 'office_dens', 'avg_rent', 'avail_space'
    ]
    exist = [c for c in out_cols if c in enriched.columns]
    final = enriched[exist]
    final.to_csv('coffee_2gis.csv', index=False, encoding='utf-8-sig')
    
    logger.info(f"\n=== DONE ===")
    logger.info(f"saved {len(final)} cafes to coffee_2gis.csv")
    return final

if __name__ == "__main__":
    KEY = "083a49bc-a7e2-49dc-8eff-9d720d9e6cbc"
    df = main(api_key_2gis=KEY)