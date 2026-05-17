"""
Simple Orchestrator for all services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import uuid
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

app = FastAPI(
    title="Orchestrator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== URL СЕРВИСОВ (из переменных окружения) ==========
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product_service:8002")
MARKET_SERVICE_URL = os.getenv("MARKET_SERVICE_URL", "http://market_service:8005")
FINANCE_SERVICE_URL = os.getenv("FINANCE_SERVICE_URL", "http://finance_service:8004")
TEAM_SERVICE_URL = os.getenv("TEAM_SERVICE_URL", "http://team_service:8003")
IMPLEMENTATION_URL = os.getenv("PRODUCT_IMPLEMENTATION_URL", "http://product_implementation:8008")
USER_AUTH_SERVICE_URL = os.getenv("USER_AUTH_SERVICE_URL", "http://user_auth_service:8007")

# Хранилище задач
tasks: Dict[str, Dict] = {}


# ========== ЭНДПОИНТЫ ==========

@app.get("/")
async def root():
    """Информация об оркестраторе"""
    return {
        "service": "Orchestrator",
        "version": "1.0.0",
        "port": 8003,
        "services": {
            "product": PRODUCT_SERVICE_URL,
            "market": MARKET_SERVICE_URL,
            "finance": FINANCE_SERVICE_URL,
            "team": TEAM_SERVICE_URL,
            "implementation": IMPLEMENTATION_URL,
            "user_auth": USER_AUTH_SERVICE_URL
        },
        "endpoints": [
            "POST /api/v1/analyze - запуск анализа",
            "GET /api/v1/status/{task_id} - статус задачи",
            "GET /api/v1/result/{task_id} - результат анализа",
            "GET /health - проверка здоровья",
            "GET /docs - Swagger документация"
        ]
    }


@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {"status": "healthy", "service": "orchestrator", "port": 8003}


@app.post("/api/v1/analyze")
async def start_analysis(request: Dict[str, Any]):
    """
    Запуск полного анализа
    
    Входные данные:
    {
        "idea": "Описание идеи",
        "region": "russia",
        "industry": "foodtech",
        "price": 500,
        "customers_year1": 1000,
        "cac": 3000,
        "user_id": "optional_user_id"
    }
    """
    task_id = str(uuid.uuid4())
    
    # Сохраняем задачу
    tasks[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "current_step": "Запуск анализа",
        "started_at": datetime.now(),
        "request": request,
        "results": {}
    }
    
    # Запускаем в фоне
    asyncio.create_task(run_full_analysis(task_id, request))
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Анализ запущен",
        "status_url": f"/api/v1/status/{task_id}"
    }


@app.get("/api/v1/status/{task_id}")
async def get_status(task_id: str):
    """Получение статуса задачи"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"],
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "error": task.get("error")
    }


