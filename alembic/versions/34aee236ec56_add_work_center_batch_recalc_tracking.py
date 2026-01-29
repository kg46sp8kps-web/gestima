"""add_work_center_batch_recalc_tracking

Revision ID: 34aee236ec56
Revises: 123020d96ea3
Create Date: 2026-01-28 21:15:21.585972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34aee236ec56'
down_revision: Union[str, Sequence[str], None] = '123020d96ea3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add batch recalculation tracking timestamps to work_centers."""
    with op.batch_alter_table('work_centers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_rate_changed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('batches_recalculated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove batch recalculation tracking timestamps."""
    with op.batch_alter_table('work_centers', schema=None) as batch_op:
        batch_op.drop_column('batches_recalculated_at')
        batch_op.drop_column('last_rate_changed_at')
