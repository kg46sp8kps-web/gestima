"""migrate_operation_to_work_center

Revision ID: 123020d96ea3
Revises: d6a7b8c9e0f1
Create Date: 2026-01-28 20:24:58.036886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '123020d96ea3'
down_revision: Union[str, Sequence[str], None] = 'd6a7b8c9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate Operations from machine_id to work_center_id."""
    # SQLite batch mode: Add work_center_id, drop machine_id
    # Batch mode automatically handles FK reconstruction
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_center_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_operations_work_center_id',
            'work_centers',
            ['work_center_id'], ['id'],
            ondelete='SET NULL'
        )
        # Drop machine_id column (FK is automatically removed in SQLite batch mode)
        batch_op.drop_column('machine_id')


def downgrade() -> None:
    """Rollback: restore machine_id, remove work_center_id."""
    # SQLite batch mode: Add machine_id, drop work_center_id
    # Batch mode automatically handles FK reconstruction
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('machine_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'operations_machine_id_fkey',
            'machines',
            ['machine_id'], ['id'],
            ondelete='SET NULL'
        )
        # Drop work_center_id column (FK is automatically removed in SQLite batch mode)
        batch_op.drop_column('work_center_id')
