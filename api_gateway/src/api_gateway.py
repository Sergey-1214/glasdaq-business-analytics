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
REPORTS_DIR = os.getenv("REPORTS_DIR", "/app/reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

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
        
        # ========== ПЕРЕХВАТ ОТВЕТА ОТ ОРКЕСТРАТОРА ДЛЯ СОХРАНЕНИЯ ==========
        # Если это ответ от оркестратора с завершенным анализом
        if service == "orchestrator" and path == "api/v1/result" and request.method == "GET":
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get("status") == "completed":
                    user_id = get_user_id_from_request(request)
                    if user_id:
                        # Сохраняем отчет автоматически
                        report_id = save_report_to_file(user_id, result_data)
                        # Добавляем report_id в ответ
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


# ========== НОВЫЕ РОУТЫ ДЛЯ ИСТОРИИ ОТЧЕТОВ ==========

@app.post("/api/reports/save")
async def save_report(request: Request):
    """
    Сохранить отчет в историю пользователя
    
    Body:
    {
        "report_data": {...},
        "user_id": "optional_if_in_header"
    }
    """
    check_api_key(request)
    
    # Получаем user_id
    user_id = get_user_id_from_request(request)
    body = await request.json()
    
    # Если user_id не в заголовке, пробуем из тела запроса
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
    """
    Получить список всех отчетов пользователя
    """
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
    """
    Получить конкретный отчет по ID
    """
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
    """
    Удалить отчет по ID
    """
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


@app.get("/api/reports/stats")
async def get_reports_stats(request: Request):
    """
    Получить статистику по отчетам пользователя
    """
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    reports = get_user_reports(user_id)
    
    # Статистика
    total = len(reports)
    
    # Подсчет отчетов по месяцам
    monthly_stats = {}
    for report in reports:
        created_at = report.get("created_at", "")
        if created_at:
            month = created_at[:7]  # YYYY-MM
            monthly_stats[month] = monthly_stats.get(month, 0) + 1
    
    return {
        "success": True,
        "user_id": user_id,
        "total_reports": total,
        "monthly_stats": monthly_stats,
        "first_report": reports[-1] if reports else None,
        "last_report": reports[0] if reports else None
    }


# ========== ЭКСПОРТ ОТЧЕТОВ ==========

@app.get("/api/reports/{report_id}/export/pdf")
async def export_report_pdf(request: Request, report_id: str):
    """
    Экспорт отчета в PDF через Report Service
    """
    check_api_key(request)
    
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required (x-user-id header)")
    
    report = get_report_by_id(user_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Перенаправляем в Report Service для генерации PDF
    if "report_service" not in SERVICES:
        raise HTTPException(status_code=503, detail="Report service unavailable")
    
    target_url = f"{SERVICES['report_service']}/api/v1/report/generate"
    
    try:
        response = await client.post(
            target_url,
            json={
                "task_id": report_id,
                "results": report.get("data", {}),
                "user_id": user_id,
                "format": "pdf"
            },
            timeout=60.0
        )
        
        if response.status_code == 200:
            pdf_data = response.json()
            return Response(
                content=pdf_data.get("content", b""),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{report_id}.pdf"
                }
            )
        else:
            raise HTTPException(status_code=response.status_code, detail="PDF generation failed")
            
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== СУЩЕСТВУЮЩИЕ РОУТЫ ==========

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
            "GET /api/reports/stats - статистика",
            "GET /api/reports/{report_id}/export/pdf - экспорт в PDF"
        ]
    }


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()