@app.get("/api/v1/result/{task_id}")
async def get_result(task_id: str):
    """Получение результата анализа"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    
    return {
        "task_id": task_id,
        "status": "completed",
        "results": task.get("results")
    }


# ========== ОСНОВНАЯ ЛОГИКА ==========

async def run_full_analysis(task_id: str, request: Dict[str, Any]):
    """
    Запуск всех сервисов с правильным порядком
    """
    task = tasks[task_id]
    try:
        results = {}
        
        # Шаг 1: Параллельный вызов независимых сервисов (Уровень 1)
        task["current_step"] = "Анализ продукта, рынка и команды"
        task["progress"] = 10
        
        product_task = call_product_service(request)
        market_task = call_market_service(request)
        team_task = call_team_service(request)
        
        product_result, market_result, team_result = await asyncio.gather(
            product_task, market_task, team_task
        )
        
        results["product"] = product_result
        results["market"] = market_result
        results["team"] = team_result
        
        task["progress"] = 40
        task["current_step"] = "Финансовый анализ"
        
        # Шаг 2: Финансовый анализ (зависит от market данных)
        finance_request = {
            "idea": request.get("idea", ""),
            "price": request.get("price", 500),
            "customers_year1": request.get("customers_year1", 1000),
            "cac": request.get("cac", 3000),
            "marketing_budget": request.get("marketing_budget"),
            "margin": request.get("margin", 60),
            "market_data": market_result.get("data", {})
        }
        finance_result = await call_finance_service(finance_request)
        results["finance"] = finance_result
        
        task["progress"] = 65
        task["current_step"] = "Анализ реализации продукта"
        
        # Шаг 3: Implementation (зависит от product и finance)
        impl_request = {
            "idea": request.get("idea", ""),
            "features": request.get("features", []),
            "timeline": request.get("timeline", 3),
            "product_data": product_result.get("data", {}),
            "finance_data": finance_result.get("data", {})
        }
        impl_result = await call_implementation_service(impl_request)
        results["implementation"] = impl_result
        
        task["progress"] = 85
        task["current_step"] = "Формирование единого отчета"
        
        # Шаг 4: Формирование единого отчета
        report = generate_unified_report(results)
        results["report"] = report
        
        # Добавляем информацию о пользователе, если есть
        if request.get("user_id"):
            results["user_id"] = request.get("user_id")
        
        # Завершение
        task["status"] = "completed"
        task["progress"] = 100
        task["current_step"] = "Анализ завершен"
        task["completed_at"] = datetime.now()
        task["results"] = results
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        task["status"] = "failed"
        task["error"] = str(e)
        task["completed_at"] = datetime.now()


async def call_product_service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Вызов Product Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "idea": request.get("idea", ""),
                "region": request.get("region", "russia"),
                "industry": request.get("industry", "other")
            }
            
            response = await client.post(
                f"{PRODUCT_SERVICE_URL}/api/v1/analyze",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            logger.error("Product service timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Product service error: {e}")
            return {"success": False, "error": str(e)}


async def call_market_service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Вызов Market Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "idea": request.get("idea", ""),
                "region": request.get("region", "russia")
            }
            
            response = await client.post(
                f"{MARKET_SERVICE_URL}/api/v1/analyze",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            logger.error("Market service timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Market service error: {e}")
            return {"success": False, "error": str(e)}


async def call_team_service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Вызов Team Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "idea": request.get("idea", ""),
                "industry": request.get("industry", "other"),
                "complexity": request.get("complexity", 5)
            }
            
            response = await client.post(
                f"{TEAM_SERVICE_URL}/api/v1/analyze",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            logger.error("Team service timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Team service error: {e}")
            return {"success": False, "error": str(e)}


async def call_finance_service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Вызов Finance Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{FINANCE_SERVICE_URL}/api/v1/analyze",
                json=request
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            logger.error("Finance service timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Finance service error: {e}")
            return {"success": False, "error": str(e)}


async def call_implementation_service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Вызов Implementation Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{IMPLEMENTATION_URL}/api/v1/analyze",
                json=request
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            logger.error("Implementation service timeout")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Implementation service error: {e}")
            return {"success": False, "error": str(e)}


def generate_unified_report(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Формирование единого отчета из результатов всех сервисов
    """
    product_data = results.get("product", {}).get("data", {})
    market_data = results.get("market", {}).get("data", {})
    finance_data = results.get("finance", {}).get("data", {})
    team_data = results.get("team", {}).get("data", {})
    impl_data = results.get("implementation", {}).get("data", {})
    
    report = {
        "summary": {
            "verdict": calculate_verdict(finance_data, market_data),
            "key_metrics": {
                "ltv_cac_ratio": finance_data.get("unit_economics", {}).get("ltv_cac_ratio"),
                "breakeven_month": finance_data.get("financial_model", {}).get("breakeven_month"),
                "market_trend": market_data.get("trend", "unknown"),
                "market_size_som": market_data.get("market_size", {}).get("som"),
                "team_score": team_data.get("team_score", "N/A")
            }
        },
        "product": {
            "swot": product_data.get("swot", {}),
            "value_proposition": product_data.get("value_proposition", ""),
            "audience": product_data.get("audience", "")
        },
        "market": {
            "tam": market_data.get("market_size", {}).get("tam"),
            "sam": market_data.get("market_size", {}).get("sam"),
            "som": market_data.get("market_size", {}).get("som"),
            "competitors": market_data.get("competitive_landscape", {}).get("competitors", []),
            "trend": market_data.get("trends", {}).get("verdict", "unknown")
        },
        "team": {
            "required_roles": team_data.get("required_roles", []),
            "founder_recommendations": team_data.get("founder_recommendations", ""),
            "hiring_priority": team_data.get("hiring_priority", [])
        },
        "finance": {
            "revenue_12m": finance_data.get("financial_model", {}).get("revenue_12m"),
            "profit_12m": finance_data.get("financial_model", {}).get("profit_12m"),
            "breakeven_month": finance_data.get("financial_model", {}).get("breakeven_month"),
            "ltv_cac_ratio": finance_data.get("unit_economics", {}).get("ltv_cac_ratio"),
            "recommendation": finance_data.get("unit_economics", {}).get("recommendation"),
            "valuation": finance_data.get("valuation", {}).get("pre_money")
        },
        "implementation": {
            "tech_stack": impl_data.get("tech_stack", ""),
            "mvp_plan": impl_data.get("mvp_plan", ""),
            "roadmap": impl_data.get("roadmap", [])
        },
        "recommendations": generate_recommendations(finance_data, market_data, product_data, team_data)
    }
    
    return report


def calculate_verdict(finance_data: Dict, market_data: Dict) -> str:
    """Расчет общего вердикта"""
    ltv_cac = finance_data.get("unit_economics", {}).get("ltv_cac_ratio", 0)
    market_verdict = market_data.get("trends", {}).get("verdict", "unknown")
    
    if ltv_cac >= 3 and market_verdict == "favorable":
        return "positive"
    elif ltv_cac >= 1.5:
        return "neutral"
    else:
        return "negative"


def generate_recommendations(finance_data: Dict, market_data: Dict, product_data: Dict, team_data: Dict) -> list:
    """Генерация рекомендаций"""
    recommendations = []
    
    ltv_cac = finance_data.get("unit_economics", {}).get("ltv_cac_ratio", 0)
    
    if ltv_cac < 2:
        recommendations.append("📈 Улучшите LTV/CAC ratio: увеличьте цену или снизьте стоимость привлечения клиентов")
    
    if market_data.get("trends", {}).get("verdict") != "favorable":
        recommendations.append("🔍 Проведите дополнительное исследование рынка перед запуском")
    
    if not product_data.get("value_proposition"):
        recommendations.append("💡 Доработайте ценностное предложение - это ключевой фактор успеха")
    
    if not team_data.get("required_roles"):
        recommendations.append("👥 Сформируйте команду: определите ключевые роли для запуска")
    
    if len(recommendations) == 0:
        recommendations.append("✅ Отличные показатели! Можно масштабировать бизнес")
    
    return recommendations