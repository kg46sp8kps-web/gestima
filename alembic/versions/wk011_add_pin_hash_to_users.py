"""Add pin_hash to users table for operator terminal PIN login

Revision ID: wk011_add_pin_hash_to_users
Revises: wk010_add_qty_on_hand
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk011_add_pin_hash_to_users'
down_revision: str = 'wk010_add_qty_on_hand'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('pin_hash', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'pin_hash')
