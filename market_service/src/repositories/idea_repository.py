from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Idea, Report


class IdeaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_idea(self, idea: Idea) -> Idea:
        self.db.add(idea)
        self.db.flush()
        self.db.refresh(idea)
        return idea

    def list_ideas_by_user(self, user_id: UUID) -> list[Idea]:
        stmt = select(Idea).where(Idea.user_id == user_id).order_by(Idea.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_idea_by_id_and_user(self, idea_id: UUID, user_id: UUID) -> Idea | None:
        stmt = select(Idea).where(Idea.id == idea_id, Idea.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_idea(self, idea: Idea) -> None:
        self.db.delete(idea)
        self.db.flush()

    def add_report(self, report: Report) -> Report:
        self.db.add(report)
        self.db.flush()
        self.db.refresh(report)
        return report

    def list_reports_by_user(self, user_id: UUID) -> list[Report]:
        stmt = select(Report).where(Report.user_id == user_id).order_by(Report.generated_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_report_by_id_and_user(self, report_id: UUID, user_id: UUID) -> Report | None:
        stmt = select(Report).where(Report.id == report_id, Report.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_report(self, report: Report) -> None:
        self.db.delete(report)
        self.db.flush()
