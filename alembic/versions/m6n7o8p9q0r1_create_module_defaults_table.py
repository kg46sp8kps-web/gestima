"""Create module_defaults table (ADR-031)

Revision ID: m6n7o8p9q0r1
Revises: l4m5n6o7p8q9
Create Date: 2026-02-02 16:00:00.000000

Module-wide default settings (distinct from per-user ModuleLayout).

Purpose:
- ModuleDefaults: Global defaults for module types (e.g., 'part-main', 'part-pricing')
- ModuleLayout: User-specific saved layouts/views

Features:
- UNIQUE constraint on module_type (one defaults per module type)
- Width/height validation (200-3000px) enforced by Pydantic
- JSON settings for additional configuration
- Soft delete support

See ADR-031 for design rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'm6n7o8p9q0r1'
down_revision: Union[str, Sequence[str], None] = 'l4m5n6o7p8q9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create module_defaults table"""
    op.create_table(
        'module_defaults',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Core fields
        sa.Column('module_type', sa.String(100), nullable=False, unique=True),
        sa.Column('default_width', sa.Integer(), nullable=False),
        sa.Column('default_height', sa.Integer(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),

        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )

    # Create index for fast lookups by module_type
    op.create_index(
        'ix_module_defaults_module_type',
        'module_defaults',
        ['module_type']
    )

    # Create index for soft delete queries
    op.create_index(
        'ix_module_defaults_deleted_at',
        'module_defaults',
        ['deleted_at']
    )


def downgrade() -> None:
    """Drop module_defaults table"""
    op.drop_index('ix_module_defaults_deleted_at', 'module_defaults')
    op.drop_index('ix_module_defaults_module_type', 'module_defaults')
    op.drop_table('module_defaults')
