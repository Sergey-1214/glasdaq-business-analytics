from __future__ import annotations

import csv
import io
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import MarketPointMetric
from src.exceptions import IngestionConflictError, IngestionError, IngestionValidationError
from src.repositories import IngestionRepository
from src.schemas import IngestionRequest, IngestionResponse
from src.schemas.ingestion import MarketPointIngest


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
                        average_check=record.metrics.average_check,
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

    def ingest_uploaded_file(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        region: str,
        source: str = "upload",
        category: str = "coffee_shop",
        notes: str | None = None,
    ) -> IngestionResponse:
        records = self._parse_uploaded_file(
            file_name=file_name,
            file_bytes=file_bytes,
            source=source,
            category=category,
        )

        payload = IngestionRequest(
            source=source,
            region=region,
            records=records,
            notes=notes or f"Uploaded from {file_name}",
        )
        return self.ingest_coffee_shops(payload)

    def _parse_uploaded_file(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        source: str,
        category: str,
    ) -> list[MarketPointIngest]:
        suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
        if suffix == "json":
            return self._parse_json_records(file_bytes, source=source, category=category)
        if suffix == "csv":
            return self._parse_csv_records(file_bytes, source=source, category=category)

        raise IngestionValidationError("Supported upload formats are CSV and JSON")

    def _parse_json_records(self, file_bytes: bytes, *, source: str, category: str) -> list[MarketPointIngest]:
        try:
            payload = json.loads(file_bytes.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IngestionValidationError(f"Invalid JSON file: {exc}") from exc

        if isinstance(payload, dict):
            raw_records = payload.get("records")
        else:
            raw_records = payload

        if not isinstance(raw_records, list) or not raw_records:
            raise IngestionValidationError("JSON file must contain a non-empty array of records")

        return [
            self._normalize_record(record, index=index, source=source, category=category)
            for index, record in enumerate(raw_records, start=1)
        ]

    def _parse_csv_records(self, file_bytes: bytes, *, source: str, category: str) -> list[MarketPointIngest]:
        try:
            content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise IngestionValidationError(f"CSV file must be UTF-8 encoded: {exc}") from exc

        sample = content[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ","

        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        rows = list(reader)
        if not rows:
            raise IngestionValidationError("CSV file is empty")

        return [
            self._normalize_record(row, index=index, source=source, category=category)
            for index, row in enumerate(rows, start=1)
        ]

    def _normalize_record(
        self,
        raw_record: dict,
        *,
        index: int,
        source: str,
        category: str,
    ) -> MarketPointIngest:
        if not isinstance(raw_record, dict):
            raise IngestionValidationError(f"Record #{index} must be an object")

        latitude = self._read_float(raw_record, "latitude", "lat", required=True, index=index)
        longitude = self._read_float(raw_record, "longitude", "lng", "lon", "long", required=True, index=index)
        name = self._read_text(raw_record, "name", "title", default=f"Point {index}")
        external_id = self._read_text(raw_record, "external_id", "id")
        if not external_id:
            slug = name.lower().replace(" ", "-")
            external_id = f"{slug}-{latitude:.6f}-{longitude:.6f}"

        metrics = {
            "distance_to_metro": self._read_float(raw_record, "distance_to_metro"),
            "metro_passenger_flow": self._read_int(raw_record, "metro_passenger_flow"),
            "public_transport_stops_count": self._read_int(raw_record, "public_transport_stops_count"),
            "cafes_300m": self._read_int(raw_record, "cafes_300m"),
            "cafes_1km": self._read_int(raw_record, "cafes_1km"),
            "average_competitor_rating": self._read_float(raw_record, "average_competitor_rating"),
            "population_density": self._read_int(raw_record, "population_density"),
            "median_income": self._read_int(raw_record, "median_income"),
            "office_density": self._read_int(raw_record, "office_density"),
            "average_rent_m2": self._read_float(raw_record, "average_rent_m2"),
            "average_check": self._read_float(raw_record, "average_check"),
            "available_commercial_spaces": self._read_int(raw_record, "available_commercial_spaces"),
            "pedestrian_traffic_estimate": self._read_int(raw_record, "pedestrian_traffic_estimate"),
            "metrics_source_label": self._read_text(raw_record, "metrics_source_label"),
        }

        metro_station_name = self._read_text(raw_record, "station_name", "metro_station", "nearest_metro_station")
        metro_station = None
        if metro_station_name:
            metro_station = {
                "source": self._read_text(raw_record, "station_source", default="upload"),
                "station_name": metro_station_name,
                "line_name": self._read_text(raw_record, "line_name", "metro_line"),
                "passenger_flow": self._read_int(raw_record, "station_passenger_flow", "metro_passenger_flow"),
                "latitude": self._read_float(raw_record, "station_latitude", "metro_lat"),
                "longitude": self._read_float(raw_record, "station_longitude", "metro_lng", "metro_lon"),
            }

        payload = {
            "source": self._read_text(raw_record, "source", default=source),
            "external_id": external_id,
            "external_type": self._read_text(raw_record, "external_type"),
            "name": name,
            "category": self._read_text(raw_record, "category", default=category),
            "latitude": latitude,
            "longitude": longitude,
            "rating": self._read_float(raw_record, "rating"),
            "raw_tags": raw_record.get("raw_tags") if isinstance(raw_record.get("raw_tags"), dict) else None,
            "metro_station": metro_station,
            "metrics": metrics if any(value is not None for value in metrics.values()) else None,
        }

        try:
            return MarketPointIngest.model_validate(payload)
        except Exception as exc:
            raise IngestionValidationError(f"Record #{index} failed validation: {exc}") from exc

    def _read_text(self, record: dict, *keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = record.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return default

    def _read_float(self, record: dict, *keys: str, required: bool = False, index: int | None = None) -> float | None:
        for key in keys:
            value = record.get(key)
            if value in (None, ""):
                continue
            try:
                return float(str(value).replace(" ", "").replace(",", "."))
            except ValueError as exc:
                raise IngestionValidationError(f"Field '{key}' in record #{index or '?'} must be a number") from exc

        if required:
            joined = ", ".join(keys)
            raise IngestionValidationError(f"Record #{index or '?'} is missing required field: {joined}")
        return None

    def _read_int(self, record: dict, *keys: str) -> int | None:
        value = self._read_float(record, *keys)
        if value is None:
            return None
        return int(value)
