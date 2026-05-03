"""create market tables

Revision ID: 0001_create_market_tables
Revises:
Create Date: 2026-04-22 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_market_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "market_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_type", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("raw_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_market_points_source_external_id"),
    )

    op.create_table(
        "metro_stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=False),
        sa.Column("line_name", sa.String(length=255), nullable=True),
        sa.Column("passenger_flow", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "station_name", "line_name", name="uq_metro_source_station_line"),
    )

    op.create_table(
        "market_point_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("market_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nearest_metro_station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("distance_to_metro", sa.Float(), nullable=True),
        sa.Column("metro_passenger_flow", sa.Integer(), nullable=True),
        sa.Column("public_transport_stops_count", sa.Integer(), nullable=True),
        sa.Column("cafes_300m", sa.Integer(), nullable=True),
        sa.Column("cafes_1km", sa.Integer(), nullable=True),
        sa.Column("average_competitor_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("population_density", sa.Integer(), nullable=True),
        sa.Column("median_income", sa.Integer(), nullable=True),
        sa.Column("office_density", sa.Integer(), nullable=True),
        sa.Column("average_rent_m2", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("available_commercial_spaces", sa.Integer(), nullable=True),
        sa.Column("pedestrian_traffic_estimate", sa.Integer(), nullable=True),
        sa.Column("metrics_source_label", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["market_point_id"], ["market_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nearest_metro_station_id"], ["metro_stations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_market_points_batch_id", "market_points", ["batch_id"])
    op.create_index("ix_market_points_category", "market_points", ["category"])
    op.create_index("ix_market_point_metrics_batch_id", "market_point_metrics", ["batch_id"])
    op.create_index("ix_market_point_metrics_market_point_id", "market_point_metrics", ["market_point_id"])
    op.create_index(
        "ix_market_point_metrics_nearest_metro_station_id",
        "market_point_metrics",
        ["nearest_metro_station_id"],
    )
    op.create_index("ix_metro_stations_batch_id", "metro_stations", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_metro_stations_batch_id", table_name="metro_stations")
    op.drop_index("ix_market_point_metrics_nearest_metro_station_id", table_name="market_point_metrics")
    op.drop_index("ix_market_point_metrics_market_point_id", table_name="market_point_metrics")
    op.drop_index("ix_market_point_metrics_batch_id", table_name="market_point_metrics")
    op.drop_index("ix_market_points_category", table_name="market_points")
    op.drop_index("ix_market_points_batch_id", table_name="market_points")
    op.drop_table("market_point_metrics")
    op.drop_table("metro_stations")
    op.drop_table("market_points")
    op.drop_table("ingestion_batches")
