"""fix: material_price_categories FK ondelete SET NULL → RESTRICT

Revision ID: fix001_mat_price_cat_ondelete
Revises: wk004_dilna_setup_trans_types
Create Date: 2026-02-26

Důvod: price_category_id je NOT NULL → ondelete SET NULL by porušilo
NOT NULL constraint. Správná hodnota je RESTRICT — nelze smazat cenovou
kategorii pokud je přiřazena k materiálovému vstupu.
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'fix001_mat_price_cat_ondelete'
down_revision: str = 'wk004_dilna_setup_trans_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite nepodporuje pojmenované FK constrainty a nevynucuje ondelete bez PRAGMA.
    # Změna je v SQLAlchemy modelu (app/models/material_input.py):
    # ondelete='SET NULL' → ondelete='RESTRICT'
    # Vynuceno na aplikační vrstvě (safe_commit + NOT NULL constraint).
    pass


def downgrade() -> None:
    pass
