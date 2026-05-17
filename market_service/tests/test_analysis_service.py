from types import SimpleNamespace
import asyncio

from src.schemas import IdeaParseResponse, IdeaParseResponseData
from src.services.analysis_service import AnalysisService


class StubRepository:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def list_market_points_with_latest_metrics(self, region: str, category: str):
        self.calls.append((region, category))
        return self.rows

    def find_metro_station_coordinates(self, region: str, station_hint: str):
        return None


class StubParser:
    def __init__(self, parsed_data: IdeaParseResponseData):
        self.parsed_data = parsed_data

    async def parse_idea(self, payload):
        return IdeaParseResponse(data=self.parsed_data)


def make_row(
    name: str,
    *,
    rating: float,
    pedestrian: int,
    metro_flow: int,
    metro_distance: int,
    cafes_300m: int,
    cafes_1km: int,
    competitor_rating: float,
    population_density: int,
    median_income: int,
    office_density: int,
    average_rent_m2: float,
    average_check: float,
    available_spaces: int,
    latitude: float = 55.75,
    longitude: float = 37.62,
):
    point = SimpleNamespace(name=name, rating=rating, latitude=latitude, longitude=longitude)
    metric = SimpleNamespace(
        pedestrian_traffic_estimate=pedestrian,
        metro_passenger_flow=metro_flow,
        distance_to_metro=metro_distance,
        cafes_300m=cafes_300m,
        cafes_1km=cafes_1km,
        average_competitor_rating=competitor_rating,
        population_density=population_density,
        median_income=median_income,
        office_density=office_density,
        average_rent_m2=average_rent_m2,
        average_check=average_check,
        available_commercial_spaces=available_spaces,
    )
    return point, metric


def build_service(parsed_data, rows):
    service = AnalysisService(db=None)
    service.repository = StubRepository(rows)
    service.idea_parser = StubParser(parsed_data)
    return service


def test_center_vs_outskirts_produce_different_results():
    rows = [
        make_row(
            "Central Hub",
            rating=4.8,
            pedestrian=2500,
            metro_flow=180000,
            metro_distance=120,
            cafes_300m=15,
            cafes_1km=40,
            competitor_rating=4.6,
            population_density=14000,
            median_income=210000,
            office_density=17000,
            average_rent_m2=12000,
            average_check=520,
            available_spaces=4,
        ),
        make_row(
            "West Corner",
            rating=4.2,
            pedestrian=800,
            metro_flow=40000,
            metro_distance=900,
            cafes_300m=3,
            cafes_1km=9,
            competitor_rating=4.0,
            population_density=7000,
            median_income=110000,
            office_density=3500,
            average_rent_m2=5200,
            average_check=360,
            available_spaces=11,
        ),
    ]

    center_parsed = IdeaParseResponseData(
        normalized_idea="Кафе в центре Москвы",
        business_category="Кофейня",
        location_preferences=["центр города", "рядом с метро"],
        target_audience=["офисные сотрудники"],
        region="Moscow",
        confidence=0.9,
    )
    outskirts_parsed = IdeaParseResponseData(
        normalized_idea="Кафе на западной окраине Москвы",
        business_category="Кофейня",
        location_preferences=["западная окраина"],
        target_audience=[],
        region="Moscow",
        confidence=0.9,
    )

    center_service = build_service(center_parsed, rows)
    outskirts_service = build_service(outskirts_parsed, rows)

    center_result = asyncio.run(center_service.analyze(SimpleNamespace(idea="Кафе в центре Москвы", region="Moscow")))
    outskirts_result = asyncio.run(
        outskirts_service.analyze(SimpleNamespace(idea="Кафе на западной окраине Москвы", region="Moscow"))
    )

    assert center_result.data.sam != outskirts_result.data.sam
    assert center_result.data.som != outskirts_result.data.som
    assert center_result.data.competitors[0].name != outskirts_result.data.competitors[0].name


def test_analysis_uses_parsed_region_and_category():
    rows = [
        make_row(
            "Metro Coffee",
            rating=4.5,
            pedestrian=1200,
            metro_flow=70000,
            metro_distance=250,
            cafes_300m=8,
            cafes_1km=16,
            competitor_rating=4.2,
            population_density=9000,
            median_income=130000,
            office_density=8000,
            average_rent_m2=7000,
            average_check=400,
            available_spaces=5,
        ),
    ]

    parsed = IdeaParseResponseData(
        normalized_idea="Кофейня у метро",
        business_category="Кофейня",
        location_preferences=["рядом с метро"],
        region="Moscow",
        confidence=0.8,
    )
    service = build_service(parsed, rows)

    asyncio.run(service.analyze(SimpleNamespace(idea="Кофейня у метро", region="Moscow")))

    assert service.repository.calls == [("Moscow", "coffee_shop")]
