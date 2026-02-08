"""Add surface_treatment to material_items

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'o8p9q0r1s2t3'
down_revision = 'n7o8p9q0r1s2'
branch_labels = None
depends_on = None


def upgrade():
    """Add surface_treatment field to material_items table"""
    # Add nullable surface_treatment column
    op.add_column('material_items',
        sa.Column('surface_treatment', sa.String(20), nullable=True)
    )


def downgrade():
    """Remove surface_treatment field from material_items table"""
    op.drop_column('material_items', 'surface_treatment')
