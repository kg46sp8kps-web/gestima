"""add uom fields to material_items and parts (ADR-050)

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5f6, b3c4d5e6f7g8
Create Date: 2026-02-24

Changes:
- material_items: ADD uom VARCHAR(4) NOT NULL DEFAULT 'kg'
- material_items: ADD conv_uom VARCHAR(4) NULL
- material_items: ADD conv_factor FLOAT NULL
- parts: ADD uom VARCHAR(4) NOT NULL DEFAULT 'ks'
- parts: ADD unit_weight FLOAT NULL

Data migration:
- Profily s weight_per_meter → conv_uom='m', conv_factor=weight_per_meter
- Odlitky/výkovky → uom='ks'
- Parts → uom='ks'
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision = ('a1b2c3d4e5f6', 'b3c4d5e6f7g8')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === material_items ===
    op.add_column('material_items', sa.Column('uom', sa.String(4), nullable=False, server_default='kg'))
    op.add_column('material_items', sa.Column('conv_uom', sa.String(4), nullable=True))
    op.add_column('material_items', sa.Column('conv_factor', sa.Float(), nullable=True))

    # === parts ===
    op.add_column('parts', sa.Column('uom', sa.String(4), nullable=False, server_default='ks'))
    op.add_column('parts', sa.Column('unit_weight', sa.Float(), nullable=True))

    # === Data migration ===

    # 1. Profily s weight_per_meter → konverzní pár (conv_uom='m', conv_factor=weight_per_meter)
    op.execute("""
        UPDATE material_items
        SET conv_uom = 'm', conv_factor = weight_per_meter
        WHERE weight_per_meter IS NOT NULL
        AND shape IN ('round_bar', 'square_bar', 'flat_bar', 'hexagonal_bar', 'tube')
    """)

    # 2. Odlitky a výkovky → uom='ks' (základní jednotka = kus)
    op.execute("""
        UPDATE material_items
        SET uom = 'ks'
        WHERE shape IN ('casting', 'forging')
    """)

    # 3. Parts → vždy ks (pokryto DEFAULT, ale explicitně pro jistotu)
    op.execute("UPDATE parts SET uom = 'ks'")


def downgrade() -> None:
    op.drop_column('parts', 'unit_weight')
    op.drop_column('parts', 'uom')
    op.drop_column('material_items', 'conv_factor')
    op.drop_column('material_items', 'conv_uom')
    op.drop_column('material_items', 'uom')
