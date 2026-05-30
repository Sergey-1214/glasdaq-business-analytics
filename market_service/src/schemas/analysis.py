from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None
    selected_latitude: float | None = None
    selected_longitude: float | None = None


class CompetitorShare(BaseModel):
    name: str
    share: int


class LocationAssessment(BaseModel):
    latitude: float
    longitude: float
    nearest_competitor_name: str | None = None
    nearest_competitor_distance_m: int | None = None
    competitors_within_500m: int = 0
    competitors_within_1km: int = 0
    pedestrian_traffic_estimate: int | None = None
    metro_passenger_flow: int | None = None
    average_rent_m2: int | None = None
    average_check: int | None = None
    median_income: int | None = None
    opportunity_score: int = 0
    verdict: str
    summary: str


class AnalysisResponseData(BaseModel):
    tam: int
    sam: int
    som: int
    competitors: list[CompetitorShare]
    trend: str
    verdict: str
    location_assessment: LocationAssessment | None = None


class AnalysisResponse(BaseModel):
    success: bool = True
    data: AnalysisResponseData
