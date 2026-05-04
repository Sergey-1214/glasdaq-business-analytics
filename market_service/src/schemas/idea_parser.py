from __future__ import annotations

from pydantic import BaseModel, Field


class IdeaParseRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None


class IdeaParseResponseData(BaseModel):
    language: str
    normalized_idea: str
    business_category: str
    subcategory: str | None = None
    business_model: str | None = None
    offering_type: str | None = None
    price_segment: str | None = None
    target_audience: list[str] = Field(default_factory=list)
    region: str | None = None
    location_preferences: list[str] = Field(default_factory=list)
    planned_average_check: float | None = None
    max_rent_m2: float | None = None
    min_pedestrian_traffic: int | None = None
    min_metro_passenger_flow: int | None = None
    preferred_distance_to_metro_m: int | None = None
    customer_problem: str | None = None
    keywords: list[str] = Field(default_factory=list)
    confidence: float
    parser_source: str | None = None
    processing_time_ms: int | None = None


class IdeaParseResponse(BaseModel):
    success: bool = True
    data: IdeaParseResponseData
