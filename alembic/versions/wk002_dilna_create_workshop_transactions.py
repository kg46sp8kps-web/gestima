"""create workshop_transactions table

Revision ID: wk002_dilna_tx
Revises: wk001_dilna_emp
Create Date: 2026-02-26

Gestima Dílna: Lokální buffer dílnických transakcí před odesláním do Inforu.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk002_dilna_tx'
down_revision: str = 'wk001_dilna_emp'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workshop_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Infor identifikace zakázky
        sa.Column('infor_job', sa.String(30), nullable=False),
        sa.Column('infor_suffix', sa.String(5), nullable=True),
        sa.Column('oper_num', sa.String(10), nullable=False),

        # Typ transakce
        sa.Column(
            'trans_type',
            sa.Enum('qty_complete', 'scrap', 'time', 'start', 'stop', name='workshoptranstype'),
            nullable=False
        ),

        # Hodnoty transakce
        sa.Column('qty_completed', sa.Float(), nullable=True),
        sa.Column('qty_scrapped', sa.Float(), nullable=True),
        sa.Column('scrap_reason', sa.String(50), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),

        # Časovač
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),

        # Status vůči Inforu
        sa.Column(
            'status',
            sa.Enum('pending', 'posting', 'posted', 'failed', name='workshoptxstatus'),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('error_msg', sa.String(500), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),

        # AuditMixin
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )

    # Indexy pro časté dotazy
    op.create_index('ix_workshop_transactions_infor_job', 'workshop_transactions', ['infor_job'])
    op.create_index('ix_workshop_transactions_status', 'workshop_transactions', ['status'])
    op.create_index('ix_workshop_transactions_deleted_at', 'workshop_transactions', ['deleted_at'])


def downgrade() -> None:
    op.drop_index('ix_workshop_transactions_deleted_at', table_name='workshop_transactions')
    op.drop_index('ix_workshop_transactions_status', table_name='workshop_transactions')
    op.drop_index('ix_workshop_transactions_infor_job', table_name='workshop_transactions')
    op.drop_table('workshop_transactions')
