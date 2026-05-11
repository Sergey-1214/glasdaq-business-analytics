from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class IdeaParseRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None


class IdeaParseResponseData(BaseModel):
    language: str = 'unknown'
    normalized_idea: str = ''
    business_category: str = 'other'
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
    confidence: float = 0.0
    parser_source: str | None = None
    processing_time_ms: int | None = None

    @field_validator('target_audience', 'location_preferences', 'keywords', mode='before')
    @classmethod
    def coerce_none_to_list(cls, v):
        return v if v is not None else []

    @field_validator('confidence', mode='before')
    @classmethod
    def coerce_confidence(cls, v):
        if v is None:
            return 0.0
        try:
            f = float(str(v).replace('%', '').strip())
            return f / 100 if f > 1 else f
        except (ValueError, TypeError):
            return 0.0

    @model_validator(mode='before')
    @classmethod
    def coerce_fields(cls, values):
        if not isinstance(values, dict):
            return values
        # Model sometimes nests numeric fields inside location_preferences dict — extract them
        lp = values.get('location_preferences')
        if isinstance(lp, dict):
            for nested in ('max_rent_m2', 'min_pedestrian_traffic', 'min_metro_passenger_flow', 'preferred_distance_to_metro_m'):
                if nested in lp and values.get(nested) is None:
                    values[nested] = lp[nested]
            values['location_preferences'] = []
        # Coerce None to defaults for required string fields
        for field, default in (('language', 'unknown'), ('normalized_idea', ''), ('business_category', 'other')):
            if values.get(field) is None:
                values[field] = default
        # Coerce string → float for float | None fields
        for field in ('planned_average_check', 'max_rent_m2'):
            v = values.get(field)
            if v is not None and not isinstance(v, (int, float)):
                try:
                    values[field] = float(str(v).replace(' ', '').replace(',', '.'))
                except (ValueError, TypeError):
                    values[field] = None
        # Coerce string → int for int | None fields
        for field in ('min_pedestrian_traffic', 'min_metro_passenger_flow', 'preferred_distance_to_metro_m', 'processing_time_ms'):
            v = values.get(field)
            if v is not None and not isinstance(v, (int, float)):
                try:
                    values[field] = int(float(str(v).replace(' ', '').replace(',', '.')))
                except (ValueError, TypeError):
                    values[field] = None
        return values


class IdeaParseResponse(BaseModel):
    success: bool = True
    data: IdeaParseResponseData
