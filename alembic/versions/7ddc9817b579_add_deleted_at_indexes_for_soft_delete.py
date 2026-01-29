"""add_deleted_at_indexes_for_soft_delete

Revision ID: 7ddc9817b579
Revises: e1f2a3b4c5d6
Create Date: 2026-01-29 09:18:54.168377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ddc9817b579'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add deleted_at indexes for soft-delete performance (Audit 2026-01-28).

    Problem: 16× queries with `.where(deleted_at.is_(None))` cause full table scans.
    Solution: Add indexes on deleted_at column for all AuditMixin models.
    Expected impact: Parts list 1200ms → 150ms
    """
    # Core entities
    op.create_index('ix_parts_deleted_at', 'parts', ['deleted_at'])
    op.create_index('ix_batches_deleted_at', 'batches', ['deleted_at'])
    op.create_index('ix_batch_sets_deleted_at', 'batch_sets', ['deleted_at'])
    op.create_index('ix_operations_deleted_at', 'operations', ['deleted_at'])
    op.create_index('ix_features_deleted_at', 'features', ['deleted_at'])

    # Materials
    op.create_index('ix_material_items_deleted_at', 'material_items', ['deleted_at'])
    op.create_index('ix_material_groups_deleted_at', 'material_groups', ['deleted_at'])
    op.create_index('ix_material_price_categories_deleted_at', 'material_price_categories', ['deleted_at'])
    op.create_index('ix_material_price_tiers_deleted_at', 'material_price_tiers', ['deleted_at'])
    op.create_index('ix_material_norms_deleted_at', 'material_norms', ['deleted_at'])

    # Technical
    op.create_index('ix_cutting_conditions_deleted_at', 'cutting_conditions', ['deleted_at'])
    op.create_index('ix_work_centers_deleted_at', 'work_centers', ['deleted_at'])

    # System
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])
    op.create_index('ix_system_config_deleted_at', 'system_config', ['deleted_at'])


def downgrade() -> None:
    """Remove deleted_at indexes."""
    op.drop_index('ix_system_config_deleted_at', table_name='system_config')
    op.drop_index('ix_users_deleted_at', table_name='users')
    op.drop_index('ix_work_centers_deleted_at', table_name='work_centers')
    op.drop_index('ix_cutting_conditions_deleted_at', table_name='cutting_conditions')
    op.drop_index('ix_material_norms_deleted_at', table_name='material_norms')
    op.drop_index('ix_material_price_tiers_deleted_at', table_name='material_price_tiers')
    op.drop_index('ix_material_price_categories_deleted_at', table_name='material_price_categories')
    op.drop_index('ix_material_groups_deleted_at', table_name='material_groups')
    op.drop_index('ix_material_items_deleted_at', table_name='material_items')
    op.drop_index('ix_features_deleted_at', table_name='features')
    op.drop_index('ix_operations_deleted_at', table_name='operations')
    op.drop_index('ix_batch_sets_deleted_at', table_name='batch_sets')
    op.drop_index('ix_batches_deleted_at', table_name='batches')
    op.drop_index('ix_parts_deleted_at', table_name='parts')
