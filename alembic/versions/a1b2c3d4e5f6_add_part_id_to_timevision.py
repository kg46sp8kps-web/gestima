"""Add part_id index + backfill on time_vision_estimations

Revision ID: a1b2c3d4e5f6
Revises: z9a0b1c2d3e4
Create Date: 2026-02-16

Part_id column already exists (added manually).
This migration adds composite index + backfills existing estimations via Drawing filename matching.
ADR-045: Direct Part ↔ TimeVisionEstimation relationship.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "z9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add composite index if not exists (column + index may already exist from manual setup)
    conn = op.get_bind()
    existing_indexes = conn.execute(sa.text("PRAGMA index_list('time_vision_estimations')")).fetchall()
    index_names = [row[1] for row in existing_indexes]
    if "ix_tve_part_estimation" not in index_names:
        op.create_index("ix_tve_part_estimation", "time_vision_estimations", ["part_id", "estimation_type"])

    # 2. Backfill: match existing estimations to Parts via Drawing filenames
    conn = op.get_bind()
    estimations = conn.execute(
        sa.text("""
            SELECT tve.id, tve.pdf_filename
            FROM time_vision_estimations tve
            WHERE tve.part_id IS NULL
              AND tve.deleted_at IS NULL
        """)
    ).fetchall()

    updated = 0
    for est_id, pdf_filename in estimations:
        result = conn.execute(
            sa.text("""
                SELECT d.part_id
                FROM drawings d
                WHERE (d.file_path LIKE :pattern OR d.filename = :filename)
                  AND d.deleted_at IS NULL
                  AND d.part_id IS NOT NULL
                ORDER BY d.is_primary DESC, d.created_at DESC
                LIMIT 1
            """),
            {"pattern": f"%{pdf_filename}", "filename": pdf_filename},
        )
        row = result.fetchone()
        if row:
            conn.execute(
                sa.text("UPDATE time_vision_estimations SET part_id = :part_id WHERE id = :id"),
                {"part_id": row[0], "id": est_id},
            )
            updated += 1

    if updated:
        print(f"  Backfilled {updated} estimations with part_id")


def downgrade() -> None:
    op.drop_index("ix_tve_part_estimation", table_name="time_vision_estimations")
