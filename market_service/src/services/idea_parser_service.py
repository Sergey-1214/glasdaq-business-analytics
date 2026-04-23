from __future__ import annotations

import time

from pydantic import ValidationError

from src.clients import OllamaClient
from src.exceptions import IdeaParsingError
from src.schemas import IdeaParseRequest, IdeaParseResponse, IdeaParseResponseData


class IdeaParserService:
    def __init__(self) -> None:
        self.client = OllamaClient()

    async def parse_idea(self, payload: IdeaParseRequest) -> IdeaParseResponse:
        started_at = time.perf_counter()
        prompt = self._build_prompt(payload)
        raw_result = await self.client.chat_json(prompt)

        try:
            parsed = IdeaParseResponseData.model_validate(raw_result)
        except ValidationError as exc:
            raise IdeaParsingError(f"Model returned invalid structured output: {exc}") from exc

        parsed.parser_source = "llm"
        parsed.processing_time_ms = self._elapsed_ms(started_at)
        return IdeaParseResponse(data=parsed)

    def _build_prompt(self, payload: IdeaParseRequest) -> str:
        region_line = payload.region or ""
        return f"""
Extract startup idea parameters from Russian or English text.
Return only valid JSON with keys:
language, normalized_idea, business_category, subcategory, business_model,
offering_type, target_audience, region, location_preferences,
customer_problem, keywords, confidence.
Use null or [] if unknown. Confidence is 0..1. Do not invent details.

Idea: {payload.idea}
Region: {region_line}
""".strip()



    def _elapsed_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)
