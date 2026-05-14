from __future__ import annotations

import math
from statistics import median

from sqlalchemy.orm import Session

from src.exceptions import AppError
from src.repositories import AnalysisRepository
from src.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResponseData,
    CompetitorShare,
    IdeaParseRequest,
    IdeaParseResponseData,
)
from src.services.idea_parser_service import IdeaParserService


_CATEGORY_MAP: dict[str, str] = {
    "кофейня": "coffee_shop",
    "кофе": "coffee_shop",
    "кафе": "coffee_shop",
    "coffee shop": "coffee_shop",
    "coffee": "coffee_shop",
    "cafe": "coffee_shop",
    "specialty coffee": "coffee_shop",
    "coffee house": "coffee_shop",
    "доставка еды": "food_delivery",
    "доставка": "food_delivery",
    "доставка здоровой еды": "food_delivery",
    "доставка питания": "food_delivery",
    "food delivery": "food_delivery",
    "meal delivery": "food_delivery",
    "food services": "food_delivery",
    "delivery services": "food_delivery",
    "food & beverage": "food_delivery",
    "ресторан": "restaurant",
    "restaurant": "restaurant",
    "fine dining": "restaurant",
    "бистро": "restaurant",
    "фитнес": "fitness",
    "спортзал": "fitness",
    "gym": "fitness",
    "fitness": "fitness",
    "фитнес-клуб": "fitness",
    "аптека": "pharmacy",
    "pharmacy": "pharmacy",
    "it-сервис": "it_service",
    "it сервис": "it_service",
    "it service": "it_service",
    "приложение": "it_service",
    "saas": "it_service",
}

_METRO_ALIASES = {
    "near_metro",
    "рядом с метро",
    "около метро",
    "у метро",
    "возле метро",
    "near metro",
}

_CENTER_ALIASES = {
    "центр",
    "в центре",
    "центр москвы",
    "центр города",
    "downtown",
    "city center",
}

_OUTSKIRTS_ALIASES = {
    "окраина",
    "окраине",
    "спальный район",
    "периферия",
    "на западе",
    "запад",
    "западная",
    "западной",
    "west",
    "outskirts",
    "suburb",
    "suburban",
}

_TAKEAWAY_ALIASES = {
    "takeaway",
    "to go",
    "на вынос",
    "с собой",
}

_OFFICE_ALIASES = {
    "office workers",
    "офисные работники",
    "офисные сотрудники",
    "офисные",
    "для офисов",
    "business district",
}

_COMMUTER_ALIASES = {
    "commuters",
    "пассажиры метро",
    "пассажиры",
    "коммьютеры",
}

_PREMIUM_ALIASES = {
    "premium",
    "премиум",
    "высокий сегмент",
    "дорогой",
}

_BUDGET_ALIASES = {
    "budget",
    "low cost",
    "дешев",
    "эконом",
    "доступн",
}


def _normalize_category(raw: str) -> str:
    key = raw.strip().lower()
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    for pattern, mapped in _CATEGORY_MAP.items():
        if pattern in key or key in pattern:
            return mapped
    return "coffee_shop"


