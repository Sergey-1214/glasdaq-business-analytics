from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from src.core import CurrentUser, get_current_user
from src.db.session import get_db
from src.schemas import (
    ErrorResponse,
    IdeaCreateRequest,
    IdeaResponse,
    IdeasResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportsResponse,
    ReportUpdateRequest,
)
from src.services.ideas_service import IdeasService


router = APIRouter(tags=["ideas", "reports"])


@router.post(
    "/ideas",
    response_model=IdeaResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_idea(
    payload: IdeaCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await IdeasService(db).create_idea(current_user.user_id, payload)


@router.get(
    "/ideas/me",
    response_model=IdeasResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_my_ideas(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).list_my_ideas(current_user.user_id)


@router.get(
    "/ideas/{idea_id}",
    response_model=IdeaResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).get_my_idea(current_user.user_id, idea_id)


@router.delete(
    "/ideas/{idea_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def delete_idea(
    idea_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    IdeasService(db).delete_my_idea(current_user.user_id, idea_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reports",
    response_model=ReportResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def create_report(
    payload: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).create_report(current_user.user_id, payload)


@router.post(
    "/reports/upload",
    response_model=ReportResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_report_with_file(
    idea_id: UUID = Form(...),
    format: str = Form(...),
    report_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await IdeasService(db).create_report_with_file(
        user_id=current_user.user_id,
        idea_id=idea_id,
        report_format=format,
        report_file=report_file,
    )


@router.get(
    "/reports/me",
    response_model=ReportsResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).list_my_reports(current_user.user_id)


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).get_my_report(current_user.user_id, report_id)


@router.patch(
    "/reports/{report_id}",
    response_model=ReportResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_report(
    report_id: UUID,
    payload: ReportUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return IdeasService(db).update_my_report(current_user.user_id, report_id, payload)


@router.patch(
    "/reports/{report_id}/upload",
    response_model=ReportResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def update_report_with_file(
    report_id: UUID,
    report_file: UploadFile = File(...),
    format: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await IdeasService(db).update_my_report_with_file(
        user_id=current_user.user_id,
        report_id=report_id,
        report_file=report_file,
        report_format=format,
    )


@router.delete(
    "/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def delete_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    IdeasService(db).delete_my_report(current_user.user_id, report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
