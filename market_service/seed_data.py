"""
Seed script: inserts sample Moscow market points for development.
Run with: python seed_data.py
"""
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.db.session import normalize_database_url

DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/glasdaq_db")
)

engine = create_engine(DATABASE_URL)

# ---------------------------------------------------------------------------
# Raw seed data: (name, category, lat, lon, rating, metrics_dict)
# category must match what analysis_service uses as DB key
# ---------------------------------------------------------------------------
POINTS = [
    # --- Кофейни / coffee_shop ---
    ("Кофемания на Тверской",       "coffee_shop",   55.7625, 37.6095, 4.5,
     dict(distance_to_metro=120, metro_passenger_flow=95000, cafes_300m=8,  cafes_1km=42, avg_comp_rating=4.2, pop_density=18000, median_income=95000, office_density=75, avg_rent=180000, avg_check=620, pedestrian=32000, avail_spaces=4)),
    ("Даблби Никольская",           "coffee_shop",   55.7553, 37.6228, 4.7,
     dict(distance_to_metro=80,  metro_passenger_flow=120000,cafes_300m=12, cafes_1km=60, avg_comp_rating=4.4, pop_density=16000, median_income=105000,office_density=80, avg_rent=220000, avg_check=580, pedestrian=45000, avail_spaces=2)),
    ("Black Market Арбат",          "coffee_shop",   55.7516, 37.5938, 4.3,
     dict(distance_to_metro=200, metro_passenger_flow=72000, cafes_300m=10, cafes_1km=38, avg_comp_rating=4.1, pop_density=14000, median_income=90000, office_density=55, avg_rent=160000, avg_check=550, pedestrian=28000, avail_spaces=3)),
    ("Surf Coffee Патриаршие",      "coffee_shop",   55.7637, 37.5979, 4.6,
     dict(distance_to_metro=450, metro_passenger_flow=55000, cafes_300m=6,  cafes_1km=29, avg_comp_rating=4.3, pop_density=12000, median_income=115000,office_density=40, avg_rent=190000, avg_check=700, pedestrian=18000, avail_spaces=2)),
    ("Skuratov Хохловка",           "coffee_shop",   55.7580, 37.6410, 4.4,
     dict(distance_to_metro=350, metro_passenger_flow=48000, cafes_300m=5,  cafes_1km=25, avg_comp_rating=4.0, pop_density=11000, median_income=88000, office_density=60, avg_rent=130000, avg_check=490, pedestrian=15000, avail_spaces=5)),

    # --- Доставка еды / food_delivery ---
    ("Кухня на районе (Хамовники)", "food_delivery", 55.7310, 37.5740, 4.2,
     dict(distance_to_metro=600, metro_passenger_flow=40000, cafes_300m=3,  cafes_1km=18, avg_comp_rating=3.8, pop_density=9000,  median_income=98000, office_density=30, avg_rent=90000,  avg_check=1100,pedestrian=8000,  avail_spaces=6)),
    ("Delivery Club (Сокольники)",  "food_delivery", 55.7897, 37.6766, 3.9,
     dict(distance_to_metro=300, metro_passenger_flow=62000, cafes_300m=4,  cafes_1km=22, avg_comp_rating=3.7, pop_density=10000, median_income=72000, office_density=20, avg_rent=70000,  avg_check=950, pedestrian=12000, avail_spaces=8)),
    ("Яндекс Еда (Митино)",         "food_delivery", 55.8366, 37.3524, 3.8,
     dict(distance_to_metro=250, metro_passenger_flow=45000, cafes_300m=2,  cafes_1km=12, avg_comp_rating=3.6, pop_density=14000, median_income=68000, office_density=15, avg_rent=55000,  avg_check=880, pedestrian=9000,  avail_spaces=10)),
    ("Самокат (Выхино)",            "food_delivery", 55.7204, 37.8178, 3.7,
     dict(distance_to_metro=180, metro_passenger_flow=55000, cafes_300m=3,  cafes_1km=14, avg_comp_rating=3.5, pop_density=13000, median_income=65000, office_density=12, avg_rent=48000,  avg_check=820, pedestrian=10000, avail_spaces=9)),
    ("GoodFood (Коньково)",         "food_delivery", 55.6340, 37.5150, 4.0,
     dict(distance_to_metro=400, metro_passenger_flow=38000, cafes_300m=2,  cafes_1km=10, avg_comp_rating=3.8, pop_density=12000, median_income=80000, office_density=18, avg_rent=60000,  avg_check=980, pedestrian=7000,  avail_spaces=7)),

    # --- Рестораны / restaurant ---
    ("Белый кролик",                "restaurant",    55.7740, 37.5858, 4.8,
     dict(distance_to_metro=500, metro_passenger_flow=50000, cafes_300m=7,  cafes_1km=30, avg_comp_rating=4.5, pop_density=13000, median_income=120000,office_density=50, avg_rent=200000, avg_check=2800,pedestrian=20000, avail_spaces=2)),
    ("Матрёшка",                    "restaurant",    55.7525, 37.6135, 4.6,
     dict(distance_to_metro=150, metro_passenger_flow=88000, cafes_300m=14, cafes_1km=55, avg_comp_rating=4.3, pop_density=17000, median_income=110000,office_density=70, avg_rent=240000, avg_check=2200,pedestrian=38000, avail_spaces=1)),
    ("Бараshка",                    "restaurant",    55.7617, 37.5895, 4.5,
     dict(distance_to_metro=220, metro_passenger_flow=65000, cafes_300m=9,  cafes_1km=40, avg_comp_rating=4.2, pop_density=15000, median_income=105000,office_density=65, avg_rent=175000, avg_check=1900,pedestrian=26000, avail_spaces=3)),
    ("Twins Garden",                "restaurant",    55.7572, 37.6302, 4.9,
     dict(distance_to_metro=280, metro_passenger_flow=72000, cafes_300m=11, cafes_1km=48, avg_comp_rating=4.4, pop_density=16000, median_income=115000,office_density=72, avg_rent=210000, avg_check=3500,pedestrian=30000, avail_spaces=2)),
    ("Нихао (Ленинский)",           "restaurant",    55.7118, 37.5748, 4.3,
     dict(distance_to_metro=380, metro_passenger_flow=42000, cafes_300m=5,  cafes_1km=20, avg_comp_rating=4.0, pop_density=11000, median_income=92000, office_density=40, avg_rent=120000, avg_check=1600,pedestrian=14000, avail_spaces=4)),

    # --- Фитнес / fitness ---
    ("World Class Тверская",        "fitness",       55.7673, 37.6061, 4.4,
     dict(distance_to_metro=100, metro_passenger_flow=95000, cafes_300m=6,  cafes_1km=35, avg_comp_rating=4.1, pop_density=16000, median_income=100000,office_density=70, avg_rent=170000, avg_check=8500,pedestrian=30000, avail_spaces=2)),
    ("Crocus Fitness (Строгино)",   "fitness",       55.8138, 37.3684, 4.2,
     dict(distance_to_metro=320, metro_passenger_flow=42000, cafes_300m=2,  cafes_1km=10, avg_comp_rating=3.9, pop_density=10000, median_income=78000, office_density=15, avg_rent=80000,  avg_check=6000,pedestrian=8000,  avail_spaces=5)),
    ("Gimnasium (Бутово)",          "fitness",       55.5690, 37.5910, 4.0,
     dict(distance_to_metro=480, metro_passenger_flow=35000, cafes_300m=1,  cafes_1km=7,  avg_comp_rating=3.7, pop_density=13000, median_income=70000, office_density=10, avg_rent=55000,  avg_check=4500,pedestrian=6000,  avail_spaces=7)),

    # --- Аптеки / pharmacy ---
    ("Ригла Новый Арбат",           "pharmacy",      55.7518, 37.5918, 4.1,
     dict(distance_to_metro=180, metro_passenger_flow=70000, cafes_300m=8,  cafes_1km=38, avg_comp_rating=4.0, pop_density=15000, median_income=98000, office_density=60, avg_rent=150000, avg_check=850, pedestrian=25000, avail_spaces=3)),
    ("Аптека 36.6 Таганская",       "pharmacy",      55.7395, 37.6568, 4.0,
     dict(distance_to_metro=90,  metro_passenger_flow=58000, cafes_300m=5,  cafes_1km=24, avg_comp_rating=3.9, pop_density=12000, median_income=82000, office_density=45, avg_rent=110000, avg_check=780, pedestrian=18000, avail_spaces=4)),
    ("Горздрав (Бибирево)",         "pharmacy",      55.8879, 37.6408, 3.8,
     dict(distance_to_metro=200, metro_passenger_flow=48000, cafes_300m=2,  cafes_1km=9,  avg_comp_rating=3.6, pop_density=16000, median_income=62000, office_density=8,  avg_rent=45000,  avg_check=690, pedestrian=11000, avail_spaces=6)),

    # --- IT-сервисы / it_service ---
    ("Яндекс (Красная Роза)",       "it_service",    55.7336, 37.5882, 4.7,
     dict(distance_to_metro=250, metro_passenger_flow=52000, cafes_300m=4,  cafes_1km=20, avg_comp_rating=4.5, pop_density=10000, median_income=140000,office_density=90, avg_rent=260000, avg_check=15000,pedestrian=15000,avail_spaces=1)),
    ("Сбертех (Кутузовский)",       "it_service",    55.7436, 37.5375, 4.4,
     dict(distance_to_metro=180, metro_passenger_flow=60000, cafes_300m=3,  cafes_1km=16, avg_comp_rating=4.2, pop_density=9000,  median_income=135000,office_density=85, avg_rent=240000, avg_check=12000,pedestrian=12000,avail_spaces=2)),
]


