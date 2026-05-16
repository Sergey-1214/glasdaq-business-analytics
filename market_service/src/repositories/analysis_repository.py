from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import IngestionBatch, MarketPoint, MarketPointMetric


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

        normalized_region = region.strip().lower()

        query = (
            select(MarketPoint, MarketPointMetric)
            .join(MarketPointMetric, MarketPointMetric.market_point_id == MarketPoint.id)
            .join(latest_metric_ids, latest_metric_ids.c.id == MarketPointMetric.id)
            .outerjoin(IngestionBatch, IngestionBatch.id == MarketPoint.batch_id)
            .where(MarketPoint.category == category)
        )

        if normalized_region:
            query = query.where(func.lower(IngestionBatch.region) == normalized_region)

        return list(self.db.execute(query).all())
