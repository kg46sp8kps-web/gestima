"""Add batch_approx to quote_items

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2026-02-25

Adds batch_approx flag to quote_items. True when unit_price came from
nearest-lower batch (not an exact quantity match) — used to show UI warning.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'f5g6h7i8j9k0'
down_revision = 'e4f5g6h7i8j9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'quote_items',
        sa.Column('batch_approx', sa.Boolean(), server_default='0', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('quote_items', 'batch_approx')
