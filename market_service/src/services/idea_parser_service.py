from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict

from pydantic import ValidationError

from src.clients import OllamaClient
from src.exceptions import IdeaParsingError
from src.schemas import IdeaParseRequest, IdeaParseResponse, IdeaParseResponseData

logger = logging.getLogger(__name__)

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
            logger.error("ValidationError on model output: %s\nRaw result: %s", exc, raw_result)
            parsed = IdeaParseResponseData(confidence=0.0)

        parsed.parser_source = "llm"
        parsed.processing_time_ms = self._elapsed_ms(started_at)
        self._cache_put(cache_key, parsed)
        return IdeaParseResponse(data=parsed)

    def _build_prompt(self, payload: IdeaParseRequest) -> str:
        region_line = payload.region or ""
        return f"""
Analyse the startup idea and return ONLY a flat JSON object. Do NOT nest objects inside any field.

Required keys (all at top level):
- language: string (ru / en / other)
- normalized_idea: string — one short sentence in Russian describing the business
- business_category: string in Russian (e.g. "Кофейня", "Доставка еды", "IT-сервис")
- subcategory: string in Russian or null
- business_model: string in Russian or null
- offering_type: string in Russian or null
- price_segment: "high" | "mid" | "low" | null
- target_audience: array of Russian strings (or [])
- region: string or null
- location_preferences: array of Russian strings describing preferred location (or []) — e.g. ["рядом с метро", "центр города"]
- planned_average_check: number (average receipt in rubles) or null
- max_rent_m2: number (max rent per m2 in rubles) or null
- min_pedestrian_traffic: integer (min daily foot traffic) or null
- min_metro_passenger_flow: integer (min daily metro passengers) or null
- preferred_distance_to_metro_m: integer (max distance to metro in meters) or null
- customer_problem: string in Russian or null
- keywords: array of Russian strings (max 8, or [])
- confidence: float 0..1 — how confident you are this is a real business idea

Rules:
- ALL string values must be in Russian (except language and price_segment).
- Use null for unknown numeric fields. Only fill numeric fields if explicitly stated in the idea.
- location_preferences is a FLAT LIST of strings, NOT an object.

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
