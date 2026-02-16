"""Add features extraction columns to time_vision_estimations

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-02-15 10:00:00.000000

Adds feature extraction support for TimeVision v2 pipeline:
- estimation_type: "time_v1" (legacy) vs "features_v2" (new deterministic)
- features_json: AI-extracted features
- features_corrected_json: Human-corrected features (ground truth for fine-tuning)
- calculated_time_min: Deterministic calculation from features
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "w6x7y8z9a0b1"
down_revision: Union[str, None] = "cf31cd62fcfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add estimation_type column with default and index
    op.add_column(
        "time_vision_estimations",
        sa.Column("estimation_type", sa.String(20), nullable=False, server_default="time_v1"),
    )
    op.create_index(
        op.f("ix_time_vision_estimations_estimation_type"),
        "time_vision_estimations",
        ["estimation_type"],
        unique=False,
    )

    # Add features_json column (AI-extracted features)
    op.add_column(
        "time_vision_estimations",
        sa.Column("features_json", sa.Text(), nullable=True),
    )

    # Add features_corrected_json column (human corrections for fine-tuning)
    op.add_column(
        "time_vision_estimations",
        sa.Column("features_corrected_json", sa.Text(), nullable=True),
    )

    # Add calculated_time_min column (deterministic calculation from features)
    op.add_column(
        "time_vision_estimations",
        sa.Column("calculated_time_min", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("time_vision_estimations", "calculated_time_min")
    op.drop_column("time_vision_estimations", "features_corrected_json")
    op.drop_column("time_vision_estimations", "features_json")
    op.drop_index(op.f("ix_time_vision_estimations_estimation_type"), table_name="time_vision_estimations")
    op.drop_column("time_vision_estimations", "estimation_type")
