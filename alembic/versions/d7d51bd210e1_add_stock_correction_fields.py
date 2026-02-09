"""add_stock_correction_fields

Revision ID: d7d51bd210e1
Revises: 933da2e09e7a
Create Date: 2026-02-09 12:41:19.377106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7d51bd210e1'
down_revision: Union[str, Sequence[str], None] = '933da2e09e7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add stock correction fields to turning_estimations and milling_estimations tables."""
    # Add columns to turning_estimations (plural)
    with op.batch_alter_table('turning_estimations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('corrected_stock_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('corrected_stock_diameter', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('corrected_stock_length', sa.Float(), nullable=True))

    # Add columns to milling_estimations (plural)
    with op.batch_alter_table('milling_estimations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('corrected_stock_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('corrected_stock_diameter', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('corrected_stock_length', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove stock correction fields."""
    with op.batch_alter_table('milling_estimations', schema=None) as batch_op:
        batch_op.drop_column('corrected_stock_length')
        batch_op.drop_column('corrected_stock_diameter')
        batch_op.drop_column('corrected_stock_type')

    with op.batch_alter_table('turning_estimations', schema=None) as batch_op:
        batch_op.drop_column('corrected_stock_length')
        batch_op.drop_column('corrected_stock_diameter')
        batch_op.drop_column('corrected_stock_type')
