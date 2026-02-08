"""Update MaterialGroup codes to 8-digit format (ADR-017 compliance)

Revision ID: p9q0r1s2t3u4
Revises: b9c0d1e2f3g4
Create Date: 2026-02-03 17:05:00

Changes MaterialGroup.code from textual codes (HLINIK, OCEL-AUTO) to 8-digit codes (20910000-20910008)
according to ADR-017 hierarchical sub-ranges (20910000-20919999 for MaterialGroups).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p9q0r1s2t3u4'
down_revision = 'b9c0d1e2f3g4'
branch_labels = None
depends_on = None


def upgrade():
    """Update MaterialGroup codes to 8-digit format"""

    # Map old textual codes to new 8-digit codes
    # Ordered by ID (1-9)
    code_mapping = [
        ('HLINIK', '20910000'),      # ID 1
        ('MED', '20910001'),          # ID 2
        ('MOSAZ', '20910002'),        # ID 3
        ('OCEL-AUTO', '20910003'),    # ID 4
        ('OCEL-KONS', '20910004'),    # ID 5
        ('OCEL-LEG', '20910005'),     # ID 6
        ('OCEL-NAST', '20910006'),    # ID 7
        ('NEREZ', '20910007'),        # ID 8
        ('PLAST', '20910008'),        # ID 9
    ]

    # Update each code
    for old_code, new_code in code_mapping:
        op.execute(
            f"UPDATE material_groups SET code = '{new_code}' WHERE code = '{old_code}'"
        )


def downgrade():
    """Revert to textual codes"""

    # Map 8-digit codes back to textual codes
    code_mapping = [
        ('20910000', 'HLINIK'),
        ('20910001', 'MED'),
        ('20910002', 'MOSAZ'),
        ('20910003', 'OCEL-AUTO'),
        ('20910004', 'OCEL-KONS'),
        ('20910005', 'OCEL-LEG'),
        ('20910006', 'OCEL-NAST'),
        ('20910007', 'NEREZ'),
        ('20910008', 'PLAST'),
    ]

    # Update each code
    for old_code, new_code in code_mapping:
        op.execute(
            f"UPDATE material_groups SET code = '{new_code}' WHERE code = '{old_code}'"
        )
