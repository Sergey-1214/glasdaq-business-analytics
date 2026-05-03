from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import IngestionBatch, MarketPoint, MetroStation
from src.schemas.ingestion import MarketPointIngest, MetroStationIngest


class IngestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_batch(self, source: str, region: str, records_received: int, notes: str | None) -> IngestionBatch:
        batch = IngestionBatch(
            source=source,
            region=region,
            status="running",
            records_received=records_received,
            notes=notes,
        )
        self.db.add(batch)
        self.db.flush()
        return batch

    def mark_batch_completed(self, batch: IngestionBatch) -> None:
        batch.status = "completed"
        batch.finished_at = datetime.now(timezone.utc)

    def mark_batch_failed(self, batch: IngestionBatch, error_message: str) -> None:
        batch.status = "failed"
        batch.finished_at = datetime.now(timezone.utc)
        batch.notes = error_message

    def get_market_point(self, record: MarketPointIngest) -> MarketPoint | None:
        return self.db.scalar(
            select(MarketPoint).where(
                MarketPoint.source == record.source,
                MarketPoint.external_id == record.external_id,
            )
        )

    def save_market_point(self, batch_id, record: MarketPointIngest, market_point: MarketPoint | None) -> MarketPoint:
        if market_point is None:
            market_point = MarketPoint(
                batch_id=batch_id,
                source=record.source,
                external_id=record.external_id,
                external_type=record.external_type,
                name=record.name,
                category=record.category,
                latitude=record.latitude,
                longitude=record.longitude,
                rating=record.rating,
                raw_tags=record.raw_tags,
            )
            self.db.add(market_point)
        else:
            market_point.batch_id = batch_id
            market_point.external_type = record.external_type
            market_point.name = record.name
            market_point.category = record.category
            market_point.latitude = record.latitude
            market_point.longitude = record.longitude
            market_point.rating = record.rating
            market_point.raw_tags = record.raw_tags

        self.db.flush()
        return market_point

    def get_metro_station(self, station: MetroStationIngest) -> MetroStation | None:
        return self.db.scalar(
            select(MetroStation).where(
                MetroStation.source == station.source,
                MetroStation.station_name == station.station_name,
                MetroStation.line_name == station.line_name,
            )
        )

    def save_metro_station(self, batch_id, station: MetroStationIngest, metro_station: MetroStation | None) -> MetroStation:
        if metro_station is None:
            metro_station = MetroStation(
                batch_id=batch_id,
                source=station.source,
                station_name=station.station_name,
                line_name=station.line_name,
                passenger_flow=station.passenger_flow,
                latitude=station.latitude,
                longitude=station.longitude,
            )
            self.db.add(metro_station)
        else:
            metro_station.batch_id = batch_id
            metro_station.passenger_flow = station.passenger_flow
            metro_station.latitude = station.latitude
            metro_station.longitude = station.longitude

        self.db.flush()
        return metro_station