class AnalysisService:
    DEFAULT_REGION = "Moscow"
    DEFAULT_CATEGORY = "coffee_shop"
    MIN_DAILY_TRANSACTIONS = 40
    MAX_DAILY_TRANSACTIONS = 220
    DAYS_PER_YEAR = 365

    def __init__(self, db: Session) -> None:
        self.repository = AnalysisRepository(db)
        self.idea_parser = IdeaParserService()

    async def analyze(self, payload: AnalysisRequest) -> AnalysisResponse:
        parsed = await self._parse_idea(payload)
        region = parsed.region or payload.region or self.DEFAULT_REGION
        raw_category = parsed.business_category or self.DEFAULT_CATEGORY
        category = _normalize_category(raw_category)

        rows = self.repository.list_market_points_with_latest_metrics(region=region, category=category)
        if not rows:
            return AnalysisResponse(
                data=AnalysisResponseData(
                    tam=0,
                    sam=0,
                    som=0,
                    competitors=[],
                    trend="stable",
                    verdict="neutral",
                )
            )

        records = [self._build_record(point, metric) for point, metric in rows]
        self._fill_missing_values(records)
        idea_profile = self._build_idea_profile(payload, parsed)
        self._calculate_scores(records, parsed, idea_profile)

        suitable_records = self._select_suitable_records(records, parsed, idea_profile)
        if not suitable_records:
            suitable_records = self._top_records(records, "opportunity_score", 0.2 if idea_profile["prefers_center"] else 0.3)

        tam = self._calculate_tam(records, parsed, idea_profile)
        sam = self._calculate_sam(suitable_records, parsed, idea_profile)
        som = self._calculate_som(sam, suitable_records)

        return AnalysisResponse(
            data=AnalysisResponseData(
                tam=tam,
                sam=sam,
                som=som,
                competitors=self._calculate_competitors(suitable_records),
                trend=self._calculate_trend(records),
                verdict=self._calculate_verdict(suitable_records),
            )
        )

    async def _parse_idea(self, payload: AnalysisRequest) -> IdeaParseResponseData:
        try:
            parsed_response = await self.idea_parser.parse_idea(
                IdeaParseRequest(idea=payload.idea, region=payload.region)
            )
            return parsed_response.data
        except AppError:
            return IdeaParseResponseData(
                language="unknown",
                normalized_idea=payload.idea[:160],
                business_category=self.DEFAULT_CATEGORY,
                subcategory=None,
                business_model="offline_retail",
                offering_type="offline_location",
                price_segment=None,
                target_audience=[],
                region=payload.region or self.DEFAULT_REGION,
                location_preferences=[],
                planned_average_check=None,
                max_rent_m2=None,
                min_pedestrian_traffic=None,
                min_metro_passenger_flow=None,
                preferred_distance_to_metro_m=None,
                customer_problem=None,
                keywords=[],
                confidence=0.0,
                parser_source="fallback",
            )

    def _build_idea_profile(self, payload: AnalysisRequest, parsed: IdeaParseResponseData) -> dict[str, bool]:
        raw_text = (payload.idea or "").lower()
        parsed_text_parts = [
            parsed.normalized_idea or "",
            parsed.business_category or "",
            parsed.subcategory or "",
            parsed.business_model or "",
            parsed.offering_type or "",
            parsed.customer_problem or "",
            " ".join(parsed.location_preferences or []),
            " ".join(parsed.target_audience or []),
            " ".join(parsed.keywords or []),
            parsed.price_segment or "",
        ]
        parsed_text = " ".join(part.lower() for part in parsed_text_parts if part)

        raw_prefers_center = self._contains_any(raw_text, _CENTER_ALIASES)
        raw_prefers_outskirts = self._contains_any(raw_text, _OUTSKIRTS_ALIASES)
        parsed_prefers_center = self._contains_any(parsed_text, _CENTER_ALIASES)
        parsed_prefers_outskirts = self._contains_any(parsed_text, _OUTSKIRTS_ALIASES)

        return {
            "prefers_metro": self._contains_any(raw_text, _METRO_ALIASES) or self._contains_any(parsed_text, _METRO_ALIASES),
            "prefers_center": raw_prefers_center or (parsed_prefers_center and not raw_prefers_outskirts),
            "prefers_outskirts": raw_prefers_outskirts or (parsed_prefers_outskirts and not raw_prefers_center),
            "takeaway": self._contains_any(raw_text, _TAKEAWAY_ALIASES) or self._contains_any(parsed_text, _TAKEAWAY_ALIASES),
            "office_audience": self._contains_any(raw_text, _OFFICE_ALIASES) or self._contains_any(parsed_text, _OFFICE_ALIASES),
            "commuter_audience": self._contains_any(raw_text, _COMMUTER_ALIASES) or self._contains_any(parsed_text, _COMMUTER_ALIASES),
            "premium": parsed.price_segment == "high" or self._contains_any(raw_text, _PREMIUM_ALIASES) or self._contains_any(parsed_text, _PREMIUM_ALIASES),
            "budget": parsed.price_segment == "low" or self._contains_any(raw_text, _BUDGET_ALIASES) or self._contains_any(parsed_text, _BUDGET_ALIASES),
        }

    def _build_record(self, point, metric) -> dict:
        return {
            "name": point.name,
            "rating": self._to_float(point.rating),
            "pedestrian_traffic_estimate": self._to_float(metric.pedestrian_traffic_estimate),
            "metro_passenger_flow": self._to_float(metric.metro_passenger_flow),
            "distance_to_metro": self._to_float(metric.distance_to_metro),
            "cafes_300m": self._to_float(metric.cafes_300m),
            "cafes_1km": self._to_float(metric.cafes_1km),
            "average_competitor_rating": self._to_float(metric.average_competitor_rating),
            "population_density": self._to_float(metric.population_density),
            "median_income": self._to_float(metric.median_income),
            "office_density": self._to_float(metric.office_density),
            "average_rent_m2": self._to_float(metric.average_rent_m2),
            "average_check": self._to_float(metric.average_check),
            "available_commercial_spaces": self._to_float(metric.available_commercial_spaces),
        }

    def _fill_missing_values(self, records: list[dict]) -> None:
        fields = [
            "rating",
            "pedestrian_traffic_estimate",
            "metro_passenger_flow",
            "distance_to_metro",
            "cafes_300m",
            "cafes_1km",
            "average_competitor_rating",
            "population_density",
            "median_income",
            "office_density",
            "average_rent_m2",
            "average_check",
            "available_commercial_spaces",
        ]

        for field in fields:
            values = [record[field] for record in records if record[field] is not None]
            fallback = median(values) if values else 0.5
            for record in records:
                if record[field] is None:
                    record[field] = fallback

    def _calculate_scores(
        self,
        records: list[dict],
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
    ) -> None:
        fields = [
            "pedestrian_traffic_estimate",
            "metro_passenger_flow",
            "population_density",
            "median_income",
            "office_density",
            "cafes_300m",
            "cafes_1km",
            "average_competitor_rating",
            "distance_to_metro",
            "average_rent_m2",
            "available_commercial_spaces",
            "rating",
            "average_check",
        ]
        normalized = {field: self._normalize(records, field) for field in fields}

        for index, record in enumerate(records):
            metro_component = normalized["metro_passenger_flow"][index]
            pedestrian_component = normalized["pedestrian_traffic_estimate"][index]
            income_component = normalized["median_income"][index]
            office_component = normalized["office_density"][index]
            density_component = normalized["population_density"][index]
            rent_component = self._invert(normalized["average_rent_m2"][index])
            distance_component = self._invert(normalized["distance_to_metro"][index])
            spaces_component = normalized["available_commercial_spaces"][index]
            check_component = normalized["average_check"][index]

            demand_score = (
                0.26 * pedestrian_component
                + 0.18 * metro_component
                + 0.18 * density_component
                + 0.18 * income_component
                + 0.20 * office_component
            )

            feasibility_score = (
                0.34 * distance_component
                + 0.36 * rent_component
                + 0.30 * spaces_component
            )

            competition_score = (
                0.50 * normalized["cafes_300m"][index]
                + 0.35 * normalized["cafes_1km"][index]
                + 0.15 * normalized["average_competitor_rating"][index]
            )

            if idea_profile["prefers_metro"]:
                demand_score += 0.12 * metro_component
                feasibility_score += 0.10 * distance_component

            if idea_profile["prefers_center"]:
                demand_score += 0.08 * metro_component + 0.08 * office_component + 0.06 * income_component
                feasibility_score -= 0.08 * normalized["average_rent_m2"][index]

            if idea_profile["prefers_outskirts"]:
                demand_score -= 0.04 * office_component
                feasibility_score += 0.14 * rent_component + 0.06 * spaces_component
                competition_score -= 0.06 * normalized["cafes_300m"][index]

            if idea_profile["office_audience"]:
                demand_score += 0.10 * office_component

            if idea_profile["commuter_audience"]:
                demand_score += 0.10 * metro_component

            if idea_profile["takeaway"]:
                demand_score += 0.08 * pedestrian_component
                feasibility_score += 0.06 * spaces_component

            if idea_profile["premium"]:
                demand_score += 0.08 * income_component + 0.05 * check_component
                competition_score += 0.04 * normalized["average_competitor_rating"][index]

            if idea_profile["budget"]:
                feasibility_score += 0.10 * rent_component
                demand_score += 0.04 * density_component

            opportunity_score = self._clamp(
                0.52 * demand_score + 0.30 * feasibility_score - 0.22 * competition_score
            )

            record["demand_score"] = self._clamp(demand_score)
            record["competition_score"] = self._clamp(competition_score)
            record["feasibility_score"] = self._clamp(feasibility_score)
            record["opportunity_score"] = opportunity_score
            record["rating_norm"] = normalized["rating"][index]

    def _select_suitable_records(
        self,
        records: list[dict],
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
    ) -> list[dict]:
        suitable = records

        if idea_profile["prefers_metro"]:
            distance_limit = min(self._percentile(records, "distance_to_metro", 0.45), 1000)
            if parsed.preferred_distance_to_metro_m is not None:
                distance_limit = min(distance_limit, parsed.preferred_distance_to_metro_m)
            suitable = [record for record in suitable if record["distance_to_metro"] <= distance_limit]

        if parsed.preferred_distance_to_metro_m is not None and not idea_profile["prefers_metro"]:
            suitable = [
                record for record in suitable
                if record["distance_to_metro"] <= parsed.preferred_distance_to_metro_m
            ]

        if idea_profile["takeaway"] or (parsed.subcategory or "").lower() in _TAKEAWAY_ALIASES:
            traffic_limit = self._percentile(records, "pedestrian_traffic_estimate", 0.6)
            rent_limit = self._percentile(records, "average_rent_m2", 0.7)
            suitable = [
                record for record in suitable
                if record["pedestrian_traffic_estimate"] >= traffic_limit
                and record["average_rent_m2"] <= rent_limit
            ]

        if idea_profile["prefers_center"]:
            metro_limit = self._percentile(records, "metro_passenger_flow", 0.65)
            office_limit = self._percentile(records, "office_density", 0.6)
            suitable = [
                record for record in suitable
                if record["metro_passenger_flow"] >= metro_limit
                and record["office_density"] >= office_limit
            ]

        if idea_profile["prefers_outskirts"]:
            rent_limit = self._percentile(records, "average_rent_m2", 0.4)
            density_limit = self._percentile(records, "population_density", 0.45)
            suitable = [
                record for record in suitable
                if record["average_rent_m2"] <= rent_limit
                and record["population_density"] <= density_limit
            ]

        if parsed.max_rent_m2 is not None:
            suitable = [record for record in suitable if record["average_rent_m2"] <= parsed.max_rent_m2]

        if parsed.min_pedestrian_traffic is not None:
            suitable = [
                record for record in suitable
                if record["pedestrian_traffic_estimate"] >= parsed.min_pedestrian_traffic
            ]

        if parsed.min_metro_passenger_flow is not None:
            suitable = [
                record for record in suitable
                if record["metro_passenger_flow"] >= parsed.min_metro_passenger_flow
            ]

        if idea_profile["office_audience"]:
            office_limit = self._percentile(records, "office_density", 0.55)
            suitable = [record for record in suitable if record["office_density"] >= office_limit]

        if idea_profile["commuter_audience"]:
            flow_limit = self._percentile(records, "metro_passenger_flow", 0.55)
            suitable = [record for record in suitable if record["metro_passenger_flow"] >= flow_limit]

        if idea_profile["premium"]:
            income_limit = self._percentile(records, "median_income", 0.65)
            suitable = [record for record in suitable if record["median_income"] >= income_limit]

        if idea_profile["budget"]:
            rent_limit = self._percentile(records, "average_rent_m2", 0.45)
            suitable = [record for record in suitable if record["average_rent_m2"] <= rent_limit]

        return suitable

    def _calculate_tam(
        self,
        records: list[dict],
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
    ) -> int:
        multiplier = 1.0
        if idea_profile["prefers_center"]:
            multiplier = 1.08
        elif idea_profile["prefers_outskirts"]:
            multiplier = 0.90
        return round(sum(self._market_value(record, parsed) for record in records) * multiplier)

    def _calculate_sam(
        self,
        records: list[dict],
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
    ) -> int:
        multiplier = 1.0
        if idea_profile["premium"]:
            multiplier *= 1.06
        if idea_profile["budget"]:
            multiplier *= 0.94
        return round(sum(self._market_value(record, parsed) for record in records) * multiplier)

    def _calculate_som(self, sam: int, records: list[dict]) -> int:
        avg_opportunity = self._average(records, "opportunity_score")
        avg_competition = self._average(records, "competition_score")
        capture_rate = 0.10
        if avg_competition >= 0.7:
            capture_rate = 0.05
        elif avg_competition <= 0.35 and avg_opportunity >= 0.65:
            capture_rate = 0.12
        return round(sam * avg_opportunity * capture_rate)

    def _calculate_competitors(self, records: list[dict]) -> list[CompetitorShare]:
        ranked = []
        for index, record in enumerate(records):
            influence = (
                0.45 * record.get("rating_norm", 0.5)
                + 0.35 * record["competition_score"]
                + 0.20 * record["demand_score"]
            )
            ranked.append((record["name"] or f"Competitor {index + 1}", influence))

        top = sorted(ranked, key=lambda item: item[1], reverse=True)[:5]
        total = sum(influence for _, influence in top)
        if total <= 0:
            return []

        shares = []
        remaining = 100
        for idx, (name, influence) in enumerate(top):
            if idx == len(top) - 1:
                share = remaining
            else:
                share = round(influence / total * 100)
                remaining -= share
            shares.append(CompetitorShare(name=name, share=max(0, share)))
        return shares

    def _calculate_trend(self, records: list[dict]) -> str:
        growth_index = (
            0.35 * self._average(records, "demand_score")
            + 0.25 * self._average(records, "feasibility_score")
            - 0.25 * self._average(records, "competition_score")
        )
        if growth_index >= 0.6:
            return "growing"
        if growth_index >= 0.4:
            return "stable"
        return "declining"

    def _calculate_verdict(self, records: list[dict]) -> str:
        final_score = (
            0.45 * self._average(records, "demand_score")
            + 0.35 * self._average(records, "feasibility_score")
            + 0.20 * (1 - self._average(records, "competition_score"))
        )
        if final_score >= 0.65:
            return "favorable"
        if final_score >= 0.45:
            return "neutral"
        return "unfavorable"

    def _normalize(self, records: list[dict], field: str) -> list[float]:
        values = [record[field] for record in records]
        min_value = min(values)
        max_value = max(values)
        if math.isclose(min_value, max_value):
            return [0.5 for _ in values]
        return [(value - min_value) / (max_value - min_value) for value in values]

    def _percentile(self, records: list[dict], field: str, percentile: float) -> float:
        values = sorted(record[field] for record in records)
        if not values:
            return 0.0
        index = min(round((len(values) - 1) * percentile), len(values) - 1)
        return values[index]

    def _top_records(self, records: list[dict], field: str, share: float) -> list[dict]:
        limit = max(1, round(len(records) * share))
        return sorted(records, key=lambda record: record[field], reverse=True)[:limit]

    def _average(self, records: list[dict], field: str) -> float:
        if not records:
            return 0.0
        return sum(record[field] for record in records) / len(records)

    def _market_value(self, record: dict, parsed: IdeaParseResponseData) -> float:
        estimated_daily_transactions = (
            self.MIN_DAILY_TRANSACTIONS
            + (self.MAX_DAILY_TRANSACTIONS - self.MIN_DAILY_TRANSACTIONS) * record["demand_score"]
        )
        effective_average_check = parsed.planned_average_check or record["average_check"]
        return effective_average_check * estimated_daily_transactions * self.DAYS_PER_YEAR

    def _to_float(self, value) -> float | None:
        if value is None:
            return None
        return float(value)

    def _invert(self, value: float) -> float:
        return 1 - value

    def _clamp(self, value: float) -> float:
        return min(1.0, max(0.0, value))

    def _contains_any(self, text: str, patterns: set[str]) -> bool:
        return any(pattern in text for pattern in patterns)
