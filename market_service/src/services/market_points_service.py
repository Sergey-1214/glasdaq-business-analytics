from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories import AnalysisRepository
from src.schemas import MarketPointResponseData


class MarketPointsService:
    def __init__(self, db: Session) -> None:
        self.repository = AnalysisRepository(db)

    def list_market_points(
        self,
        *,
        region: str,
        category: str,
        limit: int,
    ) -> list[MarketPointResponseData]:
        rows = self.repository.list_market_points_with_latest_metrics(region=region, category=category)

        return [
            MarketPointResponseData(
                id=str(point.id),
                name=point.name or "Без названия",
                category=point.category,
                latitude=float(point.latitude),
                longitude=float(point.longitude),
                rating=float(point.rating) if point.rating is not None else None,
                average_check=float(metric.average_check) if metric.average_check is not None else None,
                pedestrian_traffic_estimate=(
                    float(metric.pedestrian_traffic_estimate)
                    if metric.pedestrian_traffic_estimate is not None
                    else None
                ),
                metro_passenger_flow=(
                    float(metric.metro_passenger_flow)
                    if metric.metro_passenger_flow is not None
                    else None
                ),
                distance_to_metro=float(metric.distance_to_metro) if metric.distance_to_metro is not None else None,
                nearest_metro_station=(
                    metric.nearest_metro_station.station_name
                    if metric.nearest_metro_station is not None
                    else None
                ),
            )
            for point, metric in rows[:limit]
        ]
