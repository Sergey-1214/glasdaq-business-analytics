from fastapi import FastAPI


app = FastAPI(
    title="Orchestrator Service",
    description="Request orchestration service placeholder",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "service": "orchestrator",
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
