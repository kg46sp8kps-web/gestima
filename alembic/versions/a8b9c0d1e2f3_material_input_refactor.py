"""material_input_refactor

Revision ID: a8b9c0d1e2f3
Revises: 7ddc9817b579
Create Date: 2026-01-29 14:30:00.000000

ADR-024: Material inputs refactor (v1.8.0)

Changes:
- Create material_inputs table (material moved from Part to separate table)
- Create material_operation_link table (M:N relationship)
- Add Part.revision, Part.customer_revision, Part.status fields
- Drop Part.material_* fields (8 columns)
- NO DATA MIGRATION (empty DB)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = '7ddc9817b579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Material inputs refactor: Move material from Part to separate table.

    Benefits:
    - Part is lean master data (identity only)
    - MaterialInput is independent (supports 1:N materials per part)
    - M:N relationship with Operations (flexible consumption tracking)
    - Prepared for BOM migration (v3.0 PLM)
    """

    # ═══════════════════════════════════════════════════════════
    # STEP 1: Create material_inputs table
    # ═══════════════════════════════════════════════════════════

    op.create_table(
        'material_inputs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False, server_default='0'),

        # Material reference
        sa.Column('price_category_id', sa.Integer(), sa.ForeignKey('material_price_categories.id', ondelete='SET NULL'), nullable=False),
        sa.Column('material_item_id', sa.Integer(), sa.ForeignKey('material_items.id', ondelete='SET NULL'), nullable=True),

        # Stock geometry
        sa.Column('stock_shape', sa.String(50), nullable=False),
        sa.Column('stock_diameter', sa.Float(), nullable=True),
        sa.Column('stock_length', sa.Float(), nullable=True),
        sa.Column('stock_width', sa.Float(), nullable=True),
        sa.Column('stock_height', sa.Float(), nullable=True),
        sa.Column('stock_wall_thickness', sa.Float(), nullable=True),

        # Quantity
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('notes', sa.String(500), nullable=True),

        # AuditMixin fields
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )

    # Indexes
    op.create_index('ix_material_inputs_part_id', 'material_inputs', ['part_id'])
    op.create_index('ix_material_inputs_seq', 'material_inputs', ['part_id', 'seq'])
    op.create_index('ix_material_inputs_deleted_at', 'material_inputs', ['deleted_at'])

    # ═══════════════════════════════════════════════════════════
    # STEP 2: Create material_operation_link table (M:N)
    # ═══════════════════════════════════════════════════════════

    op.create_table(
        'material_operation_link',
        sa.Column('material_input_id', sa.Integer(), sa.ForeignKey('material_inputs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('operation_id', sa.Integer(), sa.ForeignKey('operations.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('consumed_quantity', sa.Integer(), nullable=True),
    )

    op.create_index('ix_mat_op_link_material', 'material_operation_link', ['material_input_id'])
    op.create_index('ix_mat_op_link_operation', 'material_operation_link', ['operation_id'])

    # ═══════════════════════════════════════════════════════════
    # STEP 3: Add new fields to Part
    # ═══════════════════════════════════════════════════════════

    op.add_column('parts', sa.Column('revision', sa.String(2), nullable=False, server_default='A'))
    op.add_column('parts', sa.Column('customer_revision', sa.String(50), nullable=True))
    op.add_column('parts', sa.Column('status', sa.String(20), nullable=False, server_default='active'))

    # ═══════════════════════════════════════════════════════════
    # STEP 4: Drop old columns from Part
    # ═══════════════════════════════════════════════════════════

    # SQLite doesn't support DROP COLUMN directly, use batch mode
    with op.batch_alter_table('parts') as batch_op:
        batch_op.drop_column('material_item_id')
        batch_op.drop_column('price_category_id')
        batch_op.drop_column('stock_shape')
        batch_op.drop_column('stock_diameter')
        batch_op.drop_column('stock_length')
        batch_op.drop_column('stock_width')
        batch_op.drop_column('stock_height')
        batch_op.drop_column('stock_wall_thickness')


def downgrade() -> None:
    """Reverse migration (restore Part.material_* fields, drop new tables)."""

    # Add columns back to Part
    with op.batch_alter_table('parts') as batch_op:
        batch_op.add_column(sa.Column('material_item_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('price_category_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('stock_shape', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('stock_diameter', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stock_length', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stock_width', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stock_height', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stock_wall_thickness', sa.Float(), nullable=True))

    # Drop new Part fields
    with op.batch_alter_table('parts') as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('customer_revision')
        batch_op.drop_column('revision')

    # Drop new tables
    op.drop_index('ix_mat_op_link_operation')
    op.drop_index('ix_mat_op_link_material')
    op.drop_table('material_operation_link')

    op.drop_index('ix_material_inputs_deleted_at')
    op.drop_index('ix_material_inputs_seq')
    op.drop_index('ix_material_inputs_part_id')
    op.drop_table('material_inputs')
