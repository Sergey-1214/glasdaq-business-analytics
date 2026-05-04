from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import MarketPoint, MarketPointMetric


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_market_points_with_latest_metrics(
        self,
        region: str,
        category: str,
    ) -> list[tuple[MarketPoint, MarketPointMetric]]:
        latest_metric_ids = (
            select(MarketPointMetric.market_point_id, MarketPointMetric.id)
            .order_by(MarketPointMetric.market_point_id, MarketPointMetric.created_at.desc())
            .distinct(MarketPointMetric.market_point_id)
            .subquery()
        )

        query = (
            select(MarketPoint, MarketPointMetric)
            .join(MarketPointMetric, MarketPointMetric.market_point_id == MarketPoint.id)
            .join(latest_metric_ids, latest_metric_ids.c.id == MarketPointMetric.id)
            .where(MarketPoint.category == category)
        )

        # Current data has region on batches only; keep this parameter in the API contract
        # and repository signature so filtering can be tightened when regional data matures.
        _ = region
        return list(self.db.execute(query).all())
