"""Add constraints and indexes to module_layouts

Revision ID: l4m5n6o7p8q9
Revises: k3l4m5n6o7p8
Create Date: 2026-02-02 15:15:00.000000

Add missing constraints and indexes to module_layouts table:
- Unique constraint on (module_key, user_id, layout_name)
- Composite index on (user_id, module_key, deleted_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l4m5n6o7p8q9'
down_revision: Union[str, Sequence[str], None] = 'k3l4m5n6o7p8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add constraints and indexes to module_layouts"""
    # SQLite requires batch mode for adding constraints
    with op.batch_alter_table('module_layouts', schema=None) as batch_op:
        # Add unique constraint
        batch_op.create_unique_constraint(
            'uq_module_layouts_module_user_name',
            ['module_key', 'user_id', 'layout_name']
        )

    # Add composite index for fast lookups (can be done outside batch)
    op.create_index(
        'ix_module_layouts_user_module',
        'module_layouts',
        ['user_id', 'module_key', 'deleted_at']
    )


def downgrade() -> None:
    """Remove constraints and indexes"""
    op.drop_index('ix_module_layouts_user_module', 'module_layouts')

    with op.batch_alter_table('module_layouts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_module_layouts_module_user_name', type_='unique')
