from fastapi import APIRouter


router = APIRouter()


@router.get("/")
async def root():
    return {
        "service": "market_service",
        "status": "ok",
    }


@router.get("/health")
async def health():
    return {
        "status": "healthy",
    }
