from fastapi import APIRouter, Depends

from src.core import CurrentUser, get_current_user
from src.schemas import ErrorResponse, IdeaParseRequest, IdeaParseResponse
from src.services.idea_parser_service import IdeaParserService


router = APIRouter(prefix="/api/v1/ideas", tags=["idea-parser"])


@router.post(
    "/parse",
    response_model=IdeaParseResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def parse_idea(
    payload: IdeaParseRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = IdeaParserService()
    return await service.parse_idea(payload)
