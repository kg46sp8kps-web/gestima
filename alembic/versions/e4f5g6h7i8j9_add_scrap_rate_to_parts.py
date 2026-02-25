"""add_scrap_rate_to_parts

Revision ID: e4f5g6h7i8j9
Revises: d4e5f6g7h8i9
Create Date: 2026-02-25

Add scrap_rate_percent field to parts table.
Scrap rate is applied to material and machining costs before overhead and margin.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5g6h7i8j9'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scrap_rate_percent column to parts table."""
    op.add_column('parts', sa.Column('scrap_rate_percent', sa.Float(), nullable=True))
    op.execute("UPDATE parts SET scrap_rate_percent = 0.0 WHERE scrap_rate_percent IS NULL")


def downgrade() -> None:
    """Remove scrap_rate_percent column from parts table."""
    op.drop_column('parts', 'scrap_rate_percent')
