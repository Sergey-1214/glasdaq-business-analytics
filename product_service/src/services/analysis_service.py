from __future__ import annotations

from src.clients.ollama_client import OllamaClient
from src.exceptions import AnalysisFormatError
from src.schemas import AnalysisRequest, AnalysisResponse, AnalysisResponseData


class AnalysisService:
    def __init__(self) -> None:
        self.client = OllamaClient()

    async def analyze(self, payload: AnalysisRequest) -> AnalysisResponse:
        prompt = self._build_prompt(payload)
        data = await self.client.chat_json(prompt)
        try:
            parsed = AnalysisResponseData.model_validate(data)
        except Exception as exc:
            raise AnalysisFormatError(f"Unexpected analysis format: {exc}") from exc
        return AnalysisResponse(data=parsed)

    def _build_prompt(self, payload: AnalysisRequest) -> str:
        region = payload.region or "not specified"
        industry = payload.industry or "not specified"
        return f"""
You are a product analyst. Analyze the startup idea and return JSON only.

Idea: {payload.idea}
Region: {region}
Industry: {industry}

Return JSON exactly by this schema:
{{
  "swot": {{
    "strengths": ["..."],
    "weaknesses": ["..."],
    "opportunities": ["..."],
    "threats": ["..."]
  }},
  "audience": "multiline text with audience segmentation",
  "value_proposition": "multiline text with UVP, key benefits, and differentiation"
}}

Rules:
1) Each SWOT list must contain at least 3 points.
2) Response language must be Russian.
3) No markdown, no explanations, valid JSON only.
""".strip()
