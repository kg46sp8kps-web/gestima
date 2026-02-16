"""Add shape column to material_price_categories

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-02-13

Adds shape column (StockShape enum) for robust PriceCategory matching
during Infor import. Replaces fragile keyword-in-name matching.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v5w6x7y8z9a0'
down_revision = 'u4v5w6x7y8z9'
branch_labels = None
depends_on = None


def upgrade():
    """Add shape column to material_price_categories"""
    op.add_column('material_price_categories',
        sa.Column('shape', sa.String(20), nullable=True, index=True)
    )


def downgrade():
    """Remove shape column from material_price_categories"""
    op.drop_column('material_price_categories', 'shape')
