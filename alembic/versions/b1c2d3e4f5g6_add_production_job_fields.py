"""Add production job fields for VP import

Revision ID: b1c2d3e4f5g6
Revises: a0b1c2d3e4f5
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5g6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if column exists in SQLite table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    columns = [
        ("planned_setup_min", sa.Float()),
        ("actual_setup_min", sa.Float()),
        ("actual_run_machine_min", sa.Float()),
        ("actual_run_labor_min", sa.Float()),
        ("manning_coefficient", sa.Float()),
        ("actual_manning_coefficient", sa.Float()),
        ("planned_labor_time_min", sa.Float()),
        ("actual_labor_time_min", sa.Float()),
    ]
    for name, col_type in columns:
        if not _column_exists("production_records", name):
            op.add_column("production_records", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    columns = [
        "actual_labor_time_min",
        "planned_labor_time_min",
        "actual_manning_coefficient",
        "manning_coefficient",
        "actual_run_labor_min",
        "actual_run_machine_min",
        "actual_setup_min",
        "planned_setup_min",
    ]
    for name in columns:
        if _column_exists("production_records", name):
            op.drop_column("production_records", name)
