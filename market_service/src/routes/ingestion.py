from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from src.core import CurrentUser, get_current_user
from src.db.session import get_db
from src.schemas import ErrorResponse, IngestionRequest, IngestionResponse
from src.services.ingestion_service import IngestionService


router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


@router.post(
    "/coffee-shops",
    response_model=IngestionResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def ingest_coffee_shops(
    payload: IngestionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = IngestionService(db)
    return service.ingest_coffee_shops(payload)


@router.post(
    "/coffee-shops/upload",
    response_model=IngestionResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def ingest_coffee_shops_file(
    region: str = Form(...),
    source: str = Form("upload"),
    category: str = Form("coffee_shop"),
    notes: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = IngestionService(db)
    file_bytes = await file.read()
    return service.ingest_uploaded_file(
        file_name=file.filename or "upload.csv",
        file_bytes=file_bytes,
        region=region,
        source=source,
        category=category,
        notes=notes,
    )
