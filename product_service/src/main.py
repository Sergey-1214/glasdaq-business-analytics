from fastapi import FastAPI

app = FastAPI(
    title="Product Service",
    description="Product analysis service placeholder",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"service": "product_service", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
