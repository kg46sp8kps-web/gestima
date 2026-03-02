"""Job materials cache table

Revision ID: wk014_job_materials_cache
Revises: wk013_perf_indexes_pin_check
Create Date: 2026-03-02

Adds:
  - workshop_job_material_cache table (lazy cache for Infor materials)
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk014_job_materials_cache'
down_revision: str = 'wk013_perf_indexes_pin_check'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workshop_job_material_cache',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('job', sa.String(30), nullable=False, index=True),
        sa.Column('suffix', sa.String(5), nullable=False, server_default='0'),
        sa.Column('oper_num', sa.String(10), nullable=False),
        sa.Column('data_json', sa.Text, nullable=False),
        sa.Column('synced_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('job', 'suffix', 'oper_num', name='uq_wjmc_job_suffix_oper'),
    )


def downgrade() -> None:
    op.drop_table('workshop_job_material_cache')
