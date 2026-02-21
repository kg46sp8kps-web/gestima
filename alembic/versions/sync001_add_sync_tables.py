"""add sync state and sync log tables

Revision ID: sync001
Revises: z9a0b1c2d3e4
Create Date: 2026-02-21

Adds tables for Infor Smart Polling Sync system (ADR TBD).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "sync001"
down_revision: str = "783a9a0792f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sync_states and sync_logs tables."""

    # Check if sync_states table already exists (idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "sync_states" not in existing_tables:
        op.create_table(
            "sync_states",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(50), nullable=False),
            sa.Column("ido_name", sa.String(100), nullable=False),
            sa.Column("properties", sa.Text(), nullable=False),
            sa.Column("date_field", sa.String(50), nullable=False),
            sa.Column("filter_template", sa.Text(), nullable=True),
            sa.Column("interval_seconds", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_count", sa.Integer(), nullable=False),
            sa.Column("updated_count", sa.Integer(), nullable=False),
            sa.Column("error_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id")
        )
        op.create_index("ix_sync_states_id", "sync_states", ["id"], unique=False)
        op.create_index("ix_sync_states_step_name", "sync_states", ["step_name"], unique=True)

    if "sync_logs" not in existing_tables:
        op.create_table(
            "sync_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("fetched_count", sa.Integer(), nullable=False),
            sa.Column("created_count", sa.Integer(), nullable=False),
            sa.Column("updated_count", sa.Integer(), nullable=False),
            sa.Column("error_count", sa.Integer(), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id")
        )
        op.create_index("ix_sync_logs_id", "sync_logs", ["id"], unique=False)
        op.create_index("ix_sync_logs_step_name", "sync_logs", ["step_name"], unique=False)
        op.create_index("ix_sync_logs_step_created", "sync_logs", ["step_name", "created_at"], unique=False)


def downgrade() -> None:
    """Drop sync_states and sync_logs tables."""

    op.drop_index("ix_sync_logs_step_created", table_name="sync_logs")
    op.drop_index("ix_sync_logs_step_name", table_name="sync_logs")
    op.drop_index("ix_sync_logs_id", table_name="sync_logs")
    op.drop_table("sync_logs")

    op.drop_index("ix_sync_states_step_name", table_name="sync_states")
    op.drop_index("ix_sync_states_id", table_name="sync_states")
    op.drop_table("sync_states")
