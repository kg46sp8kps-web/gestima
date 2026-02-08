"""Add file_type to drawings table

Revision ID: s2t3u4v5w6x7
Revises: q0r1s2t3u4v5
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 's2t3u4v5w6x7'
down_revision = 'q0r1s2t3u4v5'
branch_labels = None
depends_on = None


def upgrade():
    """Add file_type column to drawings table with default 'pdf'"""
    op.add_column('drawings', sa.Column('file_type', sa.String(10), nullable=False, server_default='pdf'))


def downgrade():
    """Remove file_type column from drawings table"""
    op.drop_column('drawings', 'file_type')
