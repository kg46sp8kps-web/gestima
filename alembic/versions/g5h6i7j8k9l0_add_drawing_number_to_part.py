"""add_drawing_number_to_part

Revision ID: g5h6i7j8k9l0
Revises: f4a5b6c7d8e9
Create Date: 2026-02-01 12:00:00.000000

Add drawing_number field to Part table for custom drawing identification.
This field allows users to specify drawing number independent of file path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5h6i7j8k9l0'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add drawing_number column to parts table."""
    op.add_column('parts', sa.Column('drawing_number', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove drawing_number column from parts table."""
    op.drop_column('parts', 'drawing_number')
