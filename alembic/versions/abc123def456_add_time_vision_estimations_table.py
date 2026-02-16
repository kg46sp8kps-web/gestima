"""add_time_vision_estimations_table

Revision ID: abc123def456
Revises: 218fabd7a6d0
Create Date: 2026-02-11 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = '218fabd7a6d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add time_vision_estimations table for AI machining time estimation."""
    op.create_table(
        'time_vision_estimations',
        sa.Column('id', sa.Integer(), nullable=False),
        # Source
        sa.Column('pdf_filename', sa.String(length=255), nullable=False),
        sa.Column('pdf_path', sa.String(length=500), nullable=False),
        # Vision extraction results
        sa.Column('part_number_detected', sa.String(length=100), nullable=True),
        sa.Column('material_detected', sa.String(length=100), nullable=True),
        sa.Column('material_group_id', sa.Integer(), nullable=True),
        sa.Column('material_coefficient', sa.Float(), nullable=True),
        sa.Column('part_type', sa.String(length=10), nullable=True),
        sa.Column('complexity', sa.String(length=20), nullable=True),
        sa.Column('max_diameter_mm', sa.Float(), nullable=True),
        sa.Column('max_length_mm', sa.Float(), nullable=True),
        sa.Column('max_width_mm', sa.Float(), nullable=True),
        sa.Column('max_height_mm', sa.Float(), nullable=True),
        sa.Column('shape_ratio', sa.Float(), nullable=True),
        sa.Column('manufacturing_description', sa.Text(), nullable=True),
        sa.Column('operations_detected', sa.Text(), nullable=True),
        sa.Column('vision_extraction_json', sa.Text(), nullable=True),
        # Estimation results
        sa.Column('estimated_time_min', sa.Float(), nullable=True),
        sa.Column('estimation_reasoning', sa.Text(), nullable=True),
        sa.Column('estimation_breakdown_json', sa.Text(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('similar_parts_json', sa.Text(), nullable=True),
        # Actual time
        sa.Column('actual_time_min', sa.Float(), nullable=True),
        sa.Column('actual_entered_at', sa.DateTime(), nullable=True),
        sa.Column('actual_notes', sa.Text(), nullable=True),
        # Status
        sa.Column('status', sa.String(length=20), nullable=False),
        # Audit fields
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(length=100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['material_group_id'], ['material_groups.id'], ondelete='SET NULL'),
    )
    # Create indexes
    with op.batch_alter_table('time_vision_estimations', schema=None) as batch_op:
        batch_op.create_index('ix_time_vision_estimations_material_group_id', ['material_group_id'], unique=False)
        batch_op.create_index('ix_time_vision_estimations_status', ['status'], unique=False)
        batch_op.create_index('ix_time_vision_estimations_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index('ix_time_vision_estimations_id', ['id'], unique=False)


def downgrade() -> None:
    """Remove time_vision_estimations table."""
    op.drop_table('time_vision_estimations')
