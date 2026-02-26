"""extend workshop_transactions: wc, qty_moved, oper_complete, job_complete

Revision ID: wk003_dilna_extend_tx
Revises: wk002_dilna_tx
Create Date: 2026-02-26

Gestima Dílna: Přidání polí potřebných pro IteCzTsdUpdateDcSfc34Sp.
  - wc:            pracoviště (@TWc)
  - qty_moved:     přesunuté kusy (@TcQtuQtyMove)
  - oper_complete: operace dokončena (@TComplete)
  - job_complete:  VP dokončeno (@TClose)
"""

from alembic import op
import sqlalchemy as sa

revision: str = 'wk003_dilna_extend_tx'
down_revision: str = 'wk002_dilna_tx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workshop_transactions', sa.Column('wc', sa.String(20), nullable=True))
    op.add_column('workshop_transactions', sa.Column('qty_moved', sa.Float(), nullable=True))
    op.add_column('workshop_transactions', sa.Column('oper_complete', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('workshop_transactions', sa.Column('job_complete', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('workshop_transactions', 'job_complete')
    op.drop_column('workshop_transactions', 'oper_complete')
    op.drop_column('workshop_transactions', 'qty_moved')
    op.drop_column('workshop_transactions', 'wc')
