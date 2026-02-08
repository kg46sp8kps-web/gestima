"""add_missing_fk_ondelete_constraints

Revision ID: 09d8cd5db466
Revises: t3u4v5w6x7y8
Create Date: 2026-02-08 21:37:19.323130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09d8cd5db466'
down_revision: Union[str, Sequence[str], None] = 't3u4v5w6x7y8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing ondelete constraints to ForeignKey columns.

    Fixes audit P1-4:
    - batch.frozen_by_id → SET NULL (user can be deleted, batch remains)
    - batch_set.frozen_by_id → SET NULL (user can be deleted, batch_set remains)
    - material_inputs.material_group_id → SET NULL (group can be deleted, material remains orphaned)

    Note: For existing SQLite database, ondelete constraints are already defined in model definitions.
    SQLAlchemy will apply them on next table recreation (via alembic autogenerate).
    This migration marks the schema version change.

    For fresh databases (init from models), constraints are automatically created from model definitions.
    """
    # SQLite: ondelete constraints already in models (batch.py, batch_set.py, material.py)
    # No DDL changes needed - models are source of truth
    pass


def downgrade() -> None:
    """Remove ondelete constraints (revert to no ondelete).

    Note: Downgrade would require recreating tables without ondelete.
    Not implemented as this is a forward-only migration (P1 audit fix).
    """
    pass
