"""Add batch_sets table (ADR-022)

Revision ID: e1f2a3b4c5d6
Revises: 34aee236ec56
Create Date: 2026-01-28 22:00:00.000000

BatchSet model for grouping Batches into pricing sets.
Random numbering: 35XXXXXX (35000000-35999999)

See ADR-022 for design rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = '34aee236ec56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create batch_sets table and add FK to batches"""

    # 1. Create batch_sets table
    op.create_table(
        'batch_sets',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Identification (ADR-022: 8-digit, prefix 35, random)
        sa.Column('set_number', sa.String(8), nullable=False, unique=True, index=True),

        # Part relationship (nullable - SET NULL on delete for history)
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('parts.id', ondelete='SET NULL'), nullable=True, index=True),

        # Name (auto-generated timestamp)
        sa.Column('name', sa.String(100), nullable=False, index=True),

        # Status (draft | frozen)
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', index=True),

        # Freeze metadata
        sa.Column('frozen_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('frozen_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),

        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )

    # 2. Add batch_set_id FK to batches table
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('batch_set_id', sa.Integer(), nullable=True)
        )
        batch_op.create_index('ix_batches_batch_set_id', ['batch_set_id'])
        batch_op.create_foreign_key(
            'fk_batches_batch_set_id',
            'batch_sets',
            ['batch_set_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    """Remove batch_sets table and FK from batches"""

    # 1. Remove FK from batches
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.drop_constraint('fk_batches_batch_set_id', type_='foreignkey')
        batch_op.drop_index('ix_batches_batch_set_id')
        batch_op.drop_column('batch_set_id')

    # 2. Drop batch_sets table
    op.drop_table('batch_sets')
