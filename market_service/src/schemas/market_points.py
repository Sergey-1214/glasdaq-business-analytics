from __future__ import annotations

from pydantic import BaseModel


class MarketPointResponseData(BaseModel):
    id: str
    name: str
    category: str
    latitude: float
    longitude: float
    rating: float | None
    average_check: float | None
    pedestrian_traffic_estimate: float | None
    metro_passenger_flow: float | None
    distance_to_metro: float | None
    nearest_metro_station: str | None


class MarketPointsResponse(BaseModel):
    success: bool = True
    data: list[MarketPointResponseData]
