"""add drawing_number to file_links and drop drawings table

Revision ID: aa001_drawing_migration
Revises: dd651caf6969
Create Date: 2026-02-20

ADR-044 Phase 2b: Complete migration from Drawing model to FileRecord/FileLink.
- Adds drawing_number column to file_links
- Drops deprecated drawings table (data already migrated to file_records + file_links)

CRITICAL: Run scripts/migrate_drawings_to_filerecord.py BEFORE this migration!
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aa001_drawing_migration"
down_revision: Union[str, None] = "dd651caf6969"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add drawing_number column to file_links
    with op.batch_alter_table("file_links") as batch_op:
        batch_op.add_column(
            sa.Column("drawing_number", sa.String(50), nullable=True)
        )

    # Step 2: Drop deprecated drawings table
    # (data must be migrated to file_records + file_links before running this!)
    op.drop_table("drawings")


def downgrade() -> None:
    # Re-create drawings table (empty - data is gone)
    op.create_table(
        "drawings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("revision", sa.String(2), nullable=True, server_default="A"),
        sa.Column("file_type", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("deleted_by", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
    )

    # Remove drawing_number from file_links
    with op.batch_alter_table("file_links") as batch_op:
        batch_op.drop_column("drawing_number")
