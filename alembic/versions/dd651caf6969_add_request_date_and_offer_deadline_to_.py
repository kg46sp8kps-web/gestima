"""add request_date and offer_deadline to quotes

Revision ID: dd651caf6969
Revises: c2d3e4f5g6h7
Create Date: 2026-02-20 13:25:04.245625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd651caf6969'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5g6h7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add request_date and offer_deadline columns to quotes."""
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('request_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('offer_deadline', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_quotes_offer_deadline'), ['offer_deadline'], unique=False)


def downgrade() -> None:
    """Remove request_date and offer_deadline columns from quotes."""
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quotes_offer_deadline'))
        batch_op.drop_column('offer_deadline')
        batch_op.drop_column('request_date')
