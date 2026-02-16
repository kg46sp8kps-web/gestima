"""add_human_estimate_min

Revision ID: ae265e925f90
Revises: v5w6x7y8z9a0
Create Date: 2026-02-13 17:03:51.974501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae265e925f90'
down_revision: Union[str, Sequence[str], None] = 'v5w6x7y8z9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add human_estimate_min field to time_vision_estimations
    with op.batch_alter_table('time_vision_estimations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('human_estimate_min', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove human_estimate_min field from time_vision_estimations
    with op.batch_alter_table('time_vision_estimations', schema=None) as batch_op:
        batch_op.drop_column('human_estimate_min')
