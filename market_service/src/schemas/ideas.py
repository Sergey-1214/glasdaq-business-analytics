from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .analysis import AnalysisResponseData
from .idea_parser import IdeaParseResponseData


class IdeaCreateRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None


class IdeaResponseData(BaseModel):
    id: UUID
    user_id: UUID
    idea_text: str
    normalized_title: str | None
    parsed_payload: IdeaParseResponseData
    analysis_payload: AnalysisResponseData
    created_at: datetime
    updated_at: datetime


class IdeaResponse(BaseModel):
    success: bool = True
    data: IdeaResponseData


class IdeasResponse(BaseModel):
    success: bool = True
    data: list[IdeaResponseData]
