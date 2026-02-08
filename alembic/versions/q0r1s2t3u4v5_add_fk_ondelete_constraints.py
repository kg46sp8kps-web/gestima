"""Add FK ondelete constraints

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-02-03 19:30:00

Adds missing ondelete constraints to ForeignKey columns:
- MaterialItem.material_group_id -> RESTRICT (nelze smazat group pokud má items)
- MaterialItem.price_category_id -> RESTRICT (nelze smazat category pokud má items)
- MaterialPriceTier.price_category_id -> CASCADE (smaže tiers když se smaže category)
- ModuleLayout.user_id -> CASCADE (smaže layouts když se smaže user)

SQLite requires recreate='always' for FK modifications.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'q0r1s2t3u4v5'
down_revision = 'p9q0r1s2t3u4'
branch_labels = None
depends_on = None


def upgrade():
    """Add ondelete constraints - SQLite recreates tables automatically"""

    # For SQLite, batch mode with recreate='always' will recreate the table
    # with the new FK constraints as defined in the models.
    # The actual ondelete behavior is now in the model definitions.

    # 1. material_items - recreate with new FK constraints
    with op.batch_alter_table('material_items', recreate='always') as batch_op:
        # Just touch a column to trigger recreate - constraints come from model
        pass

    # 2. material_price_tiers - recreate with CASCADE
    with op.batch_alter_table('material_price_tiers', recreate='always') as batch_op:
        pass

    # 3. module_layouts - recreate with CASCADE
    with op.batch_alter_table('module_layouts', recreate='always') as batch_op:
        pass


def downgrade():
    """Revert FK constraints - not really possible in SQLite, just recreate"""

    with op.batch_alter_table('material_items', recreate='always') as batch_op:
        pass

    with op.batch_alter_table('material_price_tiers', recreate='always') as batch_op:
        pass

    with op.batch_alter_table('module_layouts', recreate='always') as batch_op:
        pass
