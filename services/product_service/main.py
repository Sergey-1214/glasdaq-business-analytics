"""
Product Service - SWOT, Audience, Value Proposition
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import http
import os
import logging
from typing import Dict, Any

from shared.utils import setup_logging, get_settings
from shared.models import AnalysisRequest

# Setup
settings = get_settings()
logger = setup_logging("product_service")

app = FastAPI(
    title="Product Analysis Service",
    description="SWOT, audience, and value proposition analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama URL
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))


@app.get("/")
async def root():
    return {
        "service": "Product Service",
        "version": "1.0.0",
        "models": ["phi", "qwen2.5:7b"]
    }


@app.get("/health")
async def health():
    """Health check with Ollama"""
    try:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        if resp.status_code == 200:
            return {"status": "healthy", "ollama": "connected"}
    except:
        pass
    return {"status": "degraded", "ollama": "disconnected"}


@app.post("/api/v1/analyze")
async def analyze_product(request: AnalysisRequest):
    """
    Full product analysis
    
    Returns SWOT, audience, and value proposition
    """
    try:
        # Run parallel analyses
        swot = await analyze_swot(request.idea)
        audience = await analyze_audience(request.idea, request.region)
        value = await analyze_value_proposition(request.idea)
        
        return {
            "success": True,
            "data": {
                "swot": parse_swot(swot),
                "audience": audience,
                "value_proposition": value
            }
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze/swot")
async def swot_only(idea: str):
    """SWOT analysis only"""
    result = await analyze_swot(idea)
    return {"success": True, "data": parse_swot(result)}


@app.post("/api/v1/analyze/audience")
async def audience_only(request: AnalysisRequest):
    """Audience analysis only"""
    result = await analyze_audience(request.idea, request.region)
    return {"success": True, "data": result}


@app.post("/api/v1/analyze/value")
async def value_only(idea: str):
    """Value proposition only"""
    result = await analyze_value_proposition(idea)
    return {"success": True, "data": result}


async def analyze_swot(idea: str) -> str:
    """Run SWOT analysis using phi model"""
    prompt = f"""
    SWOT analysis for startup idea: {idea}
    
    Format exactly:
    STRENGTHS:
    - point 1
    - point 2
    
    WEAKNESSES:
    - point 1
    - point 2
    
    OPPORTUNITIES:
    - point 1
    - point 2
    
    THREATS:
    - point 1
    - point 2
    """
    
    resp = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "phi",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
    )
    
    data = resp.json()
    return data.get("message", {}).get("content", "")


async def analyze_audience(idea: str, region: str) -> str:
    """Run audience analysis using phi model"""
    prompt = f"""
    Describe target audience for: {idea}
    Region: {region}
    
    Include:
    - Demographics (age, gender, income, education)
    - Psychographics (interests, values, lifestyle)
    - Behaviors (purchasing habits, media preferences)
    - Pain points and problems
    """
    
    resp = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "phi",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
    )
    
    data = resp.json()
    return data.get("message", {}).get("content", "")


async def analyze_value_proposition(idea: str) -> str:
    """Run value proposition analysis using qwen2.5:7b model"""
    prompt = f"""
    Create value proposition for: {idea}
    
    Include:
    1. Unique Value Proposition (one sentence)
    2. Key Benefits (3-5 points)
    3. Differentiation from competitors (2-3 points)
    """
    
    resp = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "qwen2.5:7b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
    )
    
    data = resp.json()
    return data.get("message", {}).get("content", "")


def parse_swot(text: str) -> Dict[str, Any]:
    """Parse SWOT text into structured format"""
    result = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }
    
    current = None
    
    for line in text.split('\n'):
        line_lower = line.lower().strip()
        
        if 'strength' in line_lower:
            current = "strengths"
        elif 'weakness' in line_lower:
            current = "weaknesses"
        elif 'opportunity' in line_lower:
            current = "opportunities"
        elif 'threat' in line_lower:
            current = "threats"
        elif line.strip().startswith('-') and current:
            item = line.strip().lstrip('-').strip()
            if item:
                result[current].append(item)
    
    return result