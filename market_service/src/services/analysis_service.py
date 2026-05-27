from __future__ import annotations

import logging
import math
import re
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
    LocationAssessment,
)
from src.services.idea_parser_service import IdeaParserService

logger = logging.getLogger(__name__)


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
    DEFAULT_GEO_RADIUS_M = 2000

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
            logger.warning(
                "No market points found for region='%s' and category='%s'. Check ingestion data and region normalization.",
                region,
                category,
            )
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
        location_hints = self._extract_location_hints(payload, parsed)
        localized_records = self._filter_by_geo_radius(records, region, payload, parsed, idea_profile, location_hints)
        if not localized_records:
            logger.warning("Geo-radius filtering returned no points; fallback to text/metro filtering was used.")
            localized_records = self._filter_by_location_hints(records, parsed, idea_profile, location_hints)
        scoring_scope = localized_records or records
        if not localized_records:
            logger.warning("Location filtering returned no points; fallback to all points in region/category was used.")
        self._calculate_scores(scoring_scope, parsed, idea_profile)

        suitable_records = self._select_suitable_records(scoring_scope, parsed, idea_profile)
        if not suitable_records:
            suitable_records = self._top_records(scoring_scope, "opportunity_score", 0.2 if idea_profile["prefers_center"] else 0.3)

        tam = self._calculate_tam(scoring_scope, parsed, idea_profile)
        sam = self._calculate_sam(suitable_records, parsed, idea_profile)
        som = self._calculate_som(sam, suitable_records)
        location_assessment = self._build_location_assessment(records, payload)

        return AnalysisResponse(
            data=AnalysisResponseData(
                tam=tam,
                sam=sam,
                som=som,
                competitors=self._calculate_competitors(suitable_records),
                trend=self._calculate_trend(scoring_scope),
                verdict=self._calculate_verdict(suitable_records),
                location_assessment=location_assessment,
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
                district=None,
                query_type=None,
                location_preferences=[],
                planned_average_check=None,
                max_rent_m2=None,
                min_pedestrian_traffic=None,
                min_metro_passenger_flow=None,
                preferred_distance_to_metro_m=None,
                constraints=[],
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
            parsed.query_type or "",
            parsed.customer_problem or "",
            parsed.district or "",
            " ".join(parsed.location_preferences or []),
            " ".join(parsed.target_audience or []),
            " ".join(parsed.constraints or []),
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
            "latitude": self._to_float(point.latitude),
            "longitude": self._to_float(point.longitude),
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
            "nearest_metro_station": getattr(getattr(metric, "nearest_metro_station", None), "station_name", None),
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

    def _extract_location_hints(
        self,
        payload: AnalysisRequest,
        parsed: IdeaParseResponseData,
    ) -> list[str]:
        hints = []
        if parsed.district:
            hints.append(parsed.district)
        hints.extend(parsed.location_preferences or [])
        hints.extend(parsed.keywords or [])
        hints.append(payload.idea or "")
        return [self._normalize_text(h) for h in hints if h]

    def _filter_by_location_hints(
        self,
        records: list[dict],
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
        location_hints: list[str],
    ) -> list[dict]:
        if not location_hints and not parsed.preferred_distance_to_metro_m and not idea_profile["prefers_metro"]:
            return []

        metro_distance_limit = parsed.preferred_distance_to_metro_m
        if metro_distance_limit is None and idea_profile["prefers_metro"]:
            metro_distance_limit = 700

        matched = []
        for record in records:
            if metro_distance_limit is not None and record["distance_to_metro"] > metro_distance_limit:
                continue

            name_blob = " ".join(
                [
                    self._normalize_text(str(record.get("name") or "")),
                    self._normalize_text(str(record.get("nearest_metro_station") or "")),
                ]
            )
            if location_hints:
                tokens = [token for hint in location_hints for token in hint.split() if len(token) >= 4]
                if tokens and not any(token in name_blob for token in tokens):
                    continue
            matched.append(record)

        if matched:
            return matched

        # Fallback: if exact place token matching failed, still narrow by metro proximity.
        if metro_distance_limit is not None:
            return [record for record in records if record["distance_to_metro"] <= metro_distance_limit]
        return []

    def _filter_by_geo_radius(
        self,
        records: list[dict],
        region: str,
        payload: AnalysisRequest,
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
        location_hints: list[str],
    ) -> list[dict]:
        anchor = self._resolve_anchor_point(region, payload, parsed, location_hints)
        if anchor is None:
            return []

        radius_m = self._resolve_geo_radius(parsed, idea_profile)
        anchor_lat, anchor_lon = anchor
        filtered = []
        for record in records:
            lat = record.get("latitude")
            lon = record.get("longitude")
            if lat is None or lon is None:
                continue
            distance = self._haversine_m(anchor_lat, anchor_lon, lat, lon)
            if distance <= radius_m:
                filtered.append(record)
        return filtered

    def _resolve_anchor_point(
        self,
        region: str,
        payload: AnalysisRequest,
        parsed: IdeaParseResponseData,
        location_hints: list[str],
    ) -> tuple[float, float] | None:
        selected_coordinates = self._extract_selected_coordinates(payload)
        if selected_coordinates is not None:
            return selected_coordinates

        station_candidates = []
        if parsed.district:
            station_candidates.append(parsed.district)
        station_candidates.extend(parsed.location_preferences or [])
        station_candidates.extend(parsed.keywords or [])
        station_candidates.extend(location_hints)

        for candidate in station_candidates:
            normalized = self._normalize_text(candidate)
            for token in normalized.split():
                if len(token) < 4:
                    continue
                coords = self.repository.find_metro_station_coordinates(region=region, station_hint=token)
                if coords is not None:
                    return coords
        return None

    def _resolve_geo_radius(
        self,
        parsed: IdeaParseResponseData,
        idea_profile: dict[str, bool],
    ) -> int:
        if parsed.preferred_distance_to_metro_m is not None:
            return max(500, int(parsed.preferred_distance_to_metro_m) * 2)
        if idea_profile["prefers_metro"]:
            return 1200
        if idea_profile["prefers_center"]:
            return 1800
        if idea_profile["prefers_outskirts"]:
            return 3000
        return self.DEFAULT_GEO_RADIUS_M

    def _build_location_assessment(
        self,
        records: list[dict],
        payload: AnalysisRequest,
    ) -> LocationAssessment | None:
        selected_coordinates = self._extract_selected_coordinates(payload)
        if selected_coordinates is None:
            return None

        selected_latitude, selected_longitude = selected_coordinates
        if not records:
            return None

        ranked_by_distance = []
        for record in records:
            latitude = record.get("latitude")
            longitude = record.get("longitude")
            if latitude is None or longitude is None:
                continue
            distance = self._haversine_m(selected_latitude, selected_longitude, latitude, longitude)
            ranked_by_distance.append({**record, "distance_to_selected": distance})

        if not ranked_by_distance:
            return None

        ranked_by_distance.sort(key=lambda item: item["distance_to_selected"])
        nearest = ranked_by_distance[0]
        local_scope = [record for record in ranked_by_distance if record["distance_to_selected"] <= 1500]
        if not local_scope:
            local_scope = ranked_by_distance[:5]

        competitors_within_500m = sum(1 for record in ranked_by_distance if record["distance_to_selected"] <= 500)
        competitors_within_1km = sum(1 for record in ranked_by_distance if record["distance_to_selected"] <= 1000)

        pedestrian_traffic = self._weighted_average(local_scope, "pedestrian_traffic_estimate")
        metro_passenger_flow = self._weighted_average(local_scope, "metro_passenger_flow")
        average_rent = self._weighted_average(local_scope, "average_rent_m2")
        average_check = self._weighted_average(local_scope, "average_check")
        median_income = self._weighted_average(local_scope, "median_income")
        office_density = self._weighted_average(local_scope, "office_density")
        available_spaces = self._weighted_average(local_scope, "available_commercial_spaces")
        distance_to_metro = self._weighted_average(local_scope, "distance_to_metro")

        pedestrian_norm = self._relative_position(
            pedestrian_traffic,
            [record["pedestrian_traffic_estimate"] for record in records],
        )
        metro_norm = self._relative_position(
            metro_passenger_flow,
            [record["metro_passenger_flow"] for record in records],
        )
        income_norm = self._relative_position(
            median_income,
            [record["median_income"] for record in records],
        )
        rent_norm = self._invert(
            self._relative_position(
                average_rent,
                [record["average_rent_m2"] for record in records],
            )
        )
        competition_norm = self._relative_position(
            competitors_within_500m,
            [record["cafes_300m"] for record in records],
        )
        office_norm = self._relative_position(
            office_density,
            [record["office_density"] for record in records],
        )
        spaces_norm = self._relative_position(
            available_spaces,
            [record["available_commercial_spaces"] for record in records],
        )
        metro_distance_norm = self._invert(
            self._relative_position(
                distance_to_metro,
                [record["distance_to_metro"] for record in records],
            )
        )

        opportunity_score = self._clamp(
            0.24 * pedestrian_norm
            + 0.16 * metro_norm
            + 0.14 * income_norm
            + 0.12 * office_norm
            + 0.12 * rent_norm
            + 0.10 * spaces_norm
            + 0.12 * metro_distance_norm
            - 0.18 * competition_norm
        )
        verdict = self._location_verdict(opportunity_score)
        summary = self._location_summary(
            nearest_name=nearest.get("name"),
            nearest_distance_m=nearest["distance_to_selected"],
            competitors_within_500m=competitors_within_500m,
            opportunity_score=opportunity_score,
        )

        return LocationAssessment(
            latitude=round(selected_latitude, 6),
            longitude=round(selected_longitude, 6),
            nearest_competitor_name=nearest.get("name"),
            nearest_competitor_distance_m=round(nearest["distance_to_selected"]),
            competitors_within_500m=competitors_within_500m,
            competitors_within_1km=competitors_within_1km,
            pedestrian_traffic_estimate=round(pedestrian_traffic),
            metro_passenger_flow=round(metro_passenger_flow),
            average_rent_m2=round(average_rent),
            average_check=round(average_check),
            median_income=round(median_income),
            opportunity_score=round(opportunity_score * 100),
            verdict=verdict,
            summary=summary,
        )

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
                demand_score += 0.08 * income_component + 0.06 * check_component
                competition_score += 0.04 * normalized["average_competitor_rating"][index]

            if idea_profile["budget"]:
                feasibility_score += 0.10 * rent_component
                demand_score += 0.04 * density_component

            # Keep average check impact moderate for all scenarios, not only premium.
            demand_score += 0.04 * check_component

            opportunity_score = self._clamp(
                0.52 * demand_score + 0.30 * feasibility_score - 0.22 * competition_score
            )

            record["demand_score"] = self._clamp(demand_score)
            record["competition_score"] = self._clamp(competition_score)
            record["feasibility_score"] = self._clamp(feasibility_score)
            record["opportunity_score"] = opportunity_score
            record["rating_norm"] = normalized["rating"][index]
            record["check_fit_score"] = self._check_fit_score(
                record_check=record["average_check"],
                planned_check=parsed.planned_average_check,
            )

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
            check_fit = record.get("check_fit_score", 0.5)
            influence = (
                0.40 * record.get("rating_norm", 0.5)
                + 0.30 * record["competition_score"]
                + 0.20 * record["demand_score"]
                + 0.10 * check_fit
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

    def _check_fit_score(self, record_check: float, planned_check: float | None) -> float:
        if record_check <= 0:
            return 0.5
        if planned_check is None or planned_check <= 0:
            return 0.5
        relative_gap = abs(record_check - planned_check) / planned_check
        # 0 gap => 1.0, 100%+ gap => 0.0
        return self._clamp(1.0 - relative_gap)

    def _to_float(self, value) -> float | None:
        if value is None:
            return None
        return float(value)

    def _invert(self, value: float) -> float:
        return 1 - value

    def _clamp(self, value: float) -> float:
        return min(1.0, max(0.0, value))

    def _relative_position(self, value: float, population: list[float]) -> float:
        if not population:
            return 0.5
        min_value = min(population)
        max_value = max(population)
        if math.isclose(min_value, max_value):
            return 0.5
        return self._clamp((value - min_value) / (max_value - min_value))

    def _weighted_average(self, records: list[dict], field: str) -> float:
        weighted_sum = 0.0
        total_weight = 0.0
        for record in records:
            value = record.get(field)
            if value is None:
                continue
            distance = max(float(record.get("distance_to_selected") or 0.0), 75.0)
            weight = 1 / distance
            weighted_sum += float(value) * weight
            total_weight += weight

        if total_weight <= 0:
            values = [float(record[field]) for record in records if record.get(field) is not None]
            return sum(values) / len(values) if values else 0.0
        return weighted_sum / total_weight

    def _extract_selected_coordinates(self, payload: AnalysisRequest) -> tuple[float, float] | None:
        if payload.selected_latitude is None or payload.selected_longitude is None:
            return None
        return float(payload.selected_latitude), float(payload.selected_longitude)

    def _location_verdict(self, opportunity_score: float) -> str:
        if opportunity_score >= 0.66:
            return "favorable"
        if opportunity_score >= 0.45:
            return "neutral"
        return "unfavorable"

    def _location_summary(
        self,
        nearest_name: str | None,
        nearest_distance_m: float,
        competitors_within_500m: int,
        opportunity_score: float,
    ) -> str:
        score_percent = round(opportunity_score * 100)
        nearest_text = (
            f"Ближайший конкурент: {nearest_name}, {round(nearest_distance_m)} м."
            if nearest_name
            else "Ближайший конкурент не найден."
        )
        density_text = (
            "Конкуренция очень плотная."
            if competitors_within_500m >= 4
            else "Конкуренция умеренная."
            if competitors_within_500m >= 2
            else "Непосредственно рядом конкурентов немного."
        )
        return f"{nearest_text} {density_text} Интегральная оценка точки: {score_percent}/100."

    def _haversine_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _contains_any(self, text: str, patterns: set[str]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _normalize_text(self, value: str) -> str:
        normalized = value.strip().lower().replace("ё", "е")
        return re.sub(r"\s+", " ", normalized)
