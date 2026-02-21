"""GESTIMA - Recovery script: re-link existing files in uploads/ to Parts

After DB reset, physical files in uploads/parts/{...}/ survive
but FileRecord + FileLink + Part.file_id are gone.

Two-phase matching:
  Phase 1: folder_name == Part.article_number (direct match)
  Phase 2: For unmatched folders (old part_numbers like 10XXXXXXXX),
           parse PDF filenames using word-boundary token matching
           against all known article_numbers (same logic as infor_document_importer).

This script:
1. Scans uploads/parts/*/ folders
2. Phase 1: Direct folder_name → Part.article_number match
3. Phase 2: Filename-based token matching for remaining folders
4. Creates FileRecord for each PDF (hash, size, path — NO copy)
5. Creates FileLink (entity_type='part', link_type='drawing')
6. Sets Part.file_id for primary PDF (alphabetically first)
7. Batch commits every 50 folders

Usage:
    python scripts/recover_uploads.py [--dry-run]
"""

import asyncio
import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.file_record import FileRecord, FileLink
from app.models.part import Part

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
PARTS_DIR = UPLOADS_DIR / "parts"
BATCH_SIZE = 50
PDF_EXTENSIONS = {".pdf"}

# Suffixes to strip from PDF filename before matching (common in Gestima exports)
STRIP_SUFFIXES = re.compile(r"[-_](nabidka|DRAW|draw)\b", re.IGNORECASE)


