"""add_vision_metadata_columns

Revision ID: 218fabd7a6d0
Revises: d7d51bd210e1
Create Date: 2026-02-09 13:09:00.513834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '218fabd7a6d0'
down_revision: Union[str, Sequence[str], None] = 'd7d51bd210e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Vision metadata columns to turning_estimations and milling_estimations tables."""
    # Add columns to turning_estimations
    with op.batch_alter_table('turning_estimations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_source', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('needs_manual_review', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('decision_log', sa.Text(), nullable=True))

    # Add columns to milling_estimations
    with op.batch_alter_table('milling_estimations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_source', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('needs_manual_review', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('decision_log', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove Vision metadata columns."""
    with op.batch_alter_table('milling_estimations', schema=None) as batch_op:
        batch_op.drop_column('decision_log')
        batch_op.drop_column('needs_manual_review')
        batch_op.drop_column('confidence')
        batch_op.drop_column('data_source')

    with op.batch_alter_table('turning_estimations', schema=None) as batch_op:
        batch_op.drop_column('decision_log')
        batch_op.drop_column('needs_manual_review')
        batch_op.drop_column('confidence')
        batch_op.drop_column('data_source')
