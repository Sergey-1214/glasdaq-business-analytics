from fastapi import APIRouter, Depends

from src.core import CurrentUser, get_current_user
from src.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from src.services import AnalysisService

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze(
    payload: AnalyzeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = AnalysisService()
    return await service.analyze(payload)
