"""add_missing_fk_indexes

Revision ID: 783a9a0792f4
Revises: ab002_partial_unique_article_number
Create Date: 2026-02-20 22:27:05.109118

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '783a9a0792f4'
down_revision: Union[str, Sequence[str], None] = 'ab002_partial_unique_article_number'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing indexes on FK columns for JOIN performance."""
    with op.batch_alter_table('batch_sets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_batch_sets_frozen_by_id'), ['frozen_by_id'], unique=False)

    with op.batch_alter_table('material_inputs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_material_inputs_material_item_id'), ['material_item_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_material_inputs_price_category_id'), ['price_category_id'], unique=False)

    with op.batch_alter_table('material_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_material_items_material_group_id'), ['material_group_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_material_items_price_category_id'), ['price_category_id'], unique=False)

    with op.batch_alter_table('material_price_tiers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_material_price_tiers_price_category_id'), ['price_category_id'], unique=False)

    with op.batch_alter_table('module_layouts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_module_layouts_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_operations_ai_estimation_id'), ['ai_estimation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_operations_work_center_id'), ['work_center_id'], unique=False)

    with op.batch_alter_table('production_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_production_records_work_center_id'), ['work_center_id'], unique=False)


def downgrade() -> None:
    """Remove FK indexes."""
    with op.batch_alter_table('production_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_production_records_work_center_id'))

    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_operations_work_center_id'))
        batch_op.drop_index(batch_op.f('ix_operations_ai_estimation_id'))

    with op.batch_alter_table('module_layouts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_module_layouts_user_id'))

    with op.batch_alter_table('material_price_tiers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_material_price_tiers_price_category_id'))

    with op.batch_alter_table('material_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_material_items_price_category_id'))
        batch_op.drop_index(batch_op.f('ix_material_items_material_group_id'))

    with op.batch_alter_table('material_inputs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_material_inputs_price_category_id'))
        batch_op.drop_index(batch_op.f('ix_material_inputs_material_item_id'))

    with op.batch_alter_table('batch_sets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_batch_sets_frozen_by_id'))
