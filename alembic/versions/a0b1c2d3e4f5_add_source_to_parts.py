"""Add source column to parts table

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
Create Date: 2026-02-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: str = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source column with default 'manual'
    op.add_column("parts", sa.Column("source", sa.String(20), nullable=False, server_default="manual"))

    # Mark all existing parts that were imported from Infor
    # They have article_number set AND were not manually created
    # (all current ~18k parts are from Infor import)
    op.execute("""
        UPDATE parts
        SET source = 'infor_import'
        WHERE article_number IS NOT NULL
          AND article_number != ''
          AND deleted_at IS NULL
    """)


def downgrade() -> None:
    op.drop_column("parts", "source")
