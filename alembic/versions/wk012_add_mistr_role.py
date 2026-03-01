"""Add mistr user with PIN 4321

Revision ID: wk012_add_mistr_role
Revises: wk011_add_pin_hash_to_users
Create Date: 2026-03-01

SQLite stores enums as strings — no ALTER TYPE needed.
Seeds a 'mistr' user with role='mistr', PIN hash from '4321'.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers
revision: str = 'wk012_add_mistr_role'
down_revision: str = 'wk011_add_pin_hash_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.services.auth_service import get_pin_hash, get_password_hash

    conn = op.get_bind()

    # Check if 'mistr' user already exists
    result = conn.execute(sa.text("SELECT id FROM users WHERE username = 'mistr'"))
    if result.fetchone() is None:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            sa.text(
                "INSERT INTO users (username, hashed_password, role, is_active, pin_hash, created_at, updated_at, created_by, version) "
                "VALUES (:username, :hashed_password, :role, :is_active, :pin_hash, :created_at, :updated_at, :created_by, :version)"
            ),
            {
                "username": "mistr",
                "hashed_password": get_password_hash("mistr-gestima"),
                "role": "MISTR",
                "is_active": True,
                "pin_hash": get_pin_hash("4321"),
                "created_at": now,
                "updated_at": now,
                "created_by": "migration",
                "version": 1,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE username = 'mistr' AND created_by = 'migration'"))
