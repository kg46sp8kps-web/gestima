"""Add ai_model to time_vision_estimations

Revision ID: c8d9e0f1a2b3
Revises: b6c7d8e9f0a1
Create Date: 2026-02-13 18:00:00.000000

Stores full model identifier (e.g. 'ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH')
to distinguish fine-tuned model versions. ai_provider stays for quick filtering.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "time_vision_estimations",
        sa.Column("ai_model", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("time_vision_estimations", "ai_model")
