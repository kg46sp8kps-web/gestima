"""add file_records and file_links tables

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-02-15 09:10:00.000000

Centralized file management system (ADR-044):
- FileRecord: Physical file storage registry with SHA-256 integrity
- FileLink: Polymorphic entity-file relationships
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "x7y8z9a0b1c2"
down_revision: Union[str, None] = "w6x7y8z9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create file_records and file_links tables."""

    # Check if file_records already exists (idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "file_records" not in existing_tables:
        # Create file_records table
        op.create_table(
            "file_records",
            sa.Column("id", sa.Integer(), nullable=False),
            # File identity
            sa.Column("file_hash", sa.String(length=64), nullable=False),  # SHA-256
            sa.Column("file_path", sa.String(length=500), nullable=False),  # Relative path
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            # File metadata
            sa.Column("file_size", sa.Integer(), nullable=False),  # Bytes
            sa.Column("file_type", sa.String(length=10), nullable=False),  # "pdf", "step", "nc", "xlsx"
            sa.Column("mime_type", sa.String(length=100), nullable=False),
            # Lifecycle status
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),  # "temp", "active", "archived"
            # Audit fields (AuditMixin)
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("updated_by", sa.String(length=100), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by", sa.String(length=100), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("file_path", name="uq_file_path"),
        )

        # Create indexes for file_records
        with op.batch_alter_table("file_records", schema=None) as batch_op:
            batch_op.create_index("ix_file_records_id", ["id"], unique=False)
            batch_op.create_index("ix_file_records_file_hash", ["file_hash"], unique=False)
            batch_op.create_index("ix_file_records_file_type", ["file_type"], unique=False)
            batch_op.create_index("ix_file_records_status", ["status"], unique=False)
            batch_op.create_index("ix_file_records_deleted_at", ["deleted_at"], unique=False)

    if "file_links" not in existing_tables:
        # Create file_links table
        op.create_table(
            "file_links",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("file_id", sa.Integer(), nullable=False),
            # Polymorphic link
            sa.Column("entity_type", sa.String(length=50), nullable=False),  # "part", "quote_item", "timevision"
            sa.Column("entity_id", sa.Integer(), nullable=False),
            # Business metadata
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("revision", sa.String(length=2), nullable=True),  # "A", "B", "C"
            sa.Column("link_type", sa.String(length=20), nullable=False, server_default="drawing"),  # "drawing", "step_model", "nc_program"
            # Audit fields (AuditMixin)
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("updated_by", sa.String(length=100), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by", sa.String(length=100), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["file_id"], ["file_records.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("file_id", "entity_type", "entity_id", name="uq_file_link"),
        )

        # Create indexes for file_links
        with op.batch_alter_table("file_links", schema=None) as batch_op:
            batch_op.create_index("ix_file_links_id", ["id"], unique=False)
            batch_op.create_index("ix_file_links_file_id", ["file_id"], unique=False)
            batch_op.create_index("ix_file_links_entity_type", ["entity_type"], unique=False)
            batch_op.create_index("ix_file_links_entity_id", ["entity_id"], unique=False)
            batch_op.create_index("ix_file_links_entity", ["entity_type", "entity_id"], unique=False)
            batch_op.create_index("ix_file_links_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    """Drop file_records and file_links tables."""
    op.drop_table("file_links")
    op.drop_table("file_records")
