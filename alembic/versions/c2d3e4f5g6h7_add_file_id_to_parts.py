"""add file_id to parts

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2026-02-17

ADR-044 Phase 2b: Add file_id FK to parts for primary drawing reference.
Same pattern as TimeVision file_id (y8z9a0b1c2d3).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5g6h7"
down_revision: str = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file_id column to parts table."""

    # Check if column already exists (idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("parts")]

    if "file_id" not in columns:
        with op.batch_alter_table("parts", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("file_id", sa.Integer(), nullable=True)
            )

            batch_op.create_foreign_key(
                "fk_parts_file_id",
                "file_records",
                ["file_id"],
                ["id"],
                ondelete="SET NULL"
            )

            batch_op.create_index(
                "ix_parts_file_id",
                ["file_id"],
                unique=False
            )


def downgrade() -> None:
    """Remove file_id column from parts table."""

    with op.batch_alter_table("parts", schema=None) as batch_op:
        batch_op.drop_index("ix_parts_file_id")
        batch_op.drop_constraint("fk_parts_file_id", type_="foreignkey")
        batch_op.drop_column("file_id")
