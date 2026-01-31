"""GESTIMA - Drawing file management service

Security-focused service for handling PDF drawing uploads:
- Magic bytes validation (not just MIME type)
- Path traversal prevention
- File size limits
- Temp file cleanup
"""

import logging
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


class DrawingService:
    """Service for managing part drawing files"""

    # Configuration
    DRAWINGS_DIR = Path("drawings")
    TEMP_DIR = DRAWINGS_DIR / "temp"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    TEMP_EXPIRY_HOURS = 24
    PDF_MAGIC_BYTES = b"%PDF"

    def __init__(self):
        """Initialize service and ensure directories exist"""
        self.DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ==================== VALIDATION ====================

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

    async def validate_file_size(self, file: UploadFile) -> int:
        """
        Validate file size without loading entire file into memory.

        Returns:
            int: File size in bytes

        Raises:
            HTTPException 413: File too large
        """
        # Seek to end to get size (file.file is sync, not async)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start

        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
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
