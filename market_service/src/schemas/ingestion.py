from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetroStationIngest(BaseModel):
    source: str = "mos_ru"
    station_name: str
    line_name: str | None = None
    passenger_flow: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class MarketPointMetricsIngest(BaseModel):
    distance_to_metro: float | None = None
    metro_passenger_flow: int | None = None
    public_transport_stops_count: int | None = None
    cafes_300m: int | None = None
    cafes_1km: int | None = None
    average_competitor_rating: float | None = None
    population_density: int | None = None
    median_income: int | None = None
    office_density: int | None = None
    average_rent_m2: float | None = None
    available_commercial_spaces: int | None = None
    pedestrian_traffic_estimate: int | None = None
    metrics_source_label: str | None = None


class MarketPointIngest(BaseModel):
    source: str = "osm"
    external_id: str
    external_type: str | None = None
    name: str | None = None
    category: str = "coffee_shop"
    latitude: float
    longitude: float
    rating: float | None = None
    raw_tags: dict[str, Any] | None = None
    metro_station: MetroStationIngest | None = None
    metrics: MarketPointMetricsIngest | None = None


class IngestionRequest(BaseModel):
    source: str = "parser"
    region: str
    records: list[MarketPointIngest] = Field(default_factory=list)
    notes: str | None = None


class IngestionResponse(BaseModel):
    success: bool = True
    batch_id: str
    records_received: int
    points_upserted: int
    metro_stations_upserted: int
    metrics_created: int
