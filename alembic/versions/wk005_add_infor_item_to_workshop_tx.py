"""wk005: přidání infor_item do workshop_transactions

Ukládá DerJobItem (číslo dílu) z Infor zakázky.
Potřebné jako @TItem parametr pro IteCzTsdUpdateDcSfcMchtrxSp (stop strojové transakce).

Revision ID: wk005_add_infor_item_to_workshop_tx
Revises: fix001_mat_price_cat_ondelete
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'wk005_add_infor_item_to_workshop_tx'
down_revision: str = 'fix001_mat_price_cat_ondelete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'workshop_transactions',
        sa.Column('infor_item', sa.String(30), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('workshop_transactions', 'infor_item')
