from fastapi import FastAPI

from src.routes import health_router, ingestion_router


app = FastAPI(
    title="Market Service",
    description="Market analysis service placeholder",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(ingestion_router)
