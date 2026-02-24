"""add height to material_items (plate přířez support)

Revision ID: a2b3c4d5e6f7
Revises: 07b3e350be5d
Create Date: 2026-02-23

Přidává sloupec height do material_items pro podporu přířezu z plechu
(3 fixní rozměry: width × height × thickness).

Bez tohoto sloupce lze definovat pouze pás (width + thickness),
kde uživatel zadává délku ručně.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '07b3e350be5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add height column to material_items (for plate přířez with 3 fixed dimensions)."""
    with op.batch_alter_table('material_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('height', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove height column from material_items."""
    with op.batch_alter_table('material_items', schema=None) as batch_op:
        batch_op.drop_column('height')
