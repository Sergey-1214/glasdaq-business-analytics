from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    market_points: Mapped[list["MarketPoint"]] = relationship(back_populates="batch")
    metro_stations: Mapped[list["MetroStation"]] = relationship(back_populates="batch")
    point_metrics: Mapped[list["MarketPointMetric"]] = relationship(back_populates="batch")


class MarketPoint(Base):
    __tablename__ = "market_points"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_market_points_source_external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="osm")
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="coffee_shop")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    raw_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    batch: Mapped[IngestionBatch | None] = relationship(back_populates="market_points")
    metrics: Mapped[list["MarketPointMetric"]] = relationship(back_populates="market_point")


class MetroStation(Base):
    __tablename__ = "metro_stations"
    __table_args__ = (UniqueConstraint("source", "station_name", "line_name", name="uq_metro_source_station_line"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="mos_ru")
    station_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passenger_flow: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    batch: Mapped[IngestionBatch | None] = relationship(back_populates="metro_stations")
    point_metrics: Mapped[list["MarketPointMetric"]] = relationship(back_populates="nearest_metro_station")


class MarketPointMetric(Base):
    __tablename__ = "market_point_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    nearest_metro_station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metro_stations.id", ondelete="SET NULL"),
        nullable=True,
    )
    distance_to_metro: Mapped[float | None] = mapped_column(Float, nullable=True)
    metro_passenger_flow: Mapped[int | None] = mapped_column(Integer, nullable=True)
    public_transport_stops_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cafes_300m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cafes_1km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_competitor_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    population_density: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    office_density: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_rent_m2: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    available_commercial_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pedestrian_traffic_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_source_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    market_point: Mapped[MarketPoint] = relationship(back_populates="metrics")
    batch: Mapped[IngestionBatch | None] = relationship(back_populates="point_metrics")
    nearest_metro_station: Mapped[MetroStation | None] = relationship(back_populates="point_metrics")
