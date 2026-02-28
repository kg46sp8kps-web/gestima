"""Add qty_on_hand and qty_available to workshop_order_overviews

Revision ID: wk010_add_qty_on_hand
Revises: wk009_add_jbr_columns
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk010_add_qty_on_hand'
down_revision: str = 'wk009_add_jbr_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workshop_order_overviews', sa.Column('qty_on_hand', sa.Float(), nullable=True))
    op.add_column('workshop_order_overviews', sa.Column('qty_available', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('workshop_order_overviews', 'qty_available')
    op.drop_column('workshop_order_overviews', 'qty_on_hand')
