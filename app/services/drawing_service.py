"""GESTIMA - Drawing file management service

Security-focused service for handling PDF drawing uploads:
- Magic bytes validation (not just MIME type)
- Path traversal prevention
- File size limits
- Temp file cleanup
"""

import hashlib
import logging
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DrawingService:
    """Service for managing part drawing files"""

    # Configuration
    DRAWINGS_DIR = Path("drawings")
    TEMP_DIR = DRAWINGS_DIR / "temp"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_STEP_FILE_SIZE = 100 * 1024 * 1024  # 100MB for STEP files
    TEMP_EXPIRY_HOURS = 24
    PDF_MAGIC_BYTES = b"%PDF"
    STEP_MAGIC = b"ISO-10303"
    STEP_EXTENSIONS = {'.step', '.stp'}
    PDF_EXTENSIONS = {'.pdf'}

    def __init__(self):
        """Initialize service and ensure directories exist"""
        self.DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ==================== VALIDATION ====================

    def detect_file_type(self, filename: str) -> str:
        """
        Detect file type from filename extension.

        Args:
            filename: Name of file

        Returns:
            str: "pdf" or "step"

        Raises:
            HTTPException 400: Unsupported file type
        """
        ext = Path(filename).suffix.lower()

        if ext in self.PDF_EXTENSIONS:
            return "pdf"
        elif ext in self.STEP_EXTENSIONS:
            return "step"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Only PDF and STEP files are allowed."
            )

    async def validate_pdf(self, file: UploadFile) -> None:
        """
        Validate PDF file using magic bytes (security-critical).

        Checks:
        1. Filename extension
        2. Content-Type header
        3. Magic bytes (%PDF in first 4 bytes)

        Raises:
            HTTPException 400: Invalid file type
        """
        # Check filename extension
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed (invalid extension)"
            )

        # Check Content-Type header
        if not file.content_type or file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed (invalid content type)"
            )

        # Check magic bytes (most important!)
        header = await file.read(4)
        if not header.startswith(self.PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file (magic bytes check failed)"
            )

        # Reset file pointer for further processing
        await file.seek(0)

    async def validate_step(self, file: UploadFile) -> None:
        """
        Validate STEP file using magic bytes (security-critical).

        Checks:
        1. Filename extension (.step or .stp)
        2. Magic bytes (ISO-10303 in first 20 bytes)

        Raises:
            HTTPException 400: Invalid file type
        """
        # Check filename extension
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )

        ext = Path(file.filename).suffix.lower()
        if ext not in self.STEP_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Only STEP files are allowed (invalid extension: {ext})"
            )

        # Check magic bytes (ISO-10303 standard identifier)
        header = await file.read(20)
        if not header.startswith(self.STEP_MAGIC):
            raise HTTPException(
                status_code=400,
                detail="Invalid STEP file (magic bytes check failed)"
            )

        # Reset file pointer for further processing
        await file.seek(0)

    async def validate_file_size(self, file: UploadFile, max_size: Optional[int] = None) -> int:
        """
        Validate file size without loading entire file into memory.

        Args:
            file: Uploaded file
            max_size: Maximum file size in bytes (defaults to MAX_FILE_SIZE)

        Returns:
            int: File size in bytes

        Raises:
            HTTPException 413: File too large
        """
        if max_size is None:
            max_size = self.MAX_FILE_SIZE

        # Seek to end to get size (file.file is sync, not async)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start

        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {max_size / 1024 / 1024:.0f}MB)"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file not allowed"
            )

        return file_size

    def sanitize_part_number(self, part_number: str) -> str:
        """
        Sanitize part number to prevent path traversal attacks.

        Allows only: A-Z, a-z, 0-9, hyphen, underscore
        Blocks: .., /, \\, and other special characters

        Raises:
            HTTPException 400: Invalid part number format
        """
        if not part_number:
            raise HTTPException(status_code=400, detail="Part number is required")

        # Allow only alphanumeric, hyphen, underscore (8 chars for GESTIMA format)
        if not re.match(r'^[A-Za-z0-9_-]{1,50}$', part_number):
            raise HTTPException(
                status_code=400,
                detail="Invalid part number format (security violation)"
            )

        # Extra check: block path traversal attempts
        if ".." in part_number or "/" in part_number or "\\" in part_number:
            raise HTTPException(
                status_code=400,
                detail="Invalid part number (path traversal blocked)"
            )

        return part_number

    # ==================== TEMP FILE OPERATIONS ====================

    async def save_temp(
        self,
        file: UploadFile,
        temp_id: str
    ) -> tuple[Path, int]:
        """
        Save file to temporary storage (already implemented in uploads_router).

        This method is here for consistency but actual implementation
        is in uploads_router.py for backwards compatibility.

        Returns:
            tuple[Path, int]: (file_path, file_size)
        """
        # Validate
        await self.validate_pdf(file)
        file_size = await self.validate_file_size(file)

        # Save to temp directory
        temp_path = self.TEMP_DIR / f"{temp_id}.pdf"

        try:
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info(f"Saved temp file: {temp_id} ({file_size} bytes)")
            return temp_path, file_size

        except Exception as e:
            logger.error(f"Failed to save temp file {temp_id}: {e}", exc_info=True)
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(status_code=500, detail="Failed to save temporary file")

    async def move_temp_to_permanent(
        self,
        temp_id: str,
        part_number: str
    ) -> str:
        """
        Move temp file to permanent storage.

        Args:
            temp_id: UUID of temp file
            part_number: Sanitized part number

        Returns:
            str: Relative path to permanent file (e.g., "drawings/10123456.pdf")

        Raises:
            HTTPException 404: Temp file not found
            HTTPException 500: Move operation failed
        """
        # Sanitize part number (security!)
        safe_part_number = self.sanitize_part_number(part_number)

        # Check temp file exists
        temp_path = self.TEMP_DIR / f"{temp_id}.pdf"
        if not temp_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Temporary file not found: {temp_id}"
            )

        # Permanent path
        permanent_path = self.DRAWINGS_DIR / f"{safe_part_number}.pdf"

        try:
            # Move file (atomic operation on same filesystem)
            shutil.move(str(temp_path), str(permanent_path))

            logger.info(f"Moved temp file {temp_id} → {permanent_path}")

            # Return relative path for database storage
            return f"drawings/{safe_part_number}.pdf"

        except Exception as e:
            logger.error(f"Failed to move temp file {temp_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to move temporary file to permanent storage"
            )

    # ==================== PERMANENT FILE OPERATIONS ====================

    async def save_permanent(
        self,
        file: UploadFile,
        part_number: str
    ) -> tuple[str, int]:
        """
        Save file directly to permanent storage (skip temp).

        Args:
            file: Uploaded file
            part_number: Part number (will be sanitized)

        Returns:
            tuple[str, int]: (relative_path, file_size)

        Raises:
            HTTPException: Various validation/save errors
        """
        # Validate
        await self.validate_pdf(file)
        file_size = await self.validate_file_size(file)

        # Sanitize part number
        safe_part_number = self.sanitize_part_number(part_number)

        # Permanent path
        permanent_path = self.DRAWINGS_DIR / f"{safe_part_number}.pdf"

        try:
            with permanent_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info(f"Saved permanent drawing: {safe_part_number} ({file_size} bytes)")

            return f"drawings/{safe_part_number}.pdf", file_size

        except Exception as e:
            logger.error(f"Failed to save permanent file {safe_part_number}: {e}", exc_info=True)
            if permanent_path.exists():
                permanent_path.unlink()
            raise HTTPException(status_code=500, detail="Failed to save drawing file")

    def get_drawing_path(self, part_number: str) -> Path:
        """
        Get absolute path to drawing file.

        Args:
            part_number: Part number (will be sanitized)

        Returns:
            Path: Absolute path to drawing file

        Raises:
            HTTPException 404: Drawing not found
        """
        safe_part_number = self.sanitize_part_number(part_number)
        drawing_path = self.DRAWINGS_DIR / f"{safe_part_number}.pdf"

        if not drawing_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Drawing not found for part: {part_number}"
            )

        return drawing_path

    async def delete_drawing(self, part_number: str) -> None:
        """
        Delete permanent drawing file.

        Args:
            part_number: Part number (will be sanitized)

        Raises:
            HTTPException 404: Drawing not found
        """
        safe_part_number = self.sanitize_part_number(part_number)
        drawing_path = self.DRAWINGS_DIR / f"{safe_part_number}.pdf"

        if not drawing_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Drawing not found for part: {part_number}"
            )

        try:
            drawing_path.unlink()
            logger.info(f"Deleted drawing: {safe_part_number}")

        except Exception as e:
            logger.error(f"Failed to delete drawing {safe_part_number}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete drawing file")

    # ==================== CLEANUP ====================

    async def cleanup_expired_temp_files(self) -> int:
        """
        Delete temporary files older than TEMP_EXPIRY_HOURS.

        Returns:
            int: Number of files deleted
        """
        if not self.TEMP_DIR.exists():
            return 0

        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=self.TEMP_EXPIRY_HOURS)

        try:
            for temp_file in self.TEMP_DIR.glob("*.pdf"):
                # Check file modification time
                mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)

                if mtime < cutoff_time:
                    temp_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted expired temp file: {temp_file.name}")

            if deleted_count > 0:
                logger.info(f"Cleanup: deleted {deleted_count} expired temp files")

            return deleted_count

        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}", exc_info=True)
            return deleted_count

    # ==================== MULTIPLE DRAWINGS SUPPORT ====================

    async def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file for deduplication.

        Args:
            file_path: Path to file

        Returns:
            str: Hex digest of SHA-256 hash (64 characters)
        """
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            # Read file in chunks to avoid memory issues with large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def save_drawing_record(
        self,
        part_id: int,
        file_path: str,
        filename: str,
        file_size: int,
        file_hash: str,
        is_primary: bool,
        revision: str,
        created_by: str,
        db: AsyncSession,
        file_type: str = "pdf"
    ) -> "Drawing":
        """
        Create Drawing record in database.

        Transaction handling (L-008):
        - Check duplicate hash (HTTP 409 if exists)
        - If is_primary=True, unset others
        - Create record
        - Commit handled by caller

        Args:
            part_id: ID dílu
            file_path: Relativní cesta k souboru
            filename: Původní název souboru
            file_size: Velikost v bytech
            file_hash: SHA-256 hash
            is_primary: Primární výkres?
            revision: Revize výkresu
            created_by: Username uživatele
            db: Database session

        Returns:
            Drawing: Vytvořený záznam

        Raises:
            HTTPException 409: Duplicate hash (file already exists)
            HTTPException 500: Database error
        """
        from app.models.drawing import Drawing

        try:
            # Check duplicate hash (scoped to this part only)
            result = await db.execute(
                select(Drawing).where(
                    Drawing.file_hash == file_hash,
                    Drawing.part_id == part_id,  # Same file can exist for different parts
                    Drawing.deleted_at.is_(None)
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.warning(f"Duplicate file hash detected for part {part_id}: {file_hash}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Tento soubor již existuje u tohoto dílu (výkres ID {existing.id})"
                )

            # If is_primary=True, unset others for this part (same file_type only)
            if is_primary:
                await db.execute(
                    update(Drawing)
                    .where(
                        Drawing.part_id == part_id,
                        Drawing.file_type == file_type,
                        Drawing.deleted_at.is_(None)
                    )
                    .values(is_primary=False, updated_at=datetime.utcnow())
                )
                logger.info(f"Unset is_primary for {file_type} drawings of part_id={part_id}")

            # Create new drawing record
            drawing = Drawing(
                part_id=part_id,
                file_path=file_path,
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                is_primary=is_primary,
                revision=revision,
                file_type=file_type,
                created_by=created_by,
                updated_by=created_by
            )
            db.add(drawing)
            await db.flush()  # Get ID without committing

            logger.info(
                f"Created drawing record: ID={drawing.id}, part_id={part_id}, "
                f"filename='{filename}', primary={is_primary}, revision={revision}"
            )

            return drawing

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create drawing record: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chyba při vytváření záznamu výkresu")

    async def set_primary_drawing(
        self,
        drawing_id: int,
        db: AsyncSession
    ) -> "Drawing":
        """
        Set drawing as primary, unset others for same part.

        Transaction handling (L-008):
        - Get drawing (404 if not found)
        - Unset is_primary for all drawings in same part
        - Set is_primary=True for this drawing
        - Commit handled by caller

        Args:
            drawing_id: ID výkresu
            db: Database session

        Returns:
            Drawing: Aktualizovaný výkres

        Raises:
            HTTPException 404: Drawing not found
            HTTPException 400: Drawing is soft-deleted
            HTTPException 500: Database error
        """
        from app.models.drawing import Drawing

        try:
            # Get drawing
            result = await db.execute(
                select(Drawing).where(Drawing.id == drawing_id)
            )
            drawing = result.scalar_one_or_none()

            if not drawing:
                raise HTTPException(status_code=404, detail="Výkres nebyl nalezen")

            if drawing.deleted_at is not None:
                raise HTTPException(status_code=400, detail="Nelze nastavit smazaný výkres jako primární")

            # Already primary? No-op
            if drawing.is_primary:
                logger.debug(f"Drawing {drawing_id} is already primary")
                return drawing

            # Unset is_primary for drawings in same part + same file_type
            await db.execute(
                update(Drawing)
                .where(
                    Drawing.part_id == drawing.part_id,
                    Drawing.file_type == drawing.file_type,
                    Drawing.deleted_at.is_(None)
                )
                .values(is_primary=False, updated_at=datetime.utcnow())
            )

            # Set this drawing as primary
            drawing.is_primary = True
            drawing.updated_at = datetime.utcnow()
            drawing.version += 1

            logger.info(
                f"Set drawing {drawing_id} as primary (part_id={drawing.part_id}, "
                f"filename='{drawing.filename}')"
            )

            return drawing

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to set primary drawing {drawing_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chyba při nastavování primárního výkresu")

    async def get_primary_drawing(
        self,
        part_id: int,
        db: AsyncSession,
        file_type: str = "pdf"
    ) -> Optional["Drawing"]:
        """
        Get primary drawing for part (filtered by file_type).

        Args:
            part_id: ID dílu
            db: Database session
            file_type: File type to filter ("pdf" or "step")

        Returns:
            Drawing | None: Primární výkres nebo None
        """
        from app.models.drawing import Drawing

        try:
            result = await db.execute(
                select(Drawing)
                .where(
                    Drawing.part_id == part_id,
                    Drawing.file_type == file_type,
                    Drawing.is_primary == True,
                    Drawing.deleted_at.is_(None)
                )
                .order_by(Drawing.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get primary drawing for part {part_id}: {e}", exc_info=True)
            return None

    async def auto_promote_primary(
        self,
        part_id: int,
        db: AsyncSession,
        file_type: str = "pdf"
    ) -> Optional["Drawing"]:
        """
        Auto-promote oldest non-deleted drawing of same file_type to primary.
        Called after primary drawing deletion.

        Args:
            part_id: ID dílu
            db: Database session
            file_type: File type to promote within ("pdf" or "step")

        Returns:
            Drawing | None: Newly promoted drawing or None if no drawings left

        Raises:
            HTTPException 500: Database error
        """
        from app.models.drawing import Drawing

        try:
            # Find oldest non-deleted drawing of same file_type
            result = await db.execute(
                select(Drawing)
                .where(
                    Drawing.part_id == part_id,
                    Drawing.file_type == file_type,
                    Drawing.deleted_at.is_(None)
                )
                .order_by(Drawing.created_at.asc())
                .limit(1)
            )
            drawing = result.scalar_one_or_none()

            if not drawing:
                logger.debug(f"No drawings left for part {part_id} after delete")
                return None

            # Promote to primary
            drawing.is_primary = True
            drawing.updated_at = datetime.utcnow()
            drawing.version += 1

            logger.info(
                f"Auto-promoted drawing {drawing.id} to primary "
                f"(part_id={part_id}, filename='{drawing.filename}')"
            )

            return drawing

        except Exception as e:
            logger.error(f"Failed to auto-promote primary for part {part_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chyba při automatickém povýšení primárního výkresu")
