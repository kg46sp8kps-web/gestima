"""wk006: create machine_plan_entries table

Lokalni poradnik pro mistrovske planovani operaci na pracovisti.
DB uklada POUZE poradi (position). Cerstva data se vzdy ctou z Inforu.

Revision ID: wk006_create_machine_plan_entries
Revises: wk005_add_infor_item_to_workshop_tx
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk006_create_machine_plan_entries'
down_revision: str = 'wk005_add_infor_item_to_workshop_tx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'machine_plan_entries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('wc', sa.String(20), nullable=False, index=True),
        sa.Column('infor_job', sa.String(30), nullable=False),
        sa.Column('infor_suffix', sa.String(5), nullable=False, server_default='0'),
        sa.Column('oper_num', sa.String(10), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        # AuditMixin columns
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint(
            'wc', 'infor_job', 'infor_suffix', 'oper_num',
            name='uq_machine_plan_wc_job_suffix_oper',
        ),
    )


def downgrade() -> None:
    op.drop_table('machine_plan_entries')
