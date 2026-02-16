"""GESTIMA - Centralized File Service (ADR-044)

"Dumb" file storage manager - ONLY physical file operations.
NO business logic (primary drawing, TimeVision matching, etc.).

Features:
- Magic bytes validation (security-critical)
- SHA-256 hash for integrity
- Soft delete via FileRecord.deleted_at
- Temp file cleanup via status field
- Orphan detection (files without links)
- Path traversal prevention
- File size limits

Business logic STAYS in respective routers/services.
"""

import hashlib
import logging
import re
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_record import FileRecord, FileLink

logger = logging.getLogger(__name__)


class FileService:
    """
    Centralized file storage service.

    Responsibilities:
    - Store files on disk
    - Validate file types (magic bytes)
    - Create DB records
    - Manage file-entity links
    - Cleanup temp/orphaned files

    NOT responsible for:
    - Business logic (primary drawing, revision, etc.)
    - Entity-specific workflows
    - Notifications
    """

    # Configuration
    UPLOADS_DIR = Path("uploads")

    # Magic bytes for validation
    MAGIC_BYTES = {
        "pdf": (b"%PDF", 4),
        "step": (b"ISO-10303", 20),
    }

    MIME_TYPES = {
        "pdf": "application/pdf",
        "step": "application/step",
        "stp": "application/step",
        "nc": "text/plain",
        "gcode": "text/plain",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    MAX_FILE_SIZES = {
        "pdf": 10 * 1024 * 1024,      # 10 MB
        "step": 100 * 1024 * 1024,     # 100 MB
        "stp": 100 * 1024 * 1024,
    }
    DEFAULT_MAX_SIZE = 50 * 1024 * 1024  # 50 MB default

    TEMP_EXPIRY_HOURS = 24

    def __init__(self):
        """Initialize service and ensure base directory exists."""
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # ==================== CORE METHODS ====================

    async def store(
        self,
        file: UploadFile,
        directory: str,
        db: AsyncSession,
        *,
        allowed_types: Optional[list[str]] = None,
        created_by: Optional[str] = None
    ) -> FileRecord:
        """
        Store file to disk and create DB record.

        Steps:
        1. Detect file_type from extension
        2. Validate allowed_types (if provided)
        3. Validate magic bytes (for pdf, step)
        4. Validate file size
        5. Save to disk: uploads/{directory}/{sanitized_filename}
        6. Calculate SHA-256 hash
        7. Create FileRecord in DB
        8. Return FileRecord

        Transaction handling (L-008):
        - If DB fails → delete file from disk (compensating transaction)
        - Commit handled by CALLER

        Args:
            file: Uploaded file
            directory: Subdirectory (e.g., "parts/10900635" or "loose")
            db: Database session
            allowed_types: Optional list of allowed types (e.g., ["pdf", "step"])
            created_by: Username for audit

        Returns:
            FileRecord: Created database record

        Raises:
            HTTPException 400: Invalid file type
            HTTPException 413: File too large
            HTTPException 500: Storage failed
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # 1. Detect file type
        file_type = self._detect_file_type(file.filename)

        # 2. Validate allowed types
        if allowed_types and file_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_type}' not allowed. Allowed: {', '.join(allowed_types)}"
            )

        # 3. Validate magic bytes
        await self._validate_magic_bytes_upload(file, file_type)

        # 4. Validate file size
        file_size = await self._validate_file_size_upload(file, file_type)

        # 5. Save to disk
        target_dir = self._ensure_directory(directory)
        safe_filename = self._sanitize_filename(file.filename)

        # Handle duplicate filenames (add UUID suffix)
        file_path = target_dir / safe_filename
        if file_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            unique_suffix = str(uuid.uuid4())[:8]
            safe_filename = f"{stem}_{unique_suffix}{suffix}"
            file_path = target_dir / safe_filename

        # Save file to disk
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"Saved file to disk: {file_path} ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to save file to disk: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save file to disk")

        # 6. Calculate hash
        file_hash = self._calculate_hash(file_path)

        # 7. Create DB record
        relative_path = f"{directory}/{safe_filename}"
        mime_type = self.MIME_TYPES.get(file_type, "application/octet-stream")

        try:
            record = FileRecord(
                file_hash=file_hash,
                file_path=relative_path,
                original_filename=file.filename,
                file_size=file_size,
                file_type=file_type,
                mime_type=mime_type,
                status="active",
                created_by=created_by,
                updated_by=created_by
            )
            db.add(record)
            await db.flush()  # Get ID without committing

            logger.info(
                f"Created FileRecord: ID={record.id}, path='{relative_path}', "
                f"type={file_type}, size={file_size}, hash={file_hash[:16]}..."
            )

            return record

        except Exception as e:
            # ROLLBACK: Delete file from disk
            logger.error(f"DB insert failed, deleting file from disk: {file_path}", exc_info=True)
            try:
                file_path.unlink()
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup file after DB error: {cleanup_error}")

            raise HTTPException(status_code=500, detail="Failed to create file record in database")

    def get(self, file_id: int, db: AsyncSession) -> FileRecord:
        """
        Get FileRecord by ID.

        Args:
            file_id: File ID
            db: Database session

        Returns:
            FileRecord: File record

        Raises:
            HTTPException 404: File not found
        """
        raise NotImplementedError("Use async version: await get_async()")

    async def get_async(self, file_id: int, db: AsyncSession) -> FileRecord:
        """
        Get FileRecord by ID (async).

        Args:
            file_id: File ID
            db: Database session

        Returns:
            FileRecord: File record

        Raises:
            HTTPException 404: File not found or deleted
        """
        try:
            result = await db.execute(
                select(FileRecord).where(
                    and_(
                        FileRecord.id == file_id,
                        FileRecord.deleted_at.is_(None)
                    )
                )
            )
            record = result.scalar_one_or_none()

            if not record:
                raise HTTPException(status_code=404, detail=f"File not found: ID {file_id}")

            return record

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get file {file_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Database error")

    async def link(
        self,
        file_id: int,
        entity_type: str,
        entity_id: int,
        db: AsyncSession,
        *,
        is_primary: bool = False,
        revision: Optional[str] = None,
        link_type: str = "drawing",
        created_by: Optional[str] = None
    ) -> FileLink:
        """
        Link file to entity. UPSERT: update if link exists, insert if not.

        If is_primary=True, unset other primary links for same entity+link_type.

        Transaction handling (L-008):
        - Commit handled by CALLER

        Args:
            file_id: File ID
            entity_type: Entity type (e.g., "part", "quote_item", "timevision")
            entity_id: Entity ID
            db: Database session
            is_primary: Set as primary link
            revision: Optional revision (e.g., "A", "B")
            link_type: Link type (e.g., "drawing", "step_model", "nc_program")
            created_by: Username for audit

        Returns:
            FileLink: Created or updated link

        Raises:
            HTTPException 404: File not found
            HTTPException 500: Database error
        """
        # Verify file exists
        await self.get_async(file_id, db)

        try:
            # Check if link already exists (UPSERT)
            result = await db.execute(
                select(FileLink).where(
                    and_(
                        FileLink.file_id == file_id,
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.deleted_at.is_(None)
                    )
                )
            )
            existing_link = result.scalar_one_or_none()

            if existing_link:
                # UPDATE existing link
                existing_link.is_primary = is_primary
                existing_link.revision = revision
                existing_link.link_type = link_type
                existing_link.updated_at = datetime.utcnow()
                existing_link.updated_by = created_by

                logger.info(
                    f"Updated FileLink: ID={existing_link.id}, file_id={file_id}, "
                    f"entity={entity_type}:{entity_id}, primary={is_primary}"
                )

                link = existing_link
            else:
                # INSERT new link
                link = FileLink(
                    file_id=file_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    is_primary=is_primary,
                    revision=revision,
                    link_type=link_type,
                    created_by=created_by,
                    updated_by=created_by
                )
                db.add(link)
                await db.flush()

                logger.info(
                    f"Created FileLink: ID={link.id}, file_id={file_id}, "
                    f"entity={entity_type}:{entity_id}, primary={is_primary}"
                )

            # If is_primary=True, unset others
            if is_primary:
                await db.execute(
                    select(FileLink).where(
                        and_(
                            FileLink.entity_type == entity_type,
                            FileLink.entity_id == entity_id,
                            FileLink.link_type == link_type,
                            FileLink.id != link.id,
                            FileLink.deleted_at.is_(None)
                        )
                    )
                )
                # Update is_primary=False for all other links
                result = await db.execute(
                    select(FileLink).where(
                        and_(
                            FileLink.entity_type == entity_type,
                            FileLink.entity_id == entity_id,
                            FileLink.link_type == link_type,
                            FileLink.id != link.id,
                            FileLink.deleted_at.is_(None)
                        )
                    )
                )
                other_links = result.scalars().all()
                for other_link in other_links:
                    other_link.is_primary = False
                    other_link.updated_at = datetime.utcnow()

                logger.info(
                    f"Unset is_primary for {len(other_links)} other links "
                    f"(entity={entity_type}:{entity_id}, link_type={link_type})"
                )

            return link

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to link file {file_id} to {entity_type}:{entity_id}: {e}",
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Failed to create file link")

    async def unlink(
        self,
        file_id: int,
        entity_type: str,
        entity_id: int,
        db: AsyncSession
    ) -> None:
        """
        Unlink file from entity (soft delete FileLink).

        Transaction handling (L-008):
        - Commit handled by CALLER

        Args:
            file_id: File ID
            entity_type: Entity type
            entity_id: Entity ID
            db: Database session

        Raises:
            HTTPException 404: Link not found
            HTTPException 500: Database error
        """
        try:
            result = await db.execute(
                select(FileLink).where(
                    and_(
                        FileLink.file_id == file_id,
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.deleted_at.is_(None)
                    )
                )
            )
            link = result.scalar_one_or_none()

            if not link:
                raise HTTPException(
                    status_code=404,
                    detail=f"Link not found: file {file_id} → {entity_type}:{entity_id}"
                )

            # Soft delete
            link.deleted_at = datetime.utcnow()
            link.updated_at = datetime.utcnow()

            logger.info(
                f"Soft deleted FileLink: ID={link.id}, file_id={file_id}, "
                f"entity={entity_type}:{entity_id}"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to unlink file {file_id} from {entity_type}:{entity_id}: {e}",
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Failed to unlink file")

    async def delete(
        self,
        file_id: int,
        db: AsyncSession,
        deleted_by: Optional[str] = None
    ) -> None:
        """
        Soft delete FileRecord. FileLinks remain (cascade in query filters).

        Physical file on disk is NOT deleted (safety).

        Transaction handling (L-008):
        - Commit handled by CALLER

        Args:
            file_id: File ID
            db: Database session
            deleted_by: Username for audit

        Raises:
            HTTPException 404: File not found
            HTTPException 500: Database error
        """
        record = await self.get_async(file_id, db)

        try:
            record.deleted_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            record.deleted_by = deleted_by

            logger.info(
                f"Soft deleted FileRecord: ID={file_id}, path='{record.file_path}'"
            )

        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete file")

    # ==================== HELPER METHODS ====================

    async def get_files_for_entity(
        self,
        entity_type: str,
        entity_id: int,
        db: AsyncSession,
        *,
        link_type: Optional[str] = None
    ) -> list[FileRecord]:
        """
        Get all files linked to entity (JOIN FileRecord + FileLink).

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            db: Database session
            link_type: Optional filter by link_type

        Returns:
            list[FileRecord]: Files linked to entity
        """
        try:
            query = (
                select(FileRecord)
                .join(FileLink, FileRecord.id == FileLink.file_id)
                .where(
                    and_(
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.deleted_at.is_(None),
                        FileRecord.deleted_at.is_(None)
                    )
                )
            )

            if link_type:
                query = query.where(FileLink.link_type == link_type)

            result = await db.execute(query)
            files = result.scalars().all()

            logger.debug(
                f"Found {len(files)} files for {entity_type}:{entity_id} "
                f"(link_type={link_type or 'all'})"
            )

            return list(files)

        except Exception as e:
            logger.error(
                f"Failed to get files for {entity_type}:{entity_id}: {e}",
                exc_info=True
            )
            return []

    async def get_primary(
        self,
        entity_type: str,
        entity_id: int,
        db: AsyncSession,
        link_type: str = "drawing"
    ) -> Optional[FileRecord]:
        """
        Get primary file for entity with specific link_type.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            db: Database session
            link_type: Link type (default: "drawing")

        Returns:
            FileRecord | None: Primary file or None
        """
        try:
            result = await db.execute(
                select(FileRecord)
                .join(FileLink, FileRecord.id == FileLink.file_id)
                .where(
                    and_(
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.link_type == link_type,
                        FileLink.is_primary == True,
                        FileLink.deleted_at.is_(None),
                        FileRecord.deleted_at.is_(None)
                    )
                )
                .limit(1)
            )
            primary = result.scalar_one_or_none()

            if primary:
                logger.debug(
                    f"Found primary {link_type} for {entity_type}:{entity_id}: "
                    f"FileRecord ID={primary.id}"
                )

            return primary

        except Exception as e:
            logger.error(
                f"Failed to get primary for {entity_type}:{entity_id}: {e}",
                exc_info=True
            )
            return None

    async def set_primary(
        self,
        file_id: int,
        entity_type: str,
        entity_id: int,
        db: AsyncSession
    ) -> None:
        """
        Set file as primary for entity (unset others of same link_type).

        Transaction handling (L-008):
        - Commit handled by CALLER

        Args:
            file_id: File ID
            entity_type: Entity type
            entity_id: Entity ID
            db: Database session

        Raises:
            HTTPException 404: Link not found
            HTTPException 500: Database error
        """
        try:
            # Get the link
            result = await db.execute(
                select(FileLink).where(
                    and_(
                        FileLink.file_id == file_id,
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.deleted_at.is_(None)
                    )
                )
            )
            link = result.scalar_one_or_none()

            if not link:
                raise HTTPException(
                    status_code=404,
                    detail=f"Link not found: file {file_id} → {entity_type}:{entity_id}"
                )

            # Already primary? No-op
            if link.is_primary:
                logger.debug(f"FileLink {link.id} is already primary")
                return

            # Unset other primary links of same link_type
            result = await db.execute(
                select(FileLink).where(
                    and_(
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.link_type == link.link_type,
                        FileLink.id != link.id,
                        FileLink.deleted_at.is_(None)
                    )
                )
            )
            other_links = result.scalars().all()
            for other_link in other_links:
                other_link.is_primary = False
                other_link.updated_at = datetime.utcnow()

            # Set this link as primary
            link.is_primary = True
            link.updated_at = datetime.utcnow()

            logger.info(
                f"Set FileLink {link.id} as primary (unset {len(other_links)} others)"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to set primary for file {file_id}: {e}",
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Failed to set primary file")

    async def cleanup_temp(self, db: AsyncSession, max_age_hours: int = 24) -> int:
        """
        Delete temp files (status='temp') older than max_age_hours.

        Deletes from both disk and DB.

        Transaction handling (L-008):
        - Commit handled by CALLER

        Args:
            db: Database session
            max_age_hours: Max age in hours (default: 24)

        Returns:
            int: Number of files deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted_count = 0

        try:
            # Find expired temp files
            result = await db.execute(
                select(FileRecord).where(
                    and_(
                        FileRecord.status == "temp",
                        FileRecord.created_at < cutoff_time,
                        FileRecord.deleted_at.is_(None)
                    )
                )
            )
            expired_files = result.scalars().all()

            for record in expired_files:
                # Delete from disk
                file_path = self.UPLOADS_DIR / record.file_path
                try:
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug(f"Deleted temp file from disk: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")

                # Soft delete from DB
                record.deleted_at = datetime.utcnow()
                record.updated_at = datetime.utcnow()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleanup: deleted {deleted_count} temp files "
                    f"(older than {max_age_hours}h)"
                )

            return deleted_count

        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}", exc_info=True)
            return deleted_count

    async def find_orphans(self, db: AsyncSession) -> list[FileRecord]:
        """
        Find files without any active FileLink (excluding temp files).

        Args:
            db: Database session

        Returns:
            list[FileRecord]: Orphaned files
        """
        try:
            # Subquery: file_ids with active links
            subquery = select(FileLink.file_id).where(
                FileLink.deleted_at.is_(None)
            ).distinct()

            # Files NOT in subquery (and not temp)
            result = await db.execute(
                select(FileRecord).where(
                    and_(
                        FileRecord.id.notin_(subquery),
                        FileRecord.status != "temp",
                        FileRecord.deleted_at.is_(None)
                    )
                )
            )
            orphans = result.scalars().all()

            logger.info(f"Found {len(orphans)} orphaned files")

            return list(orphans)

        except Exception as e:
            logger.error(f"Failed to find orphans: {e}", exc_info=True)
            return []

    async def serve_file(self, file_id: int, db: AsyncSession) -> FileResponse:
        """
        Serve file for download/preview.

        Args:
            file_id: File ID
            db: Database session

        Returns:
            FileResponse: FastAPI file response

        Raises:
            HTTPException 404: File not found (DB or disk)
        """
        record = await self.get_async(file_id, db)

        # Check file exists on disk
        file_path = self.UPLOADS_DIR / record.file_path
        if not file_path.exists():
            logger.error(f"File missing on disk: {file_path}")
            raise HTTPException(
                status_code=404,
                detail="File not found on disk (orphaned record)"
            )

        # content_disposition_type="inline" → browser shows PDF in-page (not download)
        return FileResponse(
            path=str(file_path),
            media_type=record.mime_type,
            filename=record.original_filename,
            content_disposition_type="inline",
        )

    # ==================== PRIVATE HELPERS ====================

    def _detect_file_type(self, filename: str) -> str:
        """
        Detect file type from extension.

        Args:
            filename: Filename

        Returns:
            str: File type ("pdf", "step", "nc", "xlsx")

        Raises:
            HTTPException 400: Unsupported file type
        """
        ext = Path(filename).suffix.lower().lstrip('.')

        # Map extensions to types
        ext_map = {
            'pdf': 'pdf',
            'step': 'step',
            'stp': 'step',
            'nc': 'nc',
            'gcode': 'nc',
            'xlsx': 'xlsx',
        }

        file_type = ext_map.get(ext)
        if not file_type:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: .{ext}"
            )

        return file_type

    async def _validate_magic_bytes_upload(
        self,
        file: UploadFile,
        file_type: str
    ) -> None:
        """
        Validate magic bytes for uploaded file.

        Args:
            file: Uploaded file
            file_type: File type

        Raises:
            HTTPException 400: Invalid magic bytes
        """
        if file_type not in self.MAGIC_BYTES:
            # No magic bytes check for this type (e.g., nc, xlsx)
            return

        magic, num_bytes = self.MAGIC_BYTES[file_type]

        # Read magic bytes
        header = await file.read(num_bytes)
        if not header.startswith(magic):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {file_type.upper()} file (magic bytes check failed)"
            )

        # Reset file pointer
        await file.seek(0)

    def _validate_magic_bytes(self, file_path: Path, file_type: str) -> None:
        """
        Validate magic bytes for file on disk.

        Args:
            file_path: Path to file
            file_type: File type

        Raises:
            HTTPException 400: Invalid magic bytes
        """
        if file_type not in self.MAGIC_BYTES:
            return

        magic, num_bytes = self.MAGIC_BYTES[file_type]

        with file_path.open("rb") as f:
            header = f.read(num_bytes)

        if not header.startswith(magic):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {file_type.upper()} file (magic bytes check failed)"
            )

    async def _validate_file_size_upload(
        self,
        file: UploadFile,
        file_type: str
    ) -> int:
        """
        Validate file size for uploaded file (without loading into memory).

        Args:
            file: Uploaded file
            file_type: File type

        Returns:
            int: File size in bytes

        Raises:
            HTTPException 413: File too large
            HTTPException 400: Empty file
        """
        max_size = self.MAX_FILE_SIZES.get(file_type, self.DEFAULT_MAX_SIZE)

        # Seek to end to get size (file.file is sync, not async)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start

        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

        if file_size > max_size:
            max_mb = max_size / 1024 / 1024
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {max_mb:.0f}MB for {file_type})"
            )

        return file_size

    def _validate_file_size(self, file_path: Path, file_type: str) -> None:
        """
        Validate file size for file on disk.

        Args:
            file_path: Path to file
            file_type: File type

        Raises:
            HTTPException 413: File too large
        """
        max_size = self.MAX_FILE_SIZES.get(file_type, self.DEFAULT_MAX_SIZE)
        file_size = file_path.stat().st_size

        if file_size > max_size:
            max_mb = max_size / 1024 / 1024
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {max_mb:.0f}MB for {file_type})"
            )

    def _calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            str: Hex digest (64 characters)
        """
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            # Read in chunks to avoid memory issues with large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.

        Allows only: A-Z, a-z, 0-9, hyphen, underscore, dot, space
        Blocks: .., /, \\, and other special characters

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename

        Raises:
            HTTPException 400: Invalid filename
        """
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Block path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename (path traversal blocked)"
            )

        # Allow only safe characters
        # Pattern: alphanumeric, hyphen, underscore, dot, space
        safe_pattern = r'^[A-Za-z0-9_\-\.\s]+$'
        if not re.match(safe_pattern, filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid filename (contains unsafe characters)"
            )

        return filename

    def _ensure_directory(self, directory: str) -> Path:
        """
        Ensure directory exists under UPLOADS_DIR.

        Args:
            directory: Subdirectory path (e.g., "parts/10900635" or "loose")

        Returns:
            Path: Absolute path to directory
        """
        target_dir = self.UPLOADS_DIR / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir


# Singleton instance
file_service = FileService()
