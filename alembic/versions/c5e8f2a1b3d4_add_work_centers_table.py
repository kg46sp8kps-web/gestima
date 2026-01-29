"""Add work_centers table (ADR-021)

Revision ID: c5e8f2a1b3d4
Revises: bb9294eaadcc
Create Date: 2026-01-28 16:00:00.000000

WorkCenter model for TPV (technology planning) and MES preparation.
Sequential numbering: 80XXXXXX (80000001-80999999)

See ADR-021 for design rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e8f2a1b3d4'
down_revision: Union[str, Sequence[str], None] = 'bb9294eaadcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create work_centers table"""
    op.create_table(
        'work_centers',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Identification (ADR-017 v2.0: 8-digit, prefix 80, sequential)
        sa.Column('work_center_number', sa.String(8), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),

        # Type classification (enum stored as string)
        sa.Column('work_center_type', sa.String(50), nullable=False),

        # Economics (pro TPV kalkulace) - all optional for virtual work centers
        sa.Column('hourly_rate_amortization', sa.Float(), nullable=True),
        sa.Column('hourly_rate_labor', sa.Float(), nullable=True),
        sa.Column('hourly_rate_tools', sa.Float(), nullable=True),
        sa.Column('hourly_rate_overhead', sa.Float(), nullable=True),

        # Tech specs (optional - pro constraint checking)
        sa.Column('max_workpiece_diameter', sa.Float(), nullable=True),
        sa.Column('max_workpiece_length', sa.Float(), nullable=True),
        sa.Column('axes', sa.Integer(), nullable=True),

        # Organization
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='99'),
        sa.Column('notes', sa.Text(), nullable=True),

        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )

    # Create index on work_center_type for filtering
    op.create_index('ix_work_centers_type', 'work_centers', ['work_center_type'])
    op.create_index('ix_work_centers_is_active', 'work_centers', ['is_active'])


def downgrade() -> None:
    """Drop work_centers table"""
    op.drop_index('ix_work_centers_is_active', 'work_centers')
    op.drop_index('ix_work_centers_type', 'work_centers')
    op.drop_table('work_centers')
