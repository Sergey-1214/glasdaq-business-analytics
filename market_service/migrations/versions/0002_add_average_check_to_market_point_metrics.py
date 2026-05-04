"""add average_check to market point metrics

Revision ID: 0002_add_average_check
Revises: 0001_create_market_tables
Create Date: 2026-05-01 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_add_average_check"
down_revision = "0001_create_market_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_point_metrics",
        sa.Column("average_check", sa.Numeric(precision=10, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("market_point_metrics", "average_check")
