"""Remove length and notes columns from parts table

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-23

Removes deprecated fields that are no longer shown in the UI.
"""
from alembic import op

# revision identifiers
revision = 'b3c4d5e6f7g8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('parts') as batch_op:
        batch_op.drop_column('length')
        batch_op.drop_column('notes')


def downgrade() -> None:
    import sqlalchemy as sa
    with op.batch_alter_table('parts') as batch_op:
        batch_op.add_column(sa.Column('notes', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('length', sa.Float(), nullable=True, server_default='0.0'))
