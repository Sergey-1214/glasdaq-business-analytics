from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    idea_id: UUID
    format: str = Field(min_length=1, max_length=50)
    report_payload: dict | None = None


class ReportUpdateRequest(BaseModel):
    format: str | None = Field(default=None, min_length=1, max_length=50)
    report_payload: dict | None = None


class ReportResponseData(BaseModel):
    id: UUID
    idea_id: UUID
    user_id: UUID
    format: str
    generated_at: datetime
    file_url: str | None
    report_payload: dict | None


class ReportResponse(BaseModel):
    success: bool = True
    data: ReportResponseData


class ReportsResponse(BaseModel):
    success: bool = True
    data: list[ReportResponseData]
