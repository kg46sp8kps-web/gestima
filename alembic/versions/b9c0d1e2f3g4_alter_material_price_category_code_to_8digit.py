"""Alter MaterialPriceCategory code to 8-digit format

Revision ID: b9c0d1e2f3g4
Revises: o8p9q0r1s2t3
Create Date: 2026-02-03

Changes:
- Alter material_price_categories.code from String(50) to String(8)
- Supports 8-digit codes: 20900000-20909999 (ADR-017)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9c0d1e2f3g4'
down_revision = 'o8p9q0r1s2t3'
branch_labels = None
depends_on = None


def upgrade():
    """Alter code column to String(8) for 8-digit format"""
    # SQLite doesn't support ALTER COLUMN directly
    # For SQLite, we need to recreate the table or use a workaround

    # For development (SQLite), this will work if table is empty or codes are already 8-digit
    # For production, existing data must be migrated first

    with op.batch_alter_table('material_price_categories') as batch_op:
        batch_op.alter_column('code',
            existing_type=sa.String(50),
            type_=sa.String(8),
            existing_nullable=False)


def downgrade():
    """Revert code column back to String(50)"""
    with op.batch_alter_table('material_price_categories') as batch_op:
        batch_op.alter_column('code',
            existing_type=sa.String(8),
            type_=sa.String(50),
            existing_nullable=False)
