"""multiple_drawings_per_part

Revision ID: f4a5b6c7d8e9
Revises: 33932d9d878f
Create Date: 2026-02-01 01:00:00.000000

IMPORTANT: This migration must be run manually!
DO NOT auto-run via alembic upgrade head.

Migration strategy:
1. Create drawings table
2. Migrate existing Part.drawing_path → Drawing records (is_primary=True)
3. Drop Part.drawing_path column (BREAKING CHANGE!)

Prerequisites:
- Backup database before running!
- Ensure all drawing files exist on disk
- Test migration on copy of database first

Notes:
- Existing parts with drawing_path → create Drawing record (is_primary=True)
- Existing parts without drawing_path → no action
- File paths preserved (no file moves)
- SHA-256 hash calculated from existing files
"""
from typing import Sequence, Union
from pathlib import Path
import hashlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = '33932d9d878f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file"""
    try:
        path = Path(file_path)
        if not path.exists():
            return "0" * 64  # Fallback for missing files

        sha256_hash = hashlib.sha256()
        with path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"WARNING: Failed to hash {file_path}: {e}")
        return "0" * 64  # Fallback


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        path = Path(file_path)
        if not path.exists():
            return 0
        return path.stat().st_size
    except Exception:
        return 0


def upgrade() -> None:
    """
    Upgrade schema: Part.drawing_path (1:1) → Part.drawings (1:N)

    Steps:
    1. Create drawings table
    2. Migrate existing drawing_path values
    3. Drop Part.drawing_path column
    """

    # STEP 1: Create drawings table
    op.create_table(
        'drawings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('part_id', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('revision', sa.String(length=2), nullable=False, server_default='A'),

        # AuditMixin fields
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.String(length=100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_drawings_id', 'drawings', ['id'])
    op.create_index('ix_drawings_part_id', 'drawings', ['part_id'])
    op.create_index('ix_drawings_file_hash', 'drawings', ['file_hash'], unique=True)
    op.create_index('ix_drawings_is_primary', 'drawings', ['is_primary'])
    op.create_index('ix_drawings_deleted_at', 'drawings', ['deleted_at'])  # Soft delete index

    print("✅ Created drawings table with indexes")

    # STEP 2: Migrate existing Part.drawing_path → Drawing records
    connection = op.get_bind()

    # Get all parts with drawing_path
    result = connection.execute(
        text("""
            SELECT id, drawing_path, created_at, updated_at, created_by, updated_by
            FROM parts
            WHERE drawing_path IS NOT NULL
              AND drawing_path != ''
              AND deleted_at IS NULL
        """)
    )

    parts_with_drawings = result.fetchall()
    migrated_count = 0
    skipped_count = 0

    for part in parts_with_drawings:
        part_id = part[0]
        drawing_path = part[1]
        created_at = part[2]
        updated_at = part[3]
        created_by = part[4]
        updated_by = part[5]

        # Calculate hash and size from disk
        file_hash = calculate_file_hash(drawing_path)
        file_size = get_file_size(drawing_path)

        # Extract filename from path
        filename = Path(drawing_path).name

        # Skip if file doesn't exist (hash is all zeros)
        if file_hash == "0" * 64:
            print(f"⚠️  SKIP: Part {part_id} - file not found: {drawing_path}")
            skipped_count += 1
            continue

        # Insert Drawing record (is_primary=TRUE)
        try:
            connection.execute(
                text("""
                    INSERT INTO drawings (
                        part_id, file_path, file_hash, file_size, filename,
                        is_primary, revision,
                        created_at, updated_at, created_by, updated_by, version
                    ) VALUES (
                        :part_id, :file_path, :file_hash, :file_size, :filename,
                        1, 'A',
                        :created_at, :updated_at, :created_by, :updated_by, 0
                    )
                """),
                {
                    'part_id': part_id,
                    'file_path': drawing_path,
                    'file_hash': file_hash,
                    'file_size': file_size,
                    'filename': filename,
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'created_by': created_by,
                    'updated_by': updated_by
                }
            )
            migrated_count += 1

        except Exception as e:
            print(f"⚠️  ERROR: Part {part_id} - failed to migrate: {e}")
            skipped_count += 1

    print(f"✅ Migrated {migrated_count} drawing records")
    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} parts (missing files or errors)")

    # STEP 3: Drop Part.drawing_path column
    # IMPORTANT: This is a BREAKING CHANGE!
    # Ensure all parts migrated successfully before uncommenting!

    # UNCOMMENT AFTER VERIFYING MIGRATION SUCCEEDED:
    # with op.batch_alter_table('parts', schema=None) as batch_op:
    #     batch_op.drop_column('drawing_path')
    # print("✅ Dropped Part.drawing_path column")

    print("\n" + "="*70)
    print("⚠️  MIGRATION COMPLETE (Part.drawing_path NOT YET DROPPED)")
    print("="*70)
    print("NEXT STEPS:")
    print("1. Verify all drawings migrated correctly:")
    print("   SELECT COUNT(*) FROM drawings WHERE is_primary = 1;")
    print("2. Check for parts still using drawing_path:")
    print("   SELECT COUNT(*) FROM parts WHERE drawing_path IS NOT NULL;")
    print("3. If verification passes, uncomment step 3 in migration file")
    print("4. Re-run migration to drop drawing_path column")
    print("="*70 + "\n")


def downgrade() -> None:
    """
    Downgrade schema: Part.drawings (1:N) → Part.drawing_path (1:1)

    WARNING: This will lose non-primary drawings!
    Only primary drawings will be migrated back.
    """

    # STEP 1: Add Part.drawing_path column back
    with op.batch_alter_table('parts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('drawing_path', sa.String(length=500), nullable=True))

    print("✅ Added Part.drawing_path column back")

    # STEP 2: Migrate primary drawings back to Part.drawing_path
    connection = op.get_bind()

    # Get all primary drawings
    result = connection.execute(
        text("""
            SELECT part_id, file_path
            FROM drawings
            WHERE is_primary = 1
              AND deleted_at IS NULL
        """)
    )

    primary_drawings = result.fetchall()
    migrated_count = 0

    for drawing in primary_drawings:
        part_id = drawing[0]
        file_path = drawing[1]

        connection.execute(
            text("""
                UPDATE parts
                SET drawing_path = :file_path
                WHERE id = :part_id
            """),
            {'part_id': part_id, 'file_path': file_path}
        )
        migrated_count += 1

    print(f"✅ Migrated {migrated_count} primary drawings back to Part.drawing_path")

    # STEP 3: Drop drawings table
    op.drop_index('ix_drawings_deleted_at', table_name='drawings')
    op.drop_index('ix_drawings_is_primary', table_name='drawings')
    op.drop_index('ix_drawings_file_hash', table_name='drawings')
    op.drop_index('ix_drawings_part_id', table_name='drawings')
    op.drop_index('ix_drawings_id', table_name='drawings')
    op.drop_table('drawings')

    print("✅ Dropped drawings table")
    print("\n⚠️  WARNING: Non-primary drawings were permanently deleted!")
