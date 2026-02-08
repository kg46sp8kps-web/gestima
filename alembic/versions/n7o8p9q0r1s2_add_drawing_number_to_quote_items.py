"""add_drawing_number_to_quote_items

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n7o8p9q0r1s2'
down_revision = 'm6n7o8p9q0r1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add drawing_number column to quote_items
    op.add_column('quote_items', sa.Column('drawing_number', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove drawing_number column from quote_items
    op.drop_column('quote_items', 'drawing_number')