def calculate_hash(file_path: Path) -> str:
    """SHA-256 hash — same as file_service._calculate_hash."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def match_filename_to_article(
    pdf_filename: str,
    lookup: dict[str, tuple[int, str]],
) -> Optional[tuple[str, int, str]]:
    """Match PDF filename to Part via word-boundary token matching.

    Same logic as infor_document_importer.match_documents_to_parts:
    - Normalise filename (lowercase, strip .pdf, strip known suffixes)
    - Exact match has priority
    - Token match: article_number bordered by non-alphanumeric or start/end
    - Longest match wins (most specific)

    Args:
        pdf_filename: e.g. "99.001.77854_Koppelplatte_F4-nabidka.pdf"
        lookup: {article_number_lower: (part_id, part_number)}

    Returns:
        (article_number, part_id, part_number) or None
    """
    # Normalise: lowercase, strip extension
    stem = pdf_filename.lower().strip()
    if stem.endswith(".pdf"):
        stem = stem[:-4]
    # Strip known suffixes (-nabidka, _DRAW etc.)
    stem = STRIP_SUFFIXES.sub("", stem)

    # 1. Exact match
    if stem in lookup:
        part_id, part_number = lookup[stem]
        return stem, part_id, part_number

    # 2. Token match (word-boundary) — same as infor_document_importer
    token_matches: list[tuple[str, int, str]] = []
    for identifier, (part_id, part_number) in lookup.items():
        if not identifier or identifier not in stem:
            continue
        pattern = (
            r"(?:^|[^a-zA-Z0-9])"
            + re.escape(identifier)
            + r"(?:$|[^a-zA-Z0-9])"
        )
        if re.search(pattern, stem):
            token_matches.append((identifier, part_id, part_number))

    if not token_matches:
        return None

    # Longest match wins (most specific article_number)
    token_matches.sort(key=lambda m: len(m[0]), reverse=True)
    return token_matches[0]


async def recover(dry_run: bool = False):
    if not PARTS_DIR.exists():
        logger.error(f"Directory not found: {PARTS_DIR}")
        return

    # Collect all folders
    folders = sorted(
        [d for d in PARTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    logger.info(f"Found {len(folders)} folders in {PARTS_DIR}")

    async with async_session() as db:
        # Load ALL Parts for both phases
        all_parts_result = await db.execute(
            select(Part.id, Part.part_number, Part.article_number).where(
                Part.deleted_at.is_(None),
            )
        )
        all_parts = all_parts_result.all()

        # article_number -> (id, part_number) — for Phase 1 direct match
        parts_by_article: dict[str, tuple[int, str]] = {}
        # article_number_lower -> (id, part_number) — for Phase 2 token match
        parts_lookup_lower: dict[str, tuple[int, str]] = {}

        for row in all_parts:
            if row.article_number:
                parts_by_article[row.article_number] = (row.id, row.part_number)
                key = row.article_number.lower().strip()
                if key:
                    parts_lookup_lower[key] = (row.id, row.part_number)

        logger.info(f"Loaded {len(parts_by_article)} active Parts from DB")

        # Phase 1: Direct folder_name → article_number match
        phase1_matched: dict[Path, tuple[int, str, str]] = {}  # folder → (part_id, part_number, article)
        unmatched_folders: list[Path] = []

        for folder_path in folders:
            folder_name = folder_path.name
            if folder_name in parts_by_article:
                part_id, part_number = parts_by_article[folder_name]
                phase1_matched[folder_path] = (part_id, part_number, folder_name)
            else:
                unmatched_folders.append(folder_path)

        logger.info(
            f"Phase 1 (direct match): {len(phase1_matched)} matched, "
            f"{len(unmatched_folders)} unmatched"
        )

        # Phase 2: Filename-based token matching for unmatched folders
        phase2_matched: dict[Path, tuple[int, str, str]] = {}
        still_unmatched: list[Path] = []

        for folder_path in unmatched_folders:
            # Get first PDF in folder (alphabetically)
            pdf_files = sorted(
                [f for f in folder_path.iterdir()
                 if f.is_file() and f.suffix.lower() in PDF_EXTENSIONS],
                key=lambda f: f.name,
            )
            if not pdf_files:
                still_unmatched.append(folder_path)
                continue

            # Try matching each PDF filename until we find a hit
            matched = False
            for pdf_file in pdf_files:
                result = match_filename_to_article(pdf_file.name, parts_lookup_lower)
                if result:
                    article_lower, part_id, part_number = result
                    # Find the original-case article_number
                    article_original = next(
                        (a for a in parts_by_article if a.lower() == article_lower),
                        article_lower,
                    )
                    phase2_matched[folder_path] = (part_id, part_number, article_original)
                    if dry_run:
                        logger.info(
                            f"  [Phase 2] {folder_path.name}/{pdf_file.name} "
                            f"→ article={article_original}"
                        )
                    matched = True
                    break

            if not matched:
                still_unmatched.append(folder_path)

        logger.info(
            f"Phase 2 (filename match): {len(phase2_matched)} matched, "
            f"{len(still_unmatched)} still unmatched"
        )

        # Merge both phases
        all_matched = {**phase1_matched, **phase2_matched}

        # Batch check existing FileLinks to avoid duplicates
        matched_part_ids = [pid for pid, _, _ in all_matched.values()]
        already_linked: set[int] = set()
        chunk_size = 500
        if matched_part_ids:
            for i in range(0, len(matched_part_ids), chunk_size):
                chunk = matched_part_ids[i:i + chunk_size]
                result = await db.execute(
                    select(FileLink.entity_id).where(
                        and_(
                            FileLink.entity_type == "part",
                            FileLink.entity_id.in_(chunk),
                            FileLink.deleted_at.is_(None),
                        )
                    )
                )
                already_linked.update(row[0] for row in result.all())

        if already_linked:
            logger.info(f"Skipping {len(already_linked)} parts already linked")

        # Process all matched folders
        total_files = 0
        total_links = 0
        total_parts_updated = 0
        total_skipped = 0
        errors: list[str] = []
        processed = 0

        for folder_path, (part_id, part_number, article_number) in sorted(
            all_matched.items(), key=lambda x: x[0].name
        ):
            if part_id in already_linked:
                total_skipped += 1
                continue

            # Find PDFs in folder (sorted alphabetically — first = primary)
            pdf_files = sorted(
                [f for f in folder_path.iterdir()
                 if f.is_file() and f.suffix.lower() in PDF_EXTENSIONS],
                key=lambda f: f.name,
            )

            if not pdf_files:
                continue

            if dry_run:
                phase = "P1" if folder_path in phase1_matched else "P2"
                logger.info(
                    f"[DRY-RUN][{phase}] {folder_path.name}: "
                    f"{len(pdf_files)} PDFs → Part {part_number} ({article_number})"
                )
                total_files += len(pdf_files)
                total_parts_updated += 1
                continue

            # Create FileRecord + FileLink for each PDF
            primary_record = None

            for pdf_idx, pdf_path in enumerate(pdf_files):
                try:
                    file_size = pdf_path.stat().st_size
                    file_hash = calculate_hash(pdf_path)
                    relative_path = str(pdf_path.relative_to(UPLOADS_DIR))
                    is_primary = pdf_idx == 0

                    record = FileRecord(
                        file_hash=file_hash,
                        file_path=relative_path,
                        original_filename=pdf_path.name,
                        file_size=file_size,
                        file_type="pdf",
                        mime_type="application/pdf",
                        status="active",
                        created_by="recovery",
                        updated_by="recovery",
                    )
                    db.add(record)
                    await db.flush()

                    link = FileLink(
                        file_id=record.id,
                        entity_type="part",
                        entity_id=part_id,
                        link_type="drawing",
                        is_primary=is_primary,
                        created_by="recovery",
                    )
                    db.add(link)

                    if is_primary:
                        primary_record = record

                    total_files += 1
                    total_links += 1

                except Exception as e:
                    errors.append(f"{folder_path.name}/{pdf_path.name}: {e}")
                    logger.error(f"Error processing {pdf_path}: {e}")

            # Set Part.file_id to primary PDF
            if primary_record:
                part_result = await db.execute(
                    select(Part).where(Part.id == part_id)
                )
                part = part_result.scalar_one_or_none()
                if part:
                    part.file_id = primary_record.id
                    total_parts_updated += 1

            processed += 1

            # Batch commit
            if processed % BATCH_SIZE == 0:
                try:
                    await db.commit()
                    logger.info(f"Committed batch {processed // BATCH_SIZE}: {processed} folders processed")
                except Exception as e:
                    await db.rollback()
                    errors.append(f"Batch commit failed at {processed}: {e}")
                    logger.error(f"Batch commit failed: {e}", exc_info=True)

        # Final commit
        if not dry_run:
            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                errors.append(f"Final commit failed: {e}")

    # Summary
    prefix = "[DRY-RUN] " if dry_run else ""
    logger.info(f"\n{prefix}=== RECOVERY SUMMARY ===")
    logger.info(f"{prefix}Folders scanned:      {len(folders)}")
    logger.info(f"{prefix}Phase 1 (direct):     {len(phase1_matched)}")
    logger.info(f"{prefix}Phase 2 (filename):   {len(phase2_matched)}")
    logger.info(f"{prefix}Total matched:        {len(all_matched)}")
    logger.info(f"{prefix}Still unmatched:      {len(still_unmatched)}")
    logger.info(f"{prefix}Already linked:       {len(already_linked)}")
    logger.info(f"{prefix}Skipped (linked):     {total_skipped}")
    logger.info(f"{prefix}FileRecords created:  {total_files}")
    logger.info(f"{prefix}FileLinks created:    {total_links}")
    logger.info(f"{prefix}Parts.file_id set:    {total_parts_updated}")
    logger.info(f"{prefix}Errors:               {len(errors)}")

    if errors:
        logger.warning(f"Errors ({len(errors)}):")
        for err in errors[:20]:
            logger.warning(f"  {err}")

    if still_unmatched and dry_run:
        logger.info(f"\nUnmatched folders (first 20):")
        for folder in still_unmatched[:20]:
            pdfs = [f.name for f in folder.iterdir()
                    if f.is_file() and f.suffix.lower() == ".pdf"]
            logger.info(f"  {folder.name}/ → {pdfs[:3]}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("Running in DRY-RUN mode (no DB changes)")
    asyncio.run(recover(dry_run=dry_run))
