"""add setup_start, setup_end to WorkshopTransType enum

Revision ID: wk004_dilna_setup_trans_types
Revises: wk003_dilna_extend_tx
Create Date: 2026-02-26

Přidání typů transakcí pro seřízení:
  setup_start → TransType='1' (ZahajitNastaveni)
  setup_end   → TransType='2' (UkoncitNastaveni)

SQLite neumí ALTER COLUMN přímo — Alembic batch mode
přetvoří tabulku s novou CHECK constraint.
"""

from alembic import op
import sqlalchemy as sa

revision: str = 'wk004_dilna_setup_trans_types'
down_revision: str = 'wk003_dilna_extend_tx'
branch_labels = None
depends_on = None

# Původní enum hodnoty
_OLD_ENUM = ('qty_complete', 'scrap', 'time', 'start', 'stop')

# Nové enum hodnoty (přidány setup_start, setup_end)
_NEW_ENUM = ('qty_complete', 'scrap', 'time', 'start', 'stop', 'setup_start', 'setup_end')


def upgrade() -> None:
    # SQLite: batch_alter_table recreates table s novou CHECK constraint
    with op.batch_alter_table('workshop_transactions') as batch_op:
        batch_op.alter_column(
            'trans_type',
            existing_type=sa.Enum(*_OLD_ENUM, name='workshoptranstype'),
            type_=sa.Enum(*_NEW_ENUM, name='workshoptranstype'),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('workshop_transactions') as batch_op:
        batch_op.alter_column(
            'trans_type',
            existing_type=sa.Enum(*_NEW_ENUM, name='workshoptranstype'),
            type_=sa.Enum(*_OLD_ENUM, name='workshoptranstype'),
            nullable=False,
        )
