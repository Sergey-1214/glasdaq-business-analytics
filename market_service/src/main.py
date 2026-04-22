from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions import AppError
from src.routes import health_router, ingestion_router
from src.schemas import ErrorResponse


app = FastAPI(
    title="Market Service",
    description="Market analysis service placeholder",
    version="1.0.0",
)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error_code=exc.error_code, detail=exc.message).model_dump(),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="internal_server_error",
            detail=f"Unexpected server error: {exc}",
        ).model_dump(),
    )


app.include_router(health_router)
app.include_router(ingestion_router)
