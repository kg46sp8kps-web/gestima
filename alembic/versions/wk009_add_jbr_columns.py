"""Add JBR columns to workshop_job_routes

Revision ID: wk009_add_jbr_columns
Revises: wk008_create_workshop_sync_tables
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk009_add_jbr_columns'
down_revision: str = 'wk008_create_workshop_sync_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workshop_job_routes', sa.Column('jbr_state', sa.String(50), nullable=True))
    op.add_column('workshop_job_routes', sa.Column('jbr_state_asd', sa.String(50), nullable=True))
    op.add_column('workshop_job_routes', sa.Column('jbr_lze_dokoncit', sa.String(10), nullable=True))
    op.add_column('workshop_job_routes', sa.Column('jbr_plan_flag', sa.String(10), nullable=True))
    op.add_column('workshop_job_routes', sa.Column('jbr_synced_at', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('workshop_job_routes', 'jbr_synced_at')
    op.drop_column('workshop_job_routes', 'jbr_plan_flag')
    op.drop_column('workshop_job_routes', 'jbr_lze_dokoncit')
    op.drop_column('workshop_job_routes', 'jbr_state_asd')
    op.drop_column('workshop_job_routes', 'jbr_state')
