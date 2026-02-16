"""Add production_records table

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-02-16

Production records store actual manufacturing data from Infor ERP:
- Production order number, batch quantity
- Operation sequence + work center
- Planned vs actual times
- Production date and source (infor/manual)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'z9a0b1c2d3e4'
down_revision = 'y8z9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'production_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('infor_order_number', sa.String(50), nullable=True, index=True),
        sa.Column('batch_quantity', sa.Integer(), nullable=True),
        sa.Column('operation_seq', sa.Integer(), nullable=True),
        sa.Column('work_center_id', sa.Integer(), sa.ForeignKey('work_centers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('planned_time_min', sa.Float(), nullable=True),
        sa.Column('actual_time_min', sa.Float(), nullable=True),
        sa.Column('production_date', sa.Date(), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('notes', sa.String(500), nullable=True),
        # AuditMixin columns
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('production_records')
