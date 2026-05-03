from fastapi import APIRouter

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
async def parse_idea(payload: IdeaParseRequest):
    service = IdeaParserService()
    return await service.parse_idea(payload)
