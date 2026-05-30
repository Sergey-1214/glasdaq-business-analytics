from fastapi import APIRouter

from src.clients.ollama_client import OllamaClient


router = APIRouter()


@router.get("/")
async def root():
    return {"service": "product_service", "status": "ok"}


@router.get("/health")
async def health():
    client = OllamaClient()
    is_healthy = await client.health()
    if is_healthy:
        return {"status": "healthy", "ollama": "connected"}
    return {"status": "degraded", "ollama": "unavailable"}
