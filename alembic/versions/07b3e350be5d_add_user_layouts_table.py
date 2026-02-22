"""add user_layouts table

Revision ID: 07b3e350be5d
Revises: sync001
Create Date: 2026-02-22 21:02:51.526628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07b3e350be5d'
down_revision: Union[str, Sequence[str], None] = 'sync001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_layouts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('tree_json', sa.JSON(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('show_in_header', sa.Boolean(), nullable=False, server_default='1'),
        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_layouts')
