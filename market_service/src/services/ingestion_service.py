from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import MarketPointMetric
from src.exceptions import IngestionConflictError, IngestionError
from src.repositories import IngestionRepository
from src.schemas import IngestionRequest, IngestionResponse


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = IngestionRepository(db)

    def ingest_coffee_shops(self, payload: IngestionRequest) -> IngestionResponse:
        batch = self.repository.create_batch(
            source=payload.source,
            region=payload.region,
            records_received=len(payload.records),
            notes=payload.notes,
        )
        self.db.commit()

        points_upserted = 0
        metro_stations_upserted = 0
        metrics_created = 0

        try:
            for record in payload.records:
                market_point = self.repository.save_market_point(
                    batch.id,
                    record,
                    self.repository.get_market_point(record),
                )
                points_upserted += 1

                metro_station = None
                if record.metro_station is not None:
                    metro_station = self.repository.save_metro_station(
                        batch.id,
                        record.metro_station,
                        self.repository.get_metro_station(record.metro_station),
                    )
                    metro_stations_upserted += 1

                if record.metrics is not None:
                    metric = MarketPointMetric(
                        market_point_id=market_point.id,
                        batch_id=batch.id,
                        nearest_metro_station_id=metro_station.id if metro_station is not None else None,
                        distance_to_metro=record.metrics.distance_to_metro,
                        metro_passenger_flow=record.metrics.metro_passenger_flow,
                        public_transport_stops_count=record.metrics.public_transport_stops_count,
                        cafes_300m=record.metrics.cafes_300m,
                        cafes_1km=record.metrics.cafes_1km,
                        average_competitor_rating=record.metrics.average_competitor_rating,
                        population_density=record.metrics.population_density,
                        median_income=record.metrics.median_income,
                        office_density=record.metrics.office_density,
                        average_rent_m2=record.metrics.average_rent_m2,
                        available_commercial_spaces=record.metrics.available_commercial_spaces,
                        pedestrian_traffic_estimate=record.metrics.pedestrian_traffic_estimate,
                        metrics_source_label=record.metrics.metrics_source_label,
                    )
                    self.db.add(metric)
                    metrics_created += 1

            self.repository.mark_batch_completed(batch)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()

            persisted_batch = self.db.get(type(batch), batch.id)
            if persisted_batch is not None:
                self.repository.mark_batch_failed(persisted_batch, f"Database integrity error: {exc}")
                self.db.commit()

            raise IngestionConflictError("Database conflict while ingesting records") from exc
        except Exception as exc:
            self.db.rollback()

            persisted_batch = self.db.get(type(batch), batch.id)
            if persisted_batch is not None:
                self.repository.mark_batch_failed(persisted_batch, str(exc))
                self.db.commit()

            raise IngestionError(f"Ingestion failed: {exc}") from exc

        return IngestionResponse(
            batch_id=str(batch.id),
            records_received=batch.records_received,
            points_upserted=points_upserted,
            metro_stations_upserted=metro_stations_upserted,
            metrics_created=metrics_created,
        )
