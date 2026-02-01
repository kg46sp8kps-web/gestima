"""add_article_number_unique_constraint

Revision ID: i1j2k3l4m5n6
Revises: h7i8j9k0l1m2
Create Date: 2026-02-01 20:00:00.000000

Add UNIQUE constraint to article_number in Part table.

This ensures no duplicate article numbers can exist in the system,
which is critical for AI quote request matching logic.

IMPORTANT: This migration will FAIL if there are existing duplicate
article_numbers in the database. Clean them up first!
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i1j2k3l4m5n6'
down_revision: Union[str, Sequence[str], None] = 'h7i8j9k0l1m2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add UNIQUE constraint to article_number.

    Note: This will fail if there are duplicate article_numbers.
    To fix duplicates before running:

    SELECT article_number, COUNT(*)
    FROM parts
    WHERE deleted_at IS NULL
    GROUP BY article_number
    HAVING COUNT(*) > 1;
    """
    # Add unique constraint
    op.create_unique_constraint(
        'uq_parts_article_number',
        'parts',
        ['article_number']
    )


def downgrade() -> None:
    """Remove UNIQUE constraint from article_number."""
    op.drop_constraint('uq_parts_article_number', 'parts', type_='unique')
