import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.exceptions import AppError
from src.routes import analysis_router, health_router, idea_parser_router, ideas_router, ingestion_router
from src.schemas import ErrorResponse


app = FastAPI(
    title="Market Service",
    description="Market analysis service placeholder",
    version="1.0.0",
)

reports_storage_dir = os.getenv("REPORTS_STORAGE_DIR", "/app/storage/reports")
reports_public_base_path = os.getenv("REPORTS_PUBLIC_BASE_PATH", "/reports/files")
fallback_reports_storage_dir = "/tmp"
try:
    os.makedirs(reports_storage_dir, exist_ok=True)
    test_path = os.path.join(reports_storage_dir, ".write_test")
    with open(test_path, "w", encoding="utf-8") as marker:
        marker.write("ok")
    os.remove(test_path)
except OSError:
    reports_storage_dir = fallback_reports_storage_dir
    os.makedirs(reports_storage_dir, exist_ok=True)

app.mount(reports_public_base_path, StaticFiles(directory=reports_storage_dir), name="report-files")


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


app.include_router(analysis_router)
app.include_router(health_router)
app.include_router(idea_parser_router)
app.include_router(ingestion_router)
app.include_router(ideas_router)
