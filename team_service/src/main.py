from fastapi import FastAPI


app = FastAPI(
    title="Team Service",
    description="Team recommendation service placeholder",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "service": "team_service",
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
