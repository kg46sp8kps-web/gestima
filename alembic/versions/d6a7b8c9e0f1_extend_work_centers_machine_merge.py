"""Extend work_centers with Machine fields (merge)

Revision ID: d6a7b8c9e0f1
Revises: c5e8f2a1b3d4
Create Date: 2026-01-28 18:00:00.000000

Merge Machine model fields into WorkCenter for single source of truth.
Added: capabilities, production suitability, setup times, bar feeder specs.

See ADR-021 for design rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a7b8c9e0f1'
down_revision: Union[str, Sequence[str], None] = 'c5e8f2a1b3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Machine-derived fields to work_centers table"""
    # Tech specs extensions
    op.add_column('work_centers', sa.Column('min_workpiece_diameter', sa.Float(), nullable=True))
    op.add_column('work_centers', sa.Column('subtype', sa.String(50), nullable=True))

    # Bar feeder / Saw specs
    op.add_column('work_centers', sa.Column('max_bar_diameter', sa.Float(), nullable=True))
    op.add_column('work_centers', sa.Column('max_cut_diameter', sa.Float(), nullable=True))
    op.add_column('work_centers', sa.Column('bar_feed_max_length', sa.Float(), nullable=True))

    # Capabilities
    op.add_column('work_centers', sa.Column('has_bar_feeder', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('work_centers', sa.Column('has_sub_spindle', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('work_centers', sa.Column('has_milling', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('work_centers', sa.Column('max_milling_tools', sa.Integer(), nullable=True))

    # Production suitability
    op.add_column('work_centers', sa.Column('suitable_for_series', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('work_centers', sa.Column('suitable_for_single', sa.Boolean(), nullable=False, server_default='1'))

    # Setup times
    op.add_column('work_centers', sa.Column('setup_base_min', sa.Float(), nullable=False, server_default='30.0'))
    op.add_column('work_centers', sa.Column('setup_per_tool_min', sa.Float(), nullable=False, server_default='3.0'))


def downgrade() -> None:
    """Remove Machine-derived fields from work_centers table"""
    op.drop_column('work_centers', 'setup_per_tool_min')
    op.drop_column('work_centers', 'setup_base_min')
    op.drop_column('work_centers', 'suitable_for_single')
    op.drop_column('work_centers', 'suitable_for_series')
    op.drop_column('work_centers', 'max_milling_tools')
    op.drop_column('work_centers', 'has_milling')
    op.drop_column('work_centers', 'has_sub_spindle')
    op.drop_column('work_centers', 'has_bar_feeder')
    op.drop_column('work_centers', 'bar_feed_max_length')
    op.drop_column('work_centers', 'max_cut_diameter')
    op.drop_column('work_centers', 'max_bar_diameter')
    op.drop_column('work_centers', 'subtype')
    op.drop_column('work_centers', 'min_workpiece_diameter')
