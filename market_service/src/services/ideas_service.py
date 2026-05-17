from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.db.models import Idea, Report
from src.exceptions import NotFoundError
from src.repositories import IdeaRepository
from src.schemas import (
    AnalysisRequest,
    IdeaCreateRequest,
    IdeaResponse,
    IdeaResponseData,
    IdeasResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportResponseData,
    ReportsResponse,
    ReportUpdateRequest,
)
from src.services.analysis_service import AnalysisService


class IdeasService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = IdeaRepository(db)
        self.analysis_service = AnalysisService(db)

    async def create_idea(self, user_id: UUID, payload: IdeaCreateRequest) -> IdeaResponse:
        analysis_request = AnalysisRequest(idea=payload.idea, region=payload.region)
        parsed = await self.analysis_service._parse_idea(analysis_request)
        analysis = await self.analysis_service.analyze(analysis_request)

        idea = Idea(
            user_id=user_id,
            idea_text=payload.idea,
            normalized_title=parsed.normalized_idea[:255] if parsed.normalized_idea else None,
            parsed_payload=parsed.model_dump(),
            analysis_payload=analysis.data.model_dump(),
        )
        self.repository.add_idea(idea)
        self.db.commit()
        return IdeaResponse(data=self._idea_to_schema(idea))

    def list_my_ideas(self, user_id: UUID) -> IdeasResponse:
        ideas = self.repository.list_ideas_by_user(user_id)
        return IdeasResponse(data=[self._idea_to_schema(idea) for idea in ideas])

    def get_my_idea(self, user_id: UUID, idea_id: UUID) -> IdeaResponse:
        idea = self.repository.get_idea_by_id_and_user(idea_id, user_id)
        if idea is None:
            raise NotFoundError("Idea not found")
        return IdeaResponse(data=self._idea_to_schema(idea))

    def delete_my_idea(self, user_id: UUID, idea_id: UUID) -> None:
        idea = self.repository.get_idea_by_id_and_user(idea_id, user_id)
        if idea is None:
            raise NotFoundError("Idea not found")
        self.repository.delete_idea(idea)
        self.db.commit()

    def create_report(self, user_id: UUID, payload: ReportCreateRequest) -> ReportResponse:
        idea = self.repository.get_idea_by_id_and_user(payload.idea_id, user_id)
        if idea is None:
            raise NotFoundError("Idea not found")

        report_payload = payload.report_payload or {}
        report = Report(
            idea_id=payload.idea_id,
            user_id=user_id,
            format=payload.format,
            file_url=None,
            report_payload=report_payload,
        )
        self.repository.add_report(report)
        report.file_url = self._persist_report_payload(report.id, report_payload)
        self.db.commit()
        return ReportResponse(data=self._report_to_schema(report))

    async def create_report_with_file(
        self,
        user_id: UUID,
        idea_id: UUID,
        report_format: str,
        report_file: UploadFile,
    ) -> ReportResponse:
        idea = self.repository.get_idea_by_id_and_user(idea_id, user_id)
        if idea is None:
            raise NotFoundError("Idea not found")

        report = Report(
            idea_id=idea_id,
            user_id=user_id,
            format=report_format,
            file_url=None,
            report_payload=None,
        )
        self.repository.add_report(report)
        report.file_url = await self._persist_uploaded_file(report.id, report_file)
        self.db.commit()
        return ReportResponse(data=self._report_to_schema(report))

    def list_my_reports(self, user_id: UUID) -> ReportsResponse:
        reports = self.repository.list_reports_by_user(user_id)
        return ReportsResponse(data=[self._report_to_schema(report) for report in reports])

    def get_my_report(self, user_id: UUID, report_id: UUID) -> ReportResponse:
        report = self.repository.get_report_by_id_and_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        return ReportResponse(data=self._report_to_schema(report))

    def update_my_report(self, user_id: UUID, report_id: UUID, payload: ReportUpdateRequest) -> ReportResponse:
        report = self.repository.get_report_by_id_and_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(report, key, value)
        if "report_payload" in data:
            report.file_url = self._persist_report_payload(report.id, report.report_payload or {})
        self.db.commit()
        self.db.refresh(report)
        return ReportResponse(data=self._report_to_schema(report))

    async def update_my_report_with_file(
        self,
        user_id: UUID,
        report_id: UUID,
        report_file: UploadFile,
        report_format: str | None = None,
    ) -> ReportResponse:
        report = self.repository.get_report_by_id_and_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        if report_format is not None:
            report.format = report_format

        report.report_payload = None
        report.file_url = await self._persist_uploaded_file(report.id, report_file)
        self.db.commit()
        self.db.refresh(report)
        return ReportResponse(data=self._report_to_schema(report))

    def delete_my_report(self, user_id: UUID, report_id: UUID) -> None:
        report = self.repository.get_report_by_id_and_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        self.repository.delete_report(report)
        self.db.commit()

    def _idea_to_schema(self, idea: Idea) -> IdeaResponseData:
        return IdeaResponseData(
            id=idea.id,
            user_id=idea.user_id,
            idea_text=idea.idea_text,
            normalized_title=idea.normalized_title,
            parsed_payload=idea.parsed_payload,
            analysis_payload=idea.analysis_payload,
            created_at=idea.created_at,
            updated_at=idea.updated_at,
        )

    def _report_to_schema(self, report: Report) -> ReportResponseData:
        return ReportResponseData(
            id=report.id,
            idea_id=report.idea_id,
            user_id=report.user_id,
            format=report.format,
            generated_at=report.generated_at,
            file_url=report.file_url,
            report_payload=report.report_payload,
        )

    def _persist_report_payload(self, report_id: UUID, report_payload: dict) -> str:
        storage_dir = self._resolve_storage_dir()
        public_base_path = os.getenv("REPORTS_PUBLIC_BASE_PATH", "/reports/files").rstrip("/")

        file_name = f"{report_id}.json"
        file_path = storage_dir / file_name
        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(report_payload, file_obj, ensure_ascii=False, indent=2)

        return f"{public_base_path}/{file_name}"

    async def _persist_uploaded_file(self, report_id: UUID, report_file: UploadFile) -> str:
        storage_dir = self._resolve_storage_dir()
        public_base_path = os.getenv("REPORTS_PUBLIC_BASE_PATH", "/reports/files").rstrip("/")

        original_ext = Path(report_file.filename or "").suffix
        safe_ext = original_ext if original_ext and len(original_ext) <= 10 else ".bin"
        file_name = f"{report_id}{safe_ext.lower()}"
        file_path = storage_dir / file_name

        content = await report_file.read()
        with file_path.open("wb") as file_obj:
            file_obj.write(content)

        return f"{public_base_path}/{file_name}"

    def _resolve_storage_dir(self) -> Path:
        preferred = Path(os.getenv("REPORTS_STORAGE_DIR", "/app/storage/reports"))
        fallback = Path("/tmp")
        for candidate in (preferred, fallback):
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                marker = candidate / ".write_test"
                marker.write_text("ok", encoding="utf-8")
                marker.unlink(missing_ok=True)
                return candidate
            except OSError:
                continue
        raise PermissionError("No writable storage directory for reports")
