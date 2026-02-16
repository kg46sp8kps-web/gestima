"""add file_id to timevision

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-02-15 14:30:00.000000

ADR-044 Phase 2: FileManager integration with TimeVision
- Add file_id FK to time_vision_estimations
- Add index on file_id for performance
- pdf_filename and pdf_path columns STAY (backward compat, Phase 3 cleanup)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "y8z9a0b1c2d3"
down_revision: Union[str, None] = "x7y8z9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file_id column to time_vision_estimations."""

    # Check if column already exists (idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("time_vision_estimations")]

    if "file_id" not in columns:
        # Use batch_alter_table for SQLite compatibility
        with op.batch_alter_table("time_vision_estimations", schema=None) as batch_op:
            # Add file_id column
            batch_op.add_column(
                sa.Column("file_id", sa.Integer(), nullable=True)
            )

            # Add FK constraint
            batch_op.create_foreign_key(
                "fk_timevision_file_id",
                "file_records",
                ["file_id"],
                ["id"],
                ondelete="SET NULL"
            )

            # Add index for performance
            batch_op.create_index(
                "ix_time_vision_estimations_file_id",
                ["file_id"],
                unique=False
            )


def downgrade() -> None:
    """Remove file_id column from time_vision_estimations."""

    with op.batch_alter_table("time_vision_estimations", schema=None) as batch_op:
        # Drop index first
        batch_op.drop_index("ix_time_vision_estimations_file_id")

        # Drop FK constraint
        batch_op.drop_constraint("fk_timevision_file_id", type_="foreignkey")

        # Drop column
        batch_op.drop_column("file_id")
