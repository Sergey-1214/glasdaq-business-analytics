from fastapi import APIRouter, Depends

from src.core import CurrentUser, get_current_user
from src.schemas import AnalysisRequest, AnalysisResponse, ErrorResponse
from src.services.analysis_service import AnalysisService


router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def analyze_product(
    payload: AnalysisRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = AnalysisService()
    return await service.analyze(payload)
