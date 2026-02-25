"""Add delivery_terms to quotes

Revision ID: d4e5f6g7h8i9
Revises: z9a0b1c2d3e4
Create Date: 2026-02-25

Adds delivery_terms field to quotes table for shipping/delivery conditions.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('quotes', sa.Column('delivery_terms', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('quotes', 'delivery_terms')