def already_seeded(session: Session) -> bool:
    result = session.execute(text("SELECT COUNT(*) FROM market_points")).scalar()
    return (result or 0) > 0


def seed(session: Session) -> None:
    if already_seeded(session):
        print("Seed data already present, skipping.")
        return

    batch_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    session.execute(text("""
        INSERT INTO ingestion_batches (id, source, region, started_at, finished_at, status, records_received)
        VALUES (:id, :source, :region, :started_at, :finished_at, :status, :records)
    """), {"id": str(batch_id), "source": "seed", "region": "Москва",
           "started_at": now, "finished_at": now, "status": "completed",
           "records": len(POINTS)})

    for name, category, lat, lon, rating, m in POINTS:
        point_id = uuid.uuid4()
        session.execute(text("""
            INSERT INTO market_points
              (id, batch_id, source, external_id, external_type, name, category, latitude, longitude, rating)
            VALUES (:id, :batch_id, :source, :ext_id, :ext_type, :name, :category, :lat, :lon, :rating)
        """), {
            "id": str(point_id), "batch_id": str(batch_id), "source": "seed",
            "ext_id": str(point_id), "ext_type": "place",
            "name": name, "category": category, "lat": lat, "lon": lon, "rating": rating,
        })

        session.execute(text("""
            INSERT INTO market_point_metrics
              (id, market_point_id, batch_id,
               distance_to_metro, metro_passenger_flow, cafes_300m, cafes_1km,
               average_competitor_rating, population_density, median_income,
               office_density, average_rent_m2, average_check,
               pedestrian_traffic_estimate, available_commercial_spaces,
               metrics_source_label)
            VALUES
              (:id, :point_id, :batch_id,
               :dist, :flow, :c300, :c1km,
               :comp_rating, :pop_density, :income,
               :office, :rent, :check_,
               :pedestrian, :avail,
               :label)
        """), {
            "id": str(uuid.uuid4()), "point_id": str(point_id), "batch_id": str(batch_id),
            "dist":     m["distance_to_metro"],
            "flow":     m["metro_passenger_flow"],
            "c300":     m["cafes_300m"],
            "c1km":     m["cafes_1km"],
            "comp_rating": m["avg_comp_rating"],
            "pop_density": m["pop_density"],
            "income":   m["median_income"],
            "office":   m["office_density"],
            "rent":     m["avg_rent"],
            "check_":   m["avg_check"],
            "pedestrian": m["pedestrian"],
            "avail":    m["avail_spaces"],
            "label":    "seed",
        })

    session.commit()
    print(f"Seeded {len(POINTS)} market points.")


if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
