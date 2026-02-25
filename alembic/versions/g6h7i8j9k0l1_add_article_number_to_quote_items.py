"""add article_number to quote_items

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-02-25

Stores the supplier article_number as a snapshot field on QuoteItem
so the quote is self-contained even after part data changes.
"""

from alembic import op
import sqlalchemy as sa

revision = 'g6h7i8j9k0l1'
down_revision = 'f5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'quote_items',
        sa.Column('article_number', sa.String(50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('quote_items', 'article_number')
