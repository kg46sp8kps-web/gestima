"""add infor_emp_num to users

Revision ID: wk001_dilna_emp
Revises: g6h7i8j9k0l1
Create Date: 2026-02-26

Gestima Dílna: Infor employee number pro dílnické terminály.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'wk001_dilna_emp'
down_revision: str = 'g6h7i8j9k0l1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('infor_emp_num', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'infor_emp_num')
