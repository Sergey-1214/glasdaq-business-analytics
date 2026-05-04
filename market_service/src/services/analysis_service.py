from __future__ import annotations

import math
from statistics import median

from sqlalchemy.orm import Session

from src.repositories import AnalysisRepository
from src.exceptions import AppError
from src.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResponseData,
    CompetitorShare,
    IdeaParseRequest,
    IdeaParseResponseData,
)
from src.services.idea_parser_service import IdeaParserService


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
        category = parsed.business_category or self.DEFAULT_CATEGORY
        if category == "other":
            category = self.DEFAULT_CATEGORY

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
        self._calculate_scores(records, parsed)

        suitable_records = self._select_suitable_records(records, parsed)
        if not suitable_records:
            suitable_records = self._top_records(records, "opportunity_score", 0.3)

        tam = self._calculate_tam(records, parsed)
        sam = self._calculate_sam(suitable_records, parsed)
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

    def _calculate_scores(self, records: list[dict], parsed: IdeaParseResponseData) -> None:
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
        ]
        normalized = {field: self._normalize(records, field) for field in fields}
        prefers_metro = "near_metro" in (parsed.location_preferences or [])

        for index, record in enumerate(records):
            if prefers_metro:
                demand_score = (
                    0.25 * normalized["pedestrian_traffic_estimate"][index]
                    + 0.30 * normalized["metro_passenger_flow"][index]
                    + 0.15 * normalized["population_density"][index]
                    + 0.15 * normalized["median_income"][index]
                    + 0.15 * normalized["office_density"][index]
                )
                feasibility_score = (
                    0.35 * self._invert(normalized["distance_to_metro"][index])
                    + 0.35 * self._invert(normalized["average_rent_m2"][index])
                    + 0.30 * normalized["available_commercial_spaces"][index]
                )
            else:
                demand_score = (
                    0.30 * normalized["pedestrian_traffic_estimate"][index]
                    + 0.20 * normalized["metro_passenger_flow"][index]
                    + 0.20 * normalized["population_density"][index]
                    + 0.15 * normalized["median_income"][index]
                    + 0.15 * normalized["office_density"][index]
                )
                feasibility_score = (
                    0.20 * self._invert(normalized["distance_to_metro"][index])
                    + 0.45 * self._invert(normalized["average_rent_m2"][index])
                    + 0.35 * normalized["available_commercial_spaces"][index]
                )

            competition_score = (
                0.50 * normalized["cafes_300m"][index]
                + 0.35 * normalized["cafes_1km"][index]
                + 0.15 * normalized["average_competitor_rating"][index]
            )
            opportunity_score = self._clamp(
                0.50 * demand_score + 0.30 * feasibility_score - 0.20 * competition_score
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
    ) -> list[dict]:
        suitable = records

        if "near_metro" in (parsed.location_preferences or []):
            distance_limit = min(self._percentile(records, "distance_to_metro", 0.5), 1000)
            if parsed.preferred_distance_to_metro_m is not None:
                distance_limit = min(distance_limit, parsed.preferred_distance_to_metro_m)
            suitable = [record for record in suitable if record["distance_to_metro"] <= distance_limit]

        if parsed.preferred_distance_to_metro_m is not None and "near_metro" not in (parsed.location_preferences or []):
            suitable = [
                record
                for record in suitable
                if record["distance_to_metro"] <= parsed.preferred_distance_to_metro_m
            ]

        if parsed.subcategory == "takeaway":
            traffic_limit = self._percentile(records, "pedestrian_traffic_estimate", 0.5)
            rent_limit = self._percentile(records, "average_rent_m2", 0.75)
            suitable = [
                record
                for record in suitable
                if record["pedestrian_traffic_estimate"] >= traffic_limit
                and record["average_rent_m2"] <= rent_limit
            ]

        if parsed.max_rent_m2 is not None:
            suitable = [record for record in suitable if record["average_rent_m2"] <= parsed.max_rent_m2]

        if parsed.min_pedestrian_traffic is not None:
            suitable = [
                record
                for record in suitable
                if record["pedestrian_traffic_estimate"] >= parsed.min_pedestrian_traffic
            ]

        if parsed.min_metro_passenger_flow is not None:
            suitable = [
                record
                for record in suitable
                if record["metro_passenger_flow"] >= parsed.min_metro_passenger_flow
            ]

        if "office workers" in (parsed.target_audience or []):
            office_limit = self._percentile(records, "office_density", 0.5)
            suitable = [record for record in suitable if record["office_density"] >= office_limit]

        if "commuters" in (parsed.target_audience or []):
            flow_limit = self._percentile(records, "metro_passenger_flow", 0.5)
            suitable = [record for record in suitable if record["metro_passenger_flow"] >= flow_limit]

        return suitable

    def _calculate_tam(self, records: list[dict], parsed: IdeaParseResponseData) -> int:
        return round(sum(self._market_value(record, parsed) for record in records))

    def _calculate_sam(self, records: list[dict], parsed: IdeaParseResponseData) -> int:
        return round(sum(self._market_value(record, parsed) for record in records))

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

        return [
            CompetitorShare(name=name, share=round(influence / total * 100))
            for name, influence in top
        ]

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
