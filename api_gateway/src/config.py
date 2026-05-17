import os

SERVICES = {
    "orchestrator": os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8003"),
    "product": os.getenv("PRODUCT_SERVICE_URL", "http://product_service:8004"),
    "team": os.getenv("TEAM_SERVICE_URL", "http://team_service:8005"),
    "finance": os.getenv("FINANCE_SERVICE_URL", "http://finance_service:8006"),
    "market": os.getenv("MARKET_SERVICE_URL", "http://market_service:8001"),
    "implementation": os.getenv("PRODUCT_IMPLEMENTATION_URL", "http://product_implementation:8008"),
    "parsers": os.getenv("PARSERS_URL", "http://parsers:8002"),
    "identity": os.getenv("USER_AUTH_SERVICE_URL", "http://user_auth_service:8007"),
}

PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
API_KEY = os.getenv("API_GATEWAY_KEY", "change-me")
