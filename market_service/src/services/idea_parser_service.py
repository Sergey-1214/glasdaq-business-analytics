from __future__ import annotations

import os
import time
from collections import OrderedDict

from pydantic import ValidationError

from src.clients import OllamaClient
from src.exceptions import IdeaParsingError
from src.schemas import IdeaParseRequest, IdeaParseResponse, IdeaParseResponseData

_CACHE_TTL_SECONDS = int(os.getenv("IDEA_PARSER_CACHE_TTL_SECONDS", "900"))
_CACHE_MAX_SIZE = int(os.getenv("IDEA_PARSER_CACHE_MAX_SIZE", "512"))


class IdeaParserService:
    _cache: OrderedDict[str, tuple[float, IdeaParseResponseData]] = OrderedDict()
    _client: OllamaClient | None = None

    def __init__(self) -> None:
        if self.__class__._client is None:
            self.__class__._client = OllamaClient()
        self.client = self.__class__._client

    async def parse_idea(self, payload: IdeaParseRequest) -> IdeaParseResponse:
        started_at = time.perf_counter()
        cache_key = self._cache_key(payload)
        cached = self._cache_get(cache_key)
        if cached is not None:
            cached.parser_source = "cache"
            cached.processing_time_ms = self._elapsed_ms(started_at)
            return IdeaParseResponse(data=cached)

        prompt = self._build_prompt(payload)
        raw_result = await self.client.chat_json(prompt)

        try:
            parsed = IdeaParseResponseData.model_validate(raw_result)
        except ValidationError as exc:
            raise IdeaParsingError(f"Model returned invalid structured output: {exc}") from exc

        parsed.parser_source = "llm"
        parsed.processing_time_ms = self._elapsed_ms(started_at)
        self._cache_put(cache_key, parsed)
        return IdeaParseResponse(data=parsed)

    def _build_prompt(self, payload: IdeaParseRequest) -> str:
        region_line = payload.region or ""
        return f"""
Extract startup idea parameters from Russian or English text.
Return only valid JSON with keys:
language, normalized_idea, business_category, subcategory, business_model,
offering_type, price_segment, target_audience, region, location_preferences,
planned_average_check, max_rent_m2, min_pedestrian_traffic,
min_metro_passenger_flow, preferred_distance_to_metro_m,
customer_problem, keywords, confidence.
Rules:
- Use null or [] if unknown.
- Confidence is 0..1.
- Do not invent details.
- Parse numeric constraints only when explicitly present.
- price_segment: high | mid | low.

Idea: {payload.idea}
Region: {region_line}
""".strip()

    def _elapsed_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    def _cache_key(self, payload: IdeaParseRequest) -> str:
        region = (payload.region or "").strip().lower()
        idea = payload.idea.strip().lower()
        return f"{region}::{idea}"

    def _cache_get(self, key: str) -> IdeaParseResponseData | None:
        item = self.__class__._cache.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self.__class__._cache.pop(key, None)
            return None
        self.__class__._cache.move_to_end(key)
        return value.model_copy(deep=True)

    def _cache_put(self, key: str, value: IdeaParseResponseData) -> None:
        if _CACHE_MAX_SIZE <= 0 or _CACHE_TTL_SECONDS <= 0:
            return
        expires_at = time.time() + _CACHE_TTL_SECONDS
        self.__class__._cache[key] = (expires_at, value.model_copy(deep=True))
        self.__class__._cache.move_to_end(key)
        while len(self.__class__._cache) > _CACHE_MAX_SIZE:
            self.__class__._cache.popitem(last=False)
