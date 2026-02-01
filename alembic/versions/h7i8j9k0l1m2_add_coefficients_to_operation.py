"""add_coefficients_to_operation

Revision ID: h7i8j9k0l1m2
Revises: g5h6i7j8k9l0
Create Date: 2026-02-01 12:30:00.000000

Add manning_coefficient and machine_utilization_coefficient fields to Operation table.
These coefficients allow fine-tuning of operation time calculations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h7i8j9k0l1m2'
down_revision: Union[str, Sequence[str], None] = 'g5h6i7j8k9l0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add coefficient columns to operations table."""
    op.add_column('operations', sa.Column('manning_coefficient', sa.Float(), nullable=True))
    op.add_column('operations', sa.Column('machine_utilization_coefficient', sa.Float(), nullable=True))

    # Set default values for existing records
    op.execute("UPDATE operations SET manning_coefficient = 100.0 WHERE manning_coefficient IS NULL")
    op.execute("UPDATE operations SET machine_utilization_coefficient = 100.0 WHERE machine_utilization_coefficient IS NULL")


def downgrade() -> None:
    """Remove coefficient columns from operations table."""
    op.drop_column('operations', 'machine_utilization_coefficient')
    op.drop_column('operations', 'manning_coefficient')
