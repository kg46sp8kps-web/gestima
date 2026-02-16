"""add_ai_estimation_id_to_operations

Revision ID: cf31cd62fcfc
Revises: c8d9e0f1a2b3
Create Date: 2026-02-14 00:22:34.904457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf31cd62fcfc'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ai_estimation_id FK to operations table."""
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_estimation_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_operations_ai_estimation_id',
            'time_vision_estimations',
            ['ai_estimation_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    """Remove ai_estimation_id from operations table."""
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_operations_ai_estimation_id', type_='foreignkey')
        batch_op.drop_column('ai_estimation_id')
