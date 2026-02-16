#!/usr/bin/env python3
"""GESTIMA - Migrate TimeVision PDF files to FileRecord system

Scans uploads/drawings/ directory and creates FileRecord entries for all PDF files.
Links existing TimeVisionEstimation records to their corresponding FileRecords via file_id FK.
Creates FileLink entries for the timevision→drawing relationship.

Features:
- UPSERT pattern for idempotent execution (safe to run multiple times)
- SHA-256 file hashing for integrity verification
- Handles loose files (PDFs without estimations)
- Handles missing files (estimations referencing deleted PDFs)
- Progress reporting to stdout

Usage:
    python scripts/migrate_timevision_files.py

Version: 1.0.0 (2026-02-15)
Implements: ADR-044 File Manager Phase 2
"""

import asyncio
import hashlib
import sys
from pathlib import Path
from typing import Optional, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.file_record import FileRecord, FileLink
from app.models.time_vision import TimeVisionEstimation


UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
DRAWINGS_DIR = UPLOADS_DIR / "drawings"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents.

    Args:
        file_path: Path to file

    Returns:
        SHA-256 hex digest (64 chars)
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in 64KB chunks to handle large files efficiently
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


async def get_or_create_file_record(
    db: AsyncSession,
    pdf_path: Path,
    created_by: str = "migration_script"
) -> Optional[FileRecord]:
    """Get existing or create new FileRecord for a PDF file.

    UPSERT logic: Check by file_path, update if exists, create if not.

    Args:
        db: Database session
        pdf_path: Absolute path to PDF file
        created_by: Audit field value

    Returns:
        FileRecord instance, or None if file doesn't exist on disk
    """
    if not pdf_path.exists():
        print(f"⚠️  File not found: {pdf_path.name}")
        return None

    # Relative path from uploads/ directory (e.g. "drawings/filename.pdf")
    relative_path = str(pdf_path.relative_to(UPLOADS_DIR))

    # Check if FileRecord already exists
    stmt = select(FileRecord).where(FileRecord.file_path == relative_path)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Update metadata (file might have changed)
        existing.file_hash = compute_file_hash(pdf_path)
        existing.file_size = pdf_path.stat().st_size
        existing.original_filename = pdf_path.name
        existing.updated_by = created_by
        return existing

    # Create new FileRecord
    file_record = FileRecord(
        file_hash=compute_file_hash(pdf_path),
        file_path=relative_path,
        original_filename=pdf_path.name,
        file_size=pdf_path.stat().st_size,
        file_type="pdf",
        mime_type="application/pdf",
        status="active",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(file_record)
    return file_record


async def get_or_create_file_link(
    db: AsyncSession,
    file_record: FileRecord,
    estimation_id: int,
    created_by: str = "migration_script"
) -> FileLink:
    """Get existing or create new FileLink for timevision→file relationship.

    UPSERT logic: UniqueConstraint on (file_id, entity_type, entity_id) prevents duplicates.

    Args:
        db: Database session
        file_record: FileRecord instance
        estimation_id: TimeVisionEstimation.id
        created_by: Audit field value

    Returns:
        FileLink instance
    """
    # Check if link already exists
    stmt = select(FileLink).where(
        FileLink.file_id == file_record.id,
        FileLink.entity_type == "timevision",
        FileLink.entity_id == estimation_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Create new link
    file_link = FileLink(
        file_id=file_record.id,
        entity_type="timevision",
        entity_id=estimation_id,
        link_type="drawing",
        is_primary=True,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(file_link)
    return file_link


async def migrate_timevision_files():
    """Main migration function.

    1. Scan drawings/ directory for all PDF files
    2. Create FileRecord entries (UPSERT by file_path)
    3. Link TimeVisionEstimation records to FileRecords via file_id FK
    4. Create FileLink entries for timevision→drawing relationship

    Transaction handling (L-008):
    - All operations in single transaction
    - Rollback on any error
    - Commit only if all steps succeed
    """
    print("🚀 Migrating TimeVision PDF files to FileRecord system\n")

    async with async_session() as db:
        try:
            # === STEP 1: Register all PDF files ===
            print("📂 Step 1/4: Scanning drawings/ directory...")
            pdf_files = list(DRAWINGS_DIR.glob("*.pdf"))
            print(f"   Found {len(pdf_files)} PDF files\n")

            # Build filename→FileRecord mapping
            file_records: Dict[str, FileRecord] = {}

            for pdf_path in pdf_files:
                file_record = await get_or_create_file_record(db, pdf_path)
                if file_record:
                    file_records[pdf_path.name] = file_record

            # Flush to DB to get IDs (needed for FK relationships)
            await db.flush()
            print(f"✅ Step 1 complete: {len(file_records)} FileRecords created/updated\n")

            # === STEP 2: Link estimations to files ===
            print("🔗 Step 2/4: Linking TimeVisionEstimations to FileRecords...")

            # Get all estimations with pdf_filename
            stmt = select(TimeVisionEstimation).where(
                TimeVisionEstimation.pdf_filename.isnot(None)
            )
            result = await db.execute(stmt)
            estimations = result.scalars().all()

            print(f"   Found {len(estimations)} TimeVisionEstimations\n")

            linked_count = 0
            missing_file_count = 0
            already_linked_count = 0

            for estimation in estimations:
                # Find matching FileRecord
                file_record = file_records.get(estimation.pdf_filename)

                if not file_record:
                    # PDF file not found on disk
                    print(f"⚠️  No file found for estimation #{estimation.id}: {estimation.pdf_filename}")
                    missing_file_count += 1
                    continue

                # Check if already linked
                if estimation.file_id == file_record.id:
                    already_linked_count += 1
                    continue

                # Set file_id FK
                estimation.file_id = file_record.id
                linked_count += 1

            await db.flush()
            print(f"✅ Step 2 complete:")
            print(f"   ✓ Linked: {linked_count}")
            print(f"   ⏭️  Already linked: {already_linked_count}")
            print(f"   ⚠️  Missing file: {missing_file_count}\n")

            # === STEP 3: Create FileLink entries (ONLY newest per estimation_type) ===
            print("📎 Step 3/5: Creating FileLink entries (newest per type only)...")

            # Find newest estimation per (pdf_filename, estimation_type)
            from sqlalchemy import func
            newest_subq = (
                select(
                    func.max(TimeVisionEstimation.id).label("newest_id"),
                )
                .where(TimeVisionEstimation.deleted_at.is_(None))
                .group_by(
                    TimeVisionEstimation.pdf_filename,
                    TimeVisionEstimation.estimation_type,
                )
            )
            newest_result = await db.execute(newest_subq)
            newest_ids = {row[0] for row in newest_result.all()}

            filelink_created = 0
            filelink_existing = 0

            for estimation in estimations:
                if not estimation.file_id:
                    continue  # Skip estimations without valid file_id
                if estimation.id not in newest_ids:
                    continue  # Skip old estimations (only link newest per type)

                # Find FileRecord
                file_record = next(
                    (fr for fr in file_records.values() if fr.id == estimation.file_id),
                    None
                )

                if not file_record:
                    continue

                file_link = await get_or_create_file_link(db, file_record, estimation.id)

                # Check if newly created or existing
                if file_link.id:
                    filelink_existing += 1
                else:
                    filelink_created += 1

            await db.flush()
            print(f"✅ Step 3 complete:")
            print(f"   ✓ Created: {filelink_created}")
            print(f"   ⏭️  Already exists: {filelink_existing}\n")

            # === STEP 4: Cleanup old FileLinks ===
            print("🧹 Step 4/5: Cleaning up old FileLinks...")

            from datetime import datetime
            cleanup_stmt = select(FileLink).where(
                FileLink.entity_type == "timevision",
                FileLink.deleted_at.is_(None),
                FileLink.entity_id.notin_(newest_ids),
            )
            cleanup_result = await db.execute(cleanup_stmt)
            old_links = cleanup_result.scalars().all()

            for old_link in old_links:
                old_link.deleted_at = datetime.utcnow()
                old_link.deleted_by = "migration_cleanup"

            await db.flush()
            print(f"✅ Step 4 complete: {len(old_links)} old links soft-deleted\n")

            # === STEP 5: Commit transaction ===
            print("💾 Step 5/5: Committing transaction...")
            await db.commit()
            print("✅ Transaction committed\n")

            # === SUMMARY ===
            print("=" * 60)
            print("📊 MIGRATION SUMMARY")
            print("=" * 60)
            print(f"FileRecords:          {len(file_records)} created/updated")
            print(f"Estimations linked:   {linked_count} new, {already_linked_count} existing")
            print(f"FileLinks created:    {filelink_created} new, {filelink_existing} existing")
            print(f"Missing files:        {missing_file_count} warnings")
            print("=" * 60)
            print("✅ Migration completed successfully!")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Migration FAILED: {e}")
            print("⏪ Transaction rolled back")
            raise


async def main():
    """Entry point with error handling."""
    try:
        await migrate_timevision_files()
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
