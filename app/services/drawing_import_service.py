"""GESTIMA - Drawing Import Service

Business logic for importing drawings from network share to FileRecord system.
Delegates physical file operations to FileService (ADR-044).

2-step workflow:
1. scan_share() + preview_import() -> show what matches
2. execute_import() -> copy files, create records, link to parts
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.file_record import FileLink
from app.schemas.drawing_import import (
    ShareFileInfo,
    ShareFolderPreview,
    DrawingImportPreviewResponse,
    ShareStatusResponse,
    ImportFolderRequest,
    DrawingImportExecuteResponse,
)
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

# Folder name prefixes to skip (not real parts)
SKIP_PREFIXES = ("46", "47")

# File extensions to import
PDF_EXTENSIONS = {".pdf"}
STEP_EXTENSIONS = {".step", ".stp"}


def _scan_share_sync(share_path: Path) -> list[dict]:
    """
    Synchronous filesystem scan of network share.

    Returns list of dicts with folder_name, pdf_files, step_files.
    Runs in thread pool via asyncio.to_thread().
    """
    if not share_path.exists() or not share_path.is_dir():
        return []

    results = []
    for entry in sorted(share_path.iterdir()):
        if not entry.is_dir():
            continue

        folder_name = entry.name

        # Skip folders by prefix
        if folder_name.startswith(SKIP_PREFIXES):
            continue

        pdf_files = []
        step_files = []

        for file_entry in entry.iterdir():
            if not file_entry.is_file():
                continue

            ext = file_entry.suffix.lower()
            file_size = file_entry.stat().st_size

            if ext in PDF_EXTENSIONS:
                pdf_files.append({
                    "filename": file_entry.name,
                    "file_size": file_size,
                    "file_type": "pdf",
                })
            elif ext in STEP_EXTENSIONS:
                step_files.append({
                    "filename": file_entry.name,
                    "file_size": file_size,
                    "file_type": "step",
                })

        # Sort alphabetically for consistent primary selection
        pdf_files.sort(key=lambda f: f["filename"])
        step_files.sort(key=lambda f: f["filename"])

        results.append({
            "folder_name": folder_name,
            "pdf_files": pdf_files,
            "step_files": step_files,
        })

    return results


class DrawingImportService:
    """
    Import drawings from network share to FileRecord system.

    Business logic:
    - Scan share folders
    - Match folder names to Part.article_number
    - Preview before import (2-step workflow)
    - Copy files + create FileRecord + FileLink
    - Set Part.file_id for primary PDF
    """

    def __init__(self, share_path: str):
        self.share_path = Path(share_path)

    def check_status(self) -> ShareStatusResponse:
        """Check if share is accessible."""
        if not self.share_path.exists():
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=False,
                total_folders=0,
                message=f"Share not accessible: {self.share_path}",
            )

        try:
            folder_count = sum(
                1 for e in self.share_path.iterdir()
                if e.is_dir() and not e.name.startswith(SKIP_PREFIXES)
            )
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=True,
                total_folders=folder_count,
                message="OK",
            )
        except PermissionError:
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=False,
                total_folders=0,
                message="Permission denied",
            )

    async def scan_share(self) -> list[dict]:
        """Scan network share folders (async wrapper)."""
        return await asyncio.to_thread(_scan_share_sync, self.share_path)

    async def preview_import(
        self,
        db: AsyncSession,
    ) -> DrawingImportPreviewResponse:
        """
        Step 1: Scan share + match folders to Parts + return preview.

        Uses batch DB queries for performance (single query for all folders).
        """
        # 1. Scan share
        share_folders = await self.scan_share()

        if not share_folders:
            return DrawingImportPreviewResponse(
                share_path=str(self.share_path),
                total_folders=0,
                folders=[],
            )

        # Count skipped folders
        total_on_disk = sum(
            1 for e in self.share_path.iterdir() if e.is_dir()
        ) if self.share_path.exists() else 0
        skipped_count = total_on_disk - len(share_folders)

        # 2. Batch query Parts by article_number
        folder_names = [f["folder_name"] for f in share_folders]

        # SQLite has a limit on IN clause params, chunk if needed
        parts_map: dict[str, dict] = {}  # article_number -> {id, part_number, file_id}
        chunk_size = 500
        for i in range(0, len(folder_names), chunk_size):
            chunk = folder_names[i:i + chunk_size]
            result = await db.execute(
                select(
                    Part.id,
                    Part.part_number,
                    Part.article_number,
                    Part.file_id,
                ).where(
                    and_(
                        Part.article_number.in_(chunk),
                        Part.deleted_at.is_(None),
                    )
                )
            )
            for row in result.all():
                parts_map[row.article_number] = {
                    "id": row.id,
                    "part_number": row.part_number,
                    "file_id": row.file_id,
                }

        # 3. Batch query existing FileLinks for matched parts
        matched_part_ids = [p["id"] for p in parts_map.values()]
        linked_part_ids: set[int] = set()

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
                linked_part_ids.update(row[0] for row in result.all())

        # 4. Build preview
        folders: list[ShareFolderPreview] = []
        stats = {"matched": 0, "unmatched": 0, "already_imported": 0, "ready": 0, "no_pdf": 0}

        for folder_data in share_folders:
            folder_name = folder_data["folder_name"]
            pdf_files = [ShareFileInfo(**f) for f in folder_data["pdf_files"]]
            step_files = [ShareFileInfo(**f) for f in folder_data["step_files"]]

            part_info = parts_map.get(folder_name)

            if not part_info:
                status = "no_match"
                stats["unmatched"] += 1
                folders.append(ShareFolderPreview(
                    folder_name=folder_name,
                    pdf_files=pdf_files,
                    step_files=step_files,
                    status=status,
                ))
                continue

            stats["matched"] += 1

            # Check if already imported
            already = (
                part_info["file_id"] is not None
                or part_info["id"] in linked_part_ids
            )

            if already:
                status = "already_imported"
                stats["already_imported"] += 1
            elif not pdf_files:
                status = "no_pdf"
                stats["no_pdf"] += 1
            else:
                status = "ready"
                stats["ready"] += 1

            primary_pdf = pdf_files[0].filename if pdf_files else None

            folders.append(ShareFolderPreview(
                folder_name=folder_name,
                matched_part_id=part_info["id"],
                matched_part_number=part_info["part_number"],
                matched_article_number=folder_name,
                pdf_files=pdf_files,
                step_files=step_files,
                primary_pdf=primary_pdf,
                already_imported=already,
                status=status,
            ))

        return DrawingImportPreviewResponse(
            share_path=str(self.share_path),
            total_folders=len(share_folders),
            matched=stats["matched"],
            unmatched=stats["unmatched"],
            already_imported=stats["already_imported"],
            ready=stats["ready"],
            no_pdf=stats["no_pdf"],
            skipped=skipped_count,
            folders=folders,
        )

    async def execute_import(
        self,
        folders: list[ImportFolderRequest],
        db: AsyncSession,
        *,
        created_by: str = "drawing_import",
    ) -> DrawingImportExecuteResponse:
        """
        Step 2: Execute import for confirmed folders.

        Copies files from share to uploads/, creates FileRecord + FileLink,
        sets Part.file_id. Commits in batches of 50.
        """
        files_created = 0
        links_created = 0
        parts_updated = 0
        skipped = 0
        errors: list[str] = []
        batch_size = 50

        for idx, folder_req in enumerate(folders):
            try:
                await self._import_folder(
                    folder_req, db, created_by=created_by,
                    counters={"files": 0, "links": 0, "parts": 0},
                )
                # Update counts from the import
                files_created += 1  # At minimum the primary PDF
                links_created += 1
                parts_updated += 1

            except Exception as e:
                error_msg = f"{folder_req.folder_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Import failed for folder {folder_req.folder_name}: {e}", exc_info=True)
                # Rollback this folder's changes but continue
                await db.rollback()
                continue

            # Commit in batches
            if (idx + 1) % batch_size == 0:
                try:
                    await db.commit()
                    logger.info(f"Batch commit: {idx + 1}/{len(folders)} folders processed")
                except Exception as e:
                    logger.error(f"Batch commit failed at {idx + 1}: {e}", exc_info=True)
                    errors.append(f"Batch commit failed at {idx + 1}: {str(e)}")
                    await db.rollback()

        # Final commit for remaining
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Final commit failed: {e}", exc_info=True)
            errors.append(f"Final commit failed: {str(e)}")
            await db.rollback()

        success = len(errors) == 0
        logger.info(
            f"Drawing import complete: {files_created} files, {links_created} links, "
            f"{parts_updated} parts, {skipped} skipped, {len(errors)} errors"
        )

        return DrawingImportExecuteResponse(
            success=success,
            files_created=files_created,
            links_created=links_created,
            parts_updated=parts_updated,
            skipped=skipped,
            errors=errors,
        )

    async def _import_folder(
        self,
        folder_req: ImportFolderRequest,
        db: AsyncSession,
        *,
        created_by: str,
        counters: dict,
    ) -> None:
        """Import a single folder's files."""
        folder_path = self.share_path / folder_req.folder_name

        if not folder_path.exists():
            raise ValueError(f"Folder not found: {folder_req.folder_name}")

        # Get the Part
        result = await db.execute(
            select(Part).where(
                and_(Part.id == folder_req.part_id, Part.deleted_at.is_(None))
            )
        )
        part = result.scalar_one_or_none()
        if not part:
            raise ValueError(f"Part not found: ID {folder_req.part_id}")

        # Import primary PDF
        primary_pdf_path = folder_path / folder_req.primary_pdf
        if not primary_pdf_path.exists():
            raise ValueError(f"Primary PDF not found: {folder_req.primary_pdf}")

        directory = f"parts/{part.part_number}"

        # Store file via FileService
        record = await file_service.store_from_path(
            source_path=primary_pdf_path,
            directory=directory,
            db=db,
            allowed_types=["pdf"],
            created_by=created_by,
        )

        # Link to part as primary drawing
        await file_service.link(
            file_id=record.id,
            entity_type="part",
            entity_id=part.id,
            db=db,
            is_primary=True,
            link_type="drawing",
            created_by=created_by,
        )

        # Set Part.file_id + drawing_path (backwards compat for UI)
        part.file_id = record.id
        part.drawing_path = record.file_path

        # Import additional PDFs (non-primary)
        for pdf_file in folder_path.iterdir():
            if not pdf_file.is_file():
                continue
            if pdf_file.suffix.lower() not in PDF_EXTENSIONS:
                continue
            if pdf_file.name == folder_req.primary_pdf:
                continue  # Already imported as primary

            try:
                extra_record = await file_service.store_from_path(
                    source_path=pdf_file,
                    directory=directory,
                    db=db,
                    allowed_types=["pdf"],
                    created_by=created_by,
                )
                await file_service.link(
                    file_id=extra_record.id,
                    entity_type="part",
                    entity_id=part.id,
                    db=db,
                    is_primary=False,
                    link_type="drawing",
                    created_by=created_by,
                )
            except Exception as e:
                logger.warning(f"Failed to import extra PDF {pdf_file.name}: {e}")

        # Import STEP files
        if folder_req.import_step:
            for step_file in folder_path.iterdir():
                if not step_file.is_file():
                    continue
                if step_file.suffix.lower() not in STEP_EXTENSIONS:
                    continue

                try:
                    step_record = await file_service.store_from_path(
                        source_path=step_file,
                        directory=directory,
                        db=db,
                        allowed_types=["step"],
                        created_by=created_by,
                    )
                    await file_service.link(
                        file_id=step_record.id,
                        entity_type="part",
                        entity_id=part.id,
                        db=db,
                        is_primary=False,
                        link_type="step_model",
                        created_by=created_by,
                    )
                except Exception as e:
                    logger.warning(f"Failed to import STEP {step_file.name}: {e}")
