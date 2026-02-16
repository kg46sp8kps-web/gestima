"""Add ai_provider to time_vision_estimations

Revision ID: u4v5w6x7y8z9
Revises: abc123def456
Create Date: 2026-02-13 10:00:00.000000

Adds ai_provider column to track which AI model generated each estimation.
Values: "claude", "openai", "openai_ft" (fine-tuned)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, None] = "abc123def456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "time_vision_estimations",
        sa.Column("ai_provider", sa.String(20), nullable=False, server_default="claude"),
    )


def downgrade() -> None:
    op.drop_column("time_vision_estimations", "ai_provider")
