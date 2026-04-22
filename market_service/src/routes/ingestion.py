from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas import IngestionRequest, IngestionResponse
from src.services import IngestionService


router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


@router.post("/coffee-shops", response_model=IngestionResponse)
def ingest_coffee_shops(payload: IngestionRequest, db: Session = Depends(get_db)):
    service = IngestionService(db)
    return service.ingest_coffee_shops(payload)
