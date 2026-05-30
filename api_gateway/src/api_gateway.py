import logging
from datetime import datetime
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from .config import SERVICES, PORT, DEBUG, API_KEY
import json
import os
from typing import Dict, List, Optional
import uuid

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

client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0))

# ========== КОНФИГУРАЦИЯ ДЛЯ ХРАНЕНИЯ ОТЧЕТОВ ==========
# Используем отдельный том market-reports-data
REPORTS_DIR = os.getenv("REPORTS_DIR", "/app/reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Helper funcs

def check_api_key(request: Request):
    api_key = request.headers.get("x-api-key")
    if api_key:
        if api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True

    auth_header = request.headers.get("authorization")
    if auth_header:
        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() == "bearer" and token == API_KEY:
            return True

    return True

def get_user_id_from_request(request: Request) -> Optional[str]:
    """Извлекает user_id из JWT токена или заголовка"""
    # Вариант 1: Из заголовка x-user-id (для тестирования)
    user_id = request.headers.get("x-user-id")
    if user_id:
        return user_id
    
    # Вариант 2: Из JWT токена (через user_auth_service)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Здесь можно декодировать JWT или вызвать user_auth_service
        # Для простоты пока возвращаем None и полагаемся на x-user-id
        pass
    
    return None

def save_report_to_file(user_id: str, report_data: Dict) -> str:
    """Сохраняет отчет в файл и возвращает report_id"""
    report_id = str(uuid.uuid4())
    user_dir = os.path.join(REPORTS_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    
    report_file = os.path.join(user_dir, f"{report_id}.json")
    
    report_with_metadata = {
        "report_id": report_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "data": report_data
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_with_metadata, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Report saved: {report_id} for user {user_id}")
    return report_id

def get_user_reports(user_id: str) -> List[Dict]:
    """Получает список всех отчетов пользователя"""
    user_dir = os.path.join(REPORTS_DIR, user_id)
    if not os.path.exists(user_dir):
        return []
    
    reports = []
    for filename in os.listdir(user_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(user_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    reports.append({
                        "report_id": report.get("report_id"),
                        "created_at": report.get("created_at"),
                        "user_id": report.get("user_id")
                    })
            except Exception as e:
                logger.error(f"Error reading report {filename}: {e}")
    
    # Сортировка по дате (новые сверху)
    reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return reports

def get_report_by_id(user_id: str, report_id: str) -> Optional[Dict]:
    """Получает конкретный отчет пользователя по ID"""
    report_file = os.path.join(REPORTS_DIR, user_id, f"{report_id}.json")
    
    if not os.path.exists(report_file):
        return None
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading report {report_id}: {e}")
        return None

def delete_report_file(user_id: str, report_id: str) -> bool:
    """Удаляет файл отчета"""
    report_file = os.path.join(REPORTS_DIR, user_id, f"{report_id}.json")
    
    if os.path.exists(report_file):
        try:
            os.remove(report_file)
            logger.info(f"Report deleted: {report_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {e}")
            return False
    return False

def get_user_registration_date(user_id: str) -> Optional[str]:
    """
    Получает дату регистрации пользователя из user-auth-db
    Через внутренний запрос к user_auth_service
    """
    try:
        # Синхронный вызов для простоты (или можно сделать асинхронным)
        import httpx as sync_httpx
        response = sync_httpx.get(
            f"{SERVICES.get('user_auth_service', 'http://user_auth_service:8007')}/api/v1/user/{user_id}",
            timeout=5.0
        )
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("created_at") or user_data.get("registration_date")
    except Exception as e:
        logger.error(f"Error fetching user registration date: {e}")
    
    return None


def build_internal_headers(request: Request) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    authorization = request.headers.get("authorization")
    if authorization:
        headers["authorization"] = authorization

    api_key = request.headers.get("x-api-key")
    if api_key:
        headers["x-api-key"] = api_key

    return headers


async def get_current_user(request: Request) -> Optional[Dict]:
    headers = build_internal_headers(request)
    if not headers.get("authorization"):
        return None

    identity_url = SERVICES.get("identity", "http://user_auth_service:8007")
    response = await client.get(f"{identity_url}/api/v1/auth/me", headers=headers)
    if response.status_code != 200:
        return None

    payload = response.json()
    return payload.get("data")


async def get_market_collection(request: Request, path: str) -> List[Dict]:
    headers = build_internal_headers(request)
    market_url = SERVICES.get("market", "http://market_service:8003")
    response = await client.get(f"{market_url}{path}", headers=headers)
    if response.status_code != 200:
        return []

    payload = response.json()
    return payload.get("data", [])


async def build_user_stats_response(request: Request) -> Dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = user.get("id")
    registration_date = user.get("created_at")
    last_active = user.get("last_login_at") or user.get("updated_at") or registration_date

    ideas = await get_market_collection(request, "/api/v1/ideas/me")
    reports = await get_market_collection(request, "/api/v1/reports/me")

    ideas = sorted(ideas, key=lambda item: item.get("created_at", ""), reverse=True)
    total_analyses = len(ideas)
    total_reports = len(reports)
    first_analysis = ideas[-1].get("created_at") if ideas else None
    last_analysis = ideas[0].get("created_at") if ideas else None
    analyses_by_month: Dict[str, int] = {}

    for idea in ideas:
        created_at = idea.get("created_at", "")
        if created_at:
            month = created_at[:7]
            analyses_by_month[month] = analyses_by_month.get(month, 0) + 1

    if last_analysis and (not last_active or str(last_analysis) > str(last_active)):
        last_active = last_analysis

    return {
        "success": True,
        "user_id": user_id,
        "stats": {
            "total_analyses": total_analyses,
            "total_reports": total_reports,
            "registration_date": registration_date,
            "last_active": last_active,
            "first_analysis": first_analysis,
            "last_analysis": last_analysis,
            "analyses_by_month": analyses_by_month,
        },
    }


# ========== MIDDLEWARE ==========

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.2f}s)")
    return response


# ========== ОСНОВНОЙ ПРОКСИ РОУТ ==========

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(service: str, path: str, request: Request):
    check_api_key(request)

    if service == "user" and path == "stats":
        return await build_user_stats_response(request)
    
    if service not in SERVICES:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found. Available: {list(SERVICES.keys())}"
        )
    
    target_url = f"{SERVICES[service]}/{path}"
    body = await request.body()
    
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("x-api-key", None)
    headers.pop("content-length", None)
    headers.pop("transfer-encoding", None)
    
    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        
        # Перехват ответа от оркестратора для сохранения
        if service == "orchestrator" and path == "api/v1/result" and request.method == "GET":
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get("status") == "completed":
                    user_id = get_user_id_from_request(request)
                    if user_id:
                        report_id = save_report_to_file(user_id, result_data)
                        result_data["report_id"] = report_id
                        return JSONResponse(content=result_data)
        
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


# Report history routes

@app.post("/api/reports/save")
async def save_report(request: Request):
    """Сохранить отчет в историю пользователя"""
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    body = await request.json()
    
    if not user_id:
        user_id = body.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header or user_id in body)")
    
    report_data = body.get("report_data")
    if not report_data:
        raise HTTPException(status_code=400, detail="report_data is required")
    
    report_id = save_report_to_file(user_id, report_data)
    
    return {
        "success": True,
        "report_id": report_id,
        "user_id": user_id,
        "message": "Report saved successfully"
    }


@app.get("/api/reports")
async def get_reports_list(request: Request):
    """Получить список всех отчетов пользователя"""
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    reports = get_user_reports(user_id)
    
    return {
        "success": True,
        "user_id": user_id,
        "total": len(reports),
        "reports": reports
    }


@app.get("/api/reports/{report_id}")
async def get_report(request: Request, report_id: str):
    """Получить конкретный отчет по ID"""
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    report = get_report_by_id(user_id, report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "success": True,
        "report": report
    }


@app.delete("/api/reports/{report_id}")
async def delete_report(request: Request, report_id: str):
    """Удалить отчет по ID"""
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    deleted = delete_report_file(user_id, report_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "success": True,
        "message": "Report deleted successfully"
    }

# User stats
@app.get("/api/user/stats")
async def get_user_stats(request: Request):
    """
    Получить расширенную статистику пользователя
    
    Возвращает:
    - total_analyses: количество анализов (отчетов)
    - total_reports: количество отчетов (синоним)
    - registration_date: дата регистрации
    - last_active: дата последней активности
    - first_analysis: дата первого анализа
    - last_analysis: дата последнего анализа
    - analyses_by_month: количество анализов по месяцам
    """
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    # Получаем все отчеты пользователя
    reports = get_user_reports(user_id)
    
    # Получаем дату регистрации из user-auth-db
    registration_date = get_user_registration_date(user_id)
    
    # Базовая статистика
    total_analyses = len(reports)
    total_reports = total_analyses  # отчет = анализ
    
    # Даты первого и последнего анализа
    first_analysis = None
    last_analysis = None
    analyses_by_month = {}
    
    if reports:
        # Последний отчет (первый в списке, т.к. сортировка по убыванию)
        last_analysis = reports[0].get("created_at")
        # Первый отчет (последний в списке)
        first_analysis = reports[-1].get("created_at")
        
        # Группировка по месяцам
        for report in reports:
            created_at = report.get("created_at", "")
            if created_at:
                month = created_at[:7]  # YYYY-MM
                analyses_by_month[month] = analyses_by_month.get(month, 0) + 1
    
    # Получаем дату последней активности (из user-auth-db или последний отчет)
    last_active = None
    try:
        import httpx as sync_httpx
        response = sync_httpx.get(
            f"{SERVICES.get('user_auth_service', 'http://user_auth_service:8007')}/api/v1/user/{user_id}/activity",
            timeout=5.0
        )
        if response.status_code == 200:
            activity_data = response.json()
            last_active = activity_data.get("last_login") or activity_data.get("last_active")
    except Exception as e:
        logger.error(f"Error fetching user activity: {e}")
    
    # Если не удалось получить из user-auth-db, используем дату последнего отчета
    if not last_active and last_analysis:
        last_active = last_analysis
    
    return {
        "success": True,
        "user_id": user_id,
        "stats": {
            "total_analyses": total_analyses,
            "total_reports": total_reports,
            "registration_date": registration_date,
            "last_active": last_active,
            "first_analysis": first_analysis,
            "last_analysis": last_analysis,
            "analyses_by_month": analyses_by_month
        }
    }


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
        "examples": [f"/api/{s}/some-endpoint" for s in SERVICES.keys()],
        "report_endpoints": [
            "POST /api/reports/save - сохранить отчет",
            "GET /api/reports - список отчетов",
            "GET /api/reports/{report_id} - получить отчет",
            "DELETE /api/reports/{report_id} - удалить отчет",
            "GET /api/user/stats - статистика пользователя"
        ]
    }


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()
