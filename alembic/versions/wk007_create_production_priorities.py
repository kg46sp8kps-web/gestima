"""wk007: create production_priorities table

Lokalni priorita a hot flag pro VP v Production Planner.
DB uklada POUZE prioritu + hot flag. Data vzdy z Inforu.

Revision ID: wk007_create_production_priorities
Revises: wk006_create_machine_plan_entries
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk007_create_production_priorities'
down_revision: str = 'wk006_create_machine_plan_entries'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'production_priorities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('infor_job', sa.String(30), nullable=False),
        sa.Column('infor_suffix', sa.String(5), nullable=False, server_default='0'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_hot', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        # AuditMixin columns
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint(
            'infor_job', 'infor_suffix',
            name='uq_production_priority_job_suffix',
        ),
    )


def downgrade() -> None:
    op.drop_table('production_priorities')
