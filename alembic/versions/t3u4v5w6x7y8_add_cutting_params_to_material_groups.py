"""Add cutting parameters to material_groups

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-02-08 14:00:00.000000

ADR-040: Machining Time Estimation - Material Group Cutting Parameters
Adds ISO group, hardness, MRR, cutting speeds, and penalty factors to material_groups.
Density already exists in the table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 't3u4v5w6x7y8'
down_revision: Union[str, None] = 's2t3u4v5w6x7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cutting parameters to material_groups."""
    # Add ISO material group
    op.add_column('material_groups', sa.Column('iso_group', sa.String(5), nullable=True))
    op.add_column('material_groups', sa.Column('hardness_hb', sa.Float(), nullable=True))

    # Material Removal Rates (cm³/min)
    op.add_column('material_groups', sa.Column('mrr_turning_roughing', sa.Float(), nullable=True))
    op.add_column('material_groups', sa.Column('mrr_turning_finishing', sa.Float(), nullable=True))
    op.add_column('material_groups', sa.Column('mrr_milling_roughing', sa.Float(), nullable=True))
    op.add_column('material_groups', sa.Column('mrr_milling_finishing', sa.Float(), nullable=True))

    # Cutting speeds (m/min)
    op.add_column('material_groups', sa.Column('cutting_speed_turning', sa.Float(), nullable=True))
    op.add_column('material_groups', sa.Column('cutting_speed_milling', sa.Float(), nullable=True))

    # Feed rates
    op.add_column('material_groups', sa.Column('feed_turning', sa.Float(), nullable=True))
    op.add_column('material_groups', sa.Column('feed_milling', sa.Float(), nullable=True))

    # Constraint penalties (default values for backward compatibility)
    op.add_column('material_groups', sa.Column('deep_pocket_penalty', sa.Float(), nullable=True, server_default='1.8'))
    op.add_column('material_groups', sa.Column('thin_wall_penalty', sa.Float(), nullable=True, server_default='2.5'))

    # Metadata
    op.add_column('material_groups', sa.Column('cutting_data_source', sa.String(100), nullable=True))

    # Create index on iso_group for faster queries
    op.create_index('ix_material_groups_iso_group', 'material_groups', ['iso_group'])


def downgrade() -> None:
    """Remove cutting parameters from material_groups."""
    op.drop_index('ix_material_groups_iso_group', table_name='material_groups')
    op.drop_column('material_groups', 'cutting_data_source')
    op.drop_column('material_groups', 'thin_wall_penalty')
    op.drop_column('material_groups', 'deep_pocket_penalty')
    op.drop_column('material_groups', 'feed_milling')
    op.drop_column('material_groups', 'feed_turning')
    op.drop_column('material_groups', 'cutting_speed_milling')
    op.drop_column('material_groups', 'cutting_speed_turning')
    op.drop_column('material_groups', 'mrr_milling_finishing')
    op.drop_column('material_groups', 'mrr_milling_roughing')
    op.drop_column('material_groups', 'mrr_turning_finishing')
    op.drop_column('material_groups', 'mrr_turning_roughing')
    op.drop_column('material_groups', 'hardness_hb')
    op.drop_column('material_groups', 'iso_group')
