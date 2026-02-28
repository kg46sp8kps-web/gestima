"""Create workshop_job_routes and workshop_order_overviews tables

Revision ID: wk008_create_workshop_sync_tables
Revises: wk007_create_production_priorities
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk008_create_workshop_sync_tables'
down_revision: str = 'wk007_create_production_priorities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- workshop_job_routes ---
    op.create_table(
        'workshop_job_routes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('job', sa.String(30), nullable=False),
        sa.Column('suffix', sa.String(5), nullable=False, server_default='0'),
        sa.Column('oper_num', sa.String(10), nullable=False),
        sa.Column('wc', sa.String(20), nullable=True),
        sa.Column('job_stat', sa.String(5), nullable=True),
        sa.Column('der_job_item', sa.String(60), nullable=True),
        sa.Column('job_description', sa.String(200), nullable=True),
        sa.Column('job_qty_released', sa.Float(), nullable=True),
        sa.Column('qty_complete', sa.Float(), nullable=True),
        sa.Column('qty_scrapped', sa.Float(), nullable=True),
        sa.Column('jsh_setup_hrs', sa.Float(), nullable=True),
        sa.Column('der_run_mch_hrs', sa.Float(), nullable=True),
        sa.Column('op_datum_st', sa.String(30), nullable=True),
        sa.Column('op_datum_sp', sa.String(30), nullable=True),
        sa.Column('record_date', sa.String(30), nullable=True),
        # AuditMixin columns
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('job', 'suffix', 'oper_num', name='uq_wjr_job_suffix_oper'),
    )
    op.create_index('ix_wjr_wc', 'workshop_job_routes', ['wc'])
    op.create_index('ix_wjr_job_stat', 'workshop_job_routes', ['job_stat'])

    # --- workshop_order_overviews ---
    op.create_table(
        'workshop_order_overviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('co_num', sa.String(20), nullable=False),
        sa.Column('co_line', sa.String(10), nullable=False),
        sa.Column('co_release', sa.String(10), nullable=False, server_default='0'),
        sa.Column('customer_code', sa.String(20), nullable=True),
        sa.Column('customer_name', sa.String(100), nullable=True),
        sa.Column('delivery_name', sa.String(100), nullable=True),
        sa.Column('item', sa.String(60), nullable=True),
        sa.Column('description', sa.String(200), nullable=True),
        sa.Column('stat', sa.String(5), nullable=True),
        sa.Column('due_date', sa.String(30), nullable=True),
        sa.Column('promise_date', sa.String(30), nullable=True),
        sa.Column('confirm_date', sa.String(30), nullable=True),
        sa.Column('qty_ordered', sa.Float(), nullable=True),
        sa.Column('qty_shipped', sa.Float(), nullable=True),
        sa.Column('qty_wip', sa.Float(), nullable=True),
        sa.Column('job', sa.String(30), nullable=True),
        sa.Column('suffix', sa.String(5), nullable=True),
        sa.Column('job_count', sa.Integer(), nullable=True),
        sa.Column('material_ready', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('raw_data', sa.Text(), nullable=True),
        sa.Column('record_date', sa.String(30), nullable=True),
        # AuditMixin columns
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('co_num', 'co_line', 'co_release', name='uq_woo_co_line_rel'),
    )
    op.create_index('ix_woo_item', 'workshop_order_overviews', ['item'])
    op.create_index('ix_woo_due_date', 'workshop_order_overviews', ['due_date'])


def downgrade() -> None:
    op.drop_table('workshop_order_overviews')
    op.drop_table('workshop_job_routes')
