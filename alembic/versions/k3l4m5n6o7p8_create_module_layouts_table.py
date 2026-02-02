"""Create module_layouts table (ADR-031)

Revision ID: k3l4m5n6o7p8
Revises: i1j2k3l4m5n6
Create Date: 2026-02-02 15:00:00.000000

Visual Editor backend support: module_layouts table stores user-specific
layout configurations for the CustomizableModule system.

Features:
- Per-user customization
- Multiple layouts per module
- Default layout support
- JSON config storage
- Soft delete support

See ADR-031 for design rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k3l4m5n6o7p8'
down_revision: Union[str, Sequence[str], None] = 'j2k3l4m5n6o7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create module_layouts table"""
    op.create_table(
        'module_layouts',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Core fields
        sa.Column('module_key', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('layout_name', sa.String(200), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),

        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_module_layouts_user_id'),
    )

    # Create composite unique constraint
    op.create_unique_constraint(
        'uq_module_layouts_module_user_name',
        'module_layouts',
        ['module_key', 'user_id', 'layout_name']
    )

    # Create index for fast lookups
    op.create_index(
        'ix_module_layouts_user_module',
        'module_layouts',
        ['user_id', 'module_key', 'deleted_at']
    )


def downgrade() -> None:
    """Drop module_layouts table"""
    op.drop_index('ix_module_layouts_user_module', 'module_layouts')
    op.drop_constraint('uq_module_layouts_module_user_name', 'module_layouts', type_='unique')
    op.drop_table('module_layouts')
