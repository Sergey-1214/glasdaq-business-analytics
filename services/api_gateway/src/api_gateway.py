import logging
from datetime import datetime
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from config import SERVICES, PORT, DEBUG, API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

app = FastAPI(title="Glasdaq API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = httpx.AsyncClient(timeout=30.0)

def check_api_key(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return True
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.2f}s)")
    return response

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(service: str, path: str, request: Request):
    check_api_key(request)
    
    if service not in SERVICES:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found. Available: {list(SERVICES.keys())}"
        )
    
    target_url = f"{SERVICES[service]}/{path}"
    body = await request.body()
    
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("authorization", None)
    
    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Service {service} is unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal gateway error")

@app.get("/health")
async def health():
    result = {"gateway": "ok", "services": {}, "timestamp": datetime.utcnow().isoformat()}
    all_ok = True
    
    for name, url in SERVICES.items():
        try:
            resp = await client.get(f"{url}/health", timeout=2.0)
            result["services"][name] = "ok" if resp.status_code == 200 else "error"
            if resp.status_code != 200:
                all_ok = False
        except:
            result["services"][name] = "unreachable"
            all_ok = False
    
    result["overall"] = "ok" if all_ok else "degraded"
    return result

@app.get("/routes")
async def routes():
    return {
        "services": list(SERVICES.keys()),
        "examples": [f"/api/{s}/some-endpoint" for s in SERVICES.keys()]
    }

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()