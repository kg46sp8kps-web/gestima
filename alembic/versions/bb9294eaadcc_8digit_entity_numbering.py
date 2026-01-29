"""8-digit entity numbering migration

Revision ID: bb9294eaadcc
Revises: 78917f98a52d
Create Date: 2026-01-28 14:00:00.000000

Migration: 7-digit → 8-digit numbering (ADR-017 v2.0)
- Parts: 1XXXXXX → 10XXXXXX (replace prefix "1" with "10")
- Materials: 2XXXXXX → 20XXXXXX (replace prefix "2" with "20")
- Batches: 3XXXXXX → 30XXXXXX (replace prefix "3" with "30")

Also fixes incorrectly migrated data:
- Parts: 11XXXXXX → 10XXXXXX (fix wrong prefix)
- Materials: 22XXXXXX → 20XXXXXX
- Batches: 33XXXXXX → 30XXXXXX

See ADR-017 for rationale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb9294eaadcc'
down_revision: Union[str, Sequence[str], None] = '78917f98a52d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate from 7-digit (PXXXXXX) to 8-digit (PPXXXXXX)

    Replaces single-digit prefix with double-digit prefix:
    - Parts: 1XXXXXX → 10XXXXXX (replace "1" with "10")
    - Materials: 2XXXXXX → 20XXXXXX (replace "2" with "20")
    - Batches: 3XXXXXX → 30XXXXXX (replace "3" with "30")

    Also fixes incorrectly migrated 8-digit data (11→10, 22→20, 33→30)
    """

    # === FIX INCORRECTLY MIGRATED DATA (8-digit with wrong prefix) ===
    # Parts: 11XXXXXX → 10XXXXXX (fix wrong prefix from previous migration)
    op.execute("""
        UPDATE parts
        SET part_number = '10' || substr(part_number, 3)
        WHERE length(part_number) = 8 AND part_number LIKE '11%'
    """)

    # Materials: 22XXXXXX → 20XXXXXX
    op.execute("""
        UPDATE material_items
        SET material_number = '20' || substr(material_number, 3)
        WHERE length(material_number) = 8 AND material_number LIKE '22%'
    """)

    # Batches: 33XXXXXX → 30XXXXXX
    op.execute("""
        UPDATE batches
        SET batch_number = '30' || substr(batch_number, 3)
        WHERE length(batch_number) = 8 AND batch_number LIKE '33%'
    """)

    # === MIGRATE 7-DIGIT DATA ===
    # Parts: 1XXXXXX → 10XXXXXX (replace prefix "1" with "10")
    op.execute("""
        UPDATE parts
        SET part_number = '10' || substr(part_number, 2)
        WHERE length(part_number) = 7 AND part_number LIKE '1%'
    """)

    # Materials: 2XXXXXX → 20XXXXXX (replace prefix "2" with "20")
    op.execute("""
        UPDATE material_items
        SET material_number = '20' || substr(material_number, 2)
        WHERE length(material_number) = 7 AND material_number LIKE '2%'
    """)

    # Batches: 3XXXXXX → 30XXXXXX (replace prefix "3" with "30")
    op.execute("""
        UPDATE batches
        SET batch_number = '30' || substr(batch_number, 2)
        WHERE length(batch_number) = 7 AND batch_number LIKE '3%'
    """)

    # Note: SQLite VARCHAR doesn't enforce length, so no column type change needed.
    # Pydantic validation enforces 8 digits on input.


def downgrade() -> None:
    """Revert to 7-digit (replace double-digit prefix with single-digit)"""

    # Parts: 10XXXXXX → 1XXXXXX (replace "10" with "1")
    op.execute("""
        UPDATE parts
        SET part_number = '1' || substr(part_number, 3)
        WHERE length(part_number) = 8 AND part_number LIKE '10%'
    """)

    # Materials: 20XXXXXX → 2XXXXXX (replace "20" with "2")
    op.execute("""
        UPDATE material_items
        SET material_number = '2' || substr(material_number, 3)
        WHERE length(material_number) = 8 AND material_number LIKE '20%'
    """)

    # Batches: 30XXXXXX → 3XXXXXX (replace "30" with "3")
    op.execute("""
        UPDATE batches
        SET batch_number = '3' || substr(batch_number, 3)
        WHERE length(batch_number) = 8 AND batch_number LIKE '30%'
    """)
