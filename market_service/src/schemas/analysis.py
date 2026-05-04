from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None


class CompetitorShare(BaseModel):
    name: str
    share: int


class AnalysisResponseData(BaseModel):
    tam: int
    sam: int
    som: int
    competitors: list[CompetitorShare]
    trend: str
    verdict: str


class AnalysisResponse(BaseModel):
    success: bool = True
    data: AnalysisResponseData
