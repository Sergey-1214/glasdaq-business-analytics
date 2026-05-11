from fastapi import FastAPI

app = FastAPI(
    title="Parsers Service",
    description="Data parsers service placeholder",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"service": "parsers", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
