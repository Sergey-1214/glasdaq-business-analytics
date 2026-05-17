from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core import CurrentUser, get_current_user
from src.db.session import get_db
from src.schemas import AnalysisRequest, AnalysisResponse, ErrorResponse
from src.services.analysis_service import AnalysisService


router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/anal",
    response_model=AnalysisResponse,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze_market(
    payload: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = AnalysisService(db)
    return await service.analyze(payload)
