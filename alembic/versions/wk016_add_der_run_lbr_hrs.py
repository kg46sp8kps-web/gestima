"""Add der_run_lbr_hrs to workshop_job_routes

Revision ID: wk016_add_der_run_lbr_hrs
Revises: wk015_infor_job_transactions
Create Date: 2026-03-03

Adds:
  - der_run_lbr_hrs column (Float) to workshop_job_routes for manning calculation
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk016_add_der_run_lbr_hrs'
down_revision: str = 'wk015_infor_job_transactions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workshop_job_routes', sa.Column('der_run_lbr_hrs', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('workshop_job_routes', 'der_run_lbr_hrs')
