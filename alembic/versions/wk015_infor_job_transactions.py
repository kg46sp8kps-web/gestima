"""Infor job transactions table (SLJobTrans mirror)

Revision ID: wk015_infor_job_transactions
Revises: wk014_job_materials_cache
Create Date: 2026-03-02

Adds:
  - infor_job_transactions table (mirror of Infor SLJobTrans)
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk015_infor_job_transactions'
down_revision: str = 'wk014_job_materials_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'infor_job_transactions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('trans_num', sa.String(30), nullable=False, unique=True),
        sa.Column('trans_type', sa.String(10), nullable=True),
        sa.Column('trans_date', sa.String(30), nullable=True),
        sa.Column('emp_num', sa.String(20), nullable=True),
        sa.Column('job', sa.String(30), nullable=False),
        sa.Column('suffix', sa.String(5), nullable=False, server_default='0'),
        sa.Column('oper_num', sa.String(10), nullable=True),
        sa.Column('wc', sa.String(20), nullable=True),
        sa.Column('run_hrs_t', sa.Float, nullable=True),
        sa.Column('setup_hrs_t', sa.Float, nullable=True),
        sa.Column('qty_complete', sa.Float, nullable=True),
        sa.Column('qty_scrapped', sa.Float, nullable=True),
        sa.Column('record_date', sa.String(30), nullable=True),
        sa.Column('synced_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_ijt_emp_trans_date', 'infor_job_transactions', ['emp_num', 'trans_date'])
    op.create_index('ix_ijt_job_suffix_oper', 'infor_job_transactions', ['job', 'suffix', 'oper_num'])


def downgrade() -> None:
    op.drop_index('ix_ijt_job_suffix_oper')
    op.drop_index('ix_ijt_emp_trans_date')
    op.drop_table('infor_job_transactions')
