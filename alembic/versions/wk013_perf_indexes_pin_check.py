"""Performance indexes + pin_check column

Revision ID: wk013_perf_indexes_pin_check
Revises: wk012_add_mistr_role
Create Date: 2026-03-01

Adds:
  - users.pin_check (SHA256 for fast PIN lookup)
  - Compound indexes on workshop_transactions for operator queries
  - Compound index on workshop_job_routes for WC queue filtering
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk013_perf_indexes_pin_check'
down_revision: str = 'wk012_add_mistr_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. pin_check column (SHA256 of PIN for fast lookup)
    op.add_column('users', sa.Column('pin_check', sa.String(64), nullable=True))

    # 2. Indexes on workshop_transactions for operator queries
    op.create_index(
        'ix_wtx_created_by_status',
        'workshop_transactions',
        ['created_by', 'status', 'deleted_at'],
    )
    op.create_index(
        'ix_wtx_created_by_type_date',
        'workshop_transactions',
        ['created_by', 'trans_type', 'created_at'],
    )

    # 3. Compound index on workshop_job_routes for WC + stat filtering
    op.create_index(
        'ix_wjr_wc_stat_deleted',
        'workshop_job_routes',
        ['wc', 'job_stat', 'deleted_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_wjr_wc_stat_deleted', table_name='workshop_job_routes')
    op.drop_index('ix_wtx_created_by_type_date', table_name='workshop_transactions')
    op.drop_index('ix_wtx_created_by_status', table_name='workshop_transactions')
    op.drop_column('users', 'pin_check')
