from __future__ import annotations

import logging
import os
import re
import time
from collections import OrderedDict

from pydantic import ValidationError

from src.clients import OllamaClient
from src.exceptions import ExternalServiceError
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
        try:
            raw_result = await self.client.chat_json(prompt)
        except ExternalServiceError as exc:
            logger.warning("Idea parser fallback activated due to external parser error: %s", exc)
            fallback = self._build_fallback_parse(payload, source="fallback_external")
            fallback.processing_time_ms = self._elapsed_ms(started_at)
            return IdeaParseResponse(data=fallback)

        try:
            parsed = IdeaParseResponseData.model_validate(raw_result)
            parsed.parser_source = "llm"
        except ValidationError as exc:
            logger.error("ValidationError on model output: %s\nRaw result: %s", exc, raw_result)
            parsed = self._build_fallback_parse(payload, source="fallback_validation")

        parsed.processing_time_ms = self._elapsed_ms(started_at)
        if parsed.confidence >= 0.4 and parsed.parser_source not in {"fallback_external", "fallback_validation"}:
            self._cache_put(cache_key, parsed)
        return IdeaParseResponse(data=parsed)

    def _build_prompt(self, payload: IdeaParseRequest) -> str:
        region_line = payload.region or ""
        return f"""
Analyse the startup idea and return ONLY a flat JSON object. Do NOT nest objects inside any field.

Required keys (all at top level):
- language: string (ru / en / other)
- normalized_idea: string, one short sentence in Russian describing the business
- business_category: string in Russian (e.g. "Кофейня", "Доставка еды", "IT-сервис")
- subcategory: string in Russian or null
- business_model: string in Russian or null
- offering_type: string in Russian or null
- query_type: string (e.g. "new_business", "location_search", "market_check") or null
- price_segment: "high" | "mid" | "low" | null
- target_audience: array of Russian strings (or [])
- region: string or null
- district: string (district/area/metro reference in Russian) or null
- location_preferences: array of Russian strings describing preferred location (or [])
- planned_average_check: number (average receipt in rubles) or null
- max_rent_m2: number (max rent per m2 in rubles) or null
- min_pedestrian_traffic: integer (min daily foot traffic) or null
- min_metro_passenger_flow: integer (min daily metro passengers) or null
- preferred_distance_to_metro_m: integer (max distance to metro in meters) or null
- constraints: array of Russian strings with explicit restrictions from user (or [])
- customer_problem: string in Russian or null
- keywords: array of Russian strings (max 8, or [])
- confidence: float 0..1, how confident you are this is a real business idea

Rules:
- ALL string values must be in Russian (except language, query_type and price_segment).
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

    def _build_fallback_parse(self, payload: IdeaParseRequest, source: str) -> IdeaParseResponseData:
        idea_text = payload.idea.strip()
        normalized_text = idea_text.lower()
        category = self._infer_category(normalized_text)
        average_check = self._extract_average_check(idea_text)

        location_preferences = []
        if any(token in normalized_text for token in ("метро", "у метро", "рядом с метро", "near metro")):
            location_preferences.append("рядом с метро")
        if any(token in normalized_text for token in ("навынос", "takeaway", "to go", "с собой")):
            location_preferences.append("формат навынос")

        target_audience = []
        if any(token in normalized_text for token in ("офис", "офисные")):
            target_audience.append("офисные сотрудники")
        if any(token in normalized_text for token in ("студент", "молодеж")):
            target_audience.append("студенты и молодая аудитория")

        confidence = 0.72 if category != "other" else 0.35
        if category in {"Кофейня", "Столовая", "Ресторан", "Доставка еды"} and any(
            token in normalized_text
            for token in ("район", "локац", "точк", "открыть", "студент", "метро", "рядом")
        ):
            confidence = max(confidence, 0.78)

        return IdeaParseResponseData(
            language="ru",
            normalized_idea=idea_text[:160],
            business_category=category,
            subcategory="specialty-кофейня" if "specialty" in normalized_text and category == "Кофейня" else None,
            business_model="офлайн-точка",
            offering_type="офлайн-локация",
            query_type="new_business",
            price_segment=self._infer_price_segment(average_check),
            target_audience=target_audience,
            region=payload.region,
            district=None,
            location_preferences=location_preferences,
            planned_average_check=average_check,
            constraints=[],
            customer_problem=None,
            keywords=self._extract_keywords(normalized_text),
            confidence=confidence,
            parser_source=source,
        )

    def _infer_category(self, normalized_text: str) -> str:
        category_aliases = (
            ("Кофейня", ("кофейня", "кофе", "specialty", "cafe", "coffee")),
            ("Столовая", ("столовая", "canteen", "cafeteria", "food court", "буфет")),
            ("Доставка еды", ("доставка еды", "доставка", "delivery", "dark kitchen")),
            ("Ресторан", ("ресторан", "restaurant", "бистро")),
            ("Фитнес", ("фитнес", "спортзал", "gym", "fitness")),
            ("Аптека", ("аптека", "pharmacy")),
            ("IT-сервис", ("it-сервис", "it сервис", "saas", "приложение", "platform")),
        )
        for label, aliases in category_aliases:
            if any(alias in normalized_text for alias in aliases):
                return label
        return "other"

    def _extract_average_check(self, idea_text: str) -> float | None:
        match = re.search(r"(?:чек(?:ом)?|средним чеком)[^\d]{0,12}(\d{2,6})", idea_text.lower())
        if match:
            return float(match.group(1))
        return None

    def _infer_price_segment(self, average_check: float | None) -> str | None:
        if average_check is None:
            return None
        if average_check >= 700:
            return "high"
        if average_check >= 350:
            return "mid"
        return "low"

    def _extract_keywords(self, normalized_text: str) -> list[str]:
        candidates = [
            ("метро", "метро"),
            ("навынос", "навынос"),
            ("specialty", "specialty"),
            ("кофе", "кофе"),
            ("кофейня", "кофейня"),
            ("столов", "столовая"),
            ("студент", "студенты"),
            ("район", "район"),
            ("офис", "офисы"),
        ]
        return [label for token, label in candidates if token in normalized_text][:8]
