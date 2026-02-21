"""partial_unique_article_number

Revision ID: ab002_partial_unique_article_number
Revises: aa001_drawing_migration
Create Date: 2026-02-20

Replace full unique index on article_number with partial unique index
(WHERE deleted_at IS NULL), so soft-deleted parts don't block re-creation
of a new part with the same article_number.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "ab002_partial_unique_article_number"
down_revision: Union[str, Sequence[str], None] = "aa001_drawing_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # Drop existing full unique index on article_number.
    # SQLAlchemy created it as ix_parts_article_number (from unique=True on Column).
    # Migration i1j2k3l4m5n6 may have also tried to add uq_parts_article_number,
    # but in SQLite that constraint is reflected as the index below.
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_parts_article_number"))
    connection.execute(sa.text("DROP INDEX IF EXISTS uq_parts_article_number"))

    # Create partial unique index — only active (non-deleted) rows are checked.
    # Allows creating a new part with the same article_number after soft-delete.
    connection.execute(sa.text(
        "CREATE UNIQUE INDEX uq_parts_article_number_active "
        "ON parts (article_number) WHERE deleted_at IS NULL"
    ))


def downgrade() -> None:
    connection = op.get_bind()

    # Remove partial index
    connection.execute(sa.text("DROP INDEX IF EXISTS uq_parts_article_number_active"))

    # Restore full unique index
    connection.execute(sa.text(
        "CREATE UNIQUE INDEX ix_parts_article_number ON parts (article_number)"
    ))
