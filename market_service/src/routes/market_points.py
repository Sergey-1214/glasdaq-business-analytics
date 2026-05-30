from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core import CurrentUser, get_current_user
from src.db.session import get_db
from src.schemas import ErrorResponse, MarketPointsResponse
from src.services.market_points_service import MarketPointsService


router = APIRouter(prefix="/api/v1", tags=["market-points"])


@router.get(
    "/market-points",
    response_model=MarketPointsResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_market_points(
    region: str = Query(default="Moscow"),
    category: str = Query(default="coffee_shop"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _ = current_user
    data = MarketPointsService(db).list_market_points(region=region, category=category, limit=limit)
    return MarketPointsResponse(data=data)
