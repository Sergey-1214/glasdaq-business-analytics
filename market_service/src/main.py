from fastapi import FastAPI


app = FastAPI(
    title="Market Service",
    description="Market analysis service placeholder",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "service": "market_service",
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
