"""add_customer_request_number_to_quote

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-02-02 12:00:00.000000

Add customer_request_number field to Quote table for storing customer's RFQ number.
This field allows tracking the original customer request number (e.g., P20971, RFQ-2026-001).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j2k3l4m5n6o7'
down_revision: Union[str, Sequence[str], None] = 'i1j2k3l4m5n6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add customer_request_number column to quotes table."""
    op.add_column('quotes', sa.Column('customer_request_number', sa.String(length=50), nullable=True))
    op.create_index('ix_quotes_customer_request_number', 'quotes', ['customer_request_number'])


def downgrade() -> None:
    """Remove customer_request_number column from quotes table."""
    op.drop_index('ix_quotes_customer_request_number', table_name='quotes')
    op.drop_column('quotes', 'customer_request_number')
