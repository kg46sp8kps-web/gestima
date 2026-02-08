"""
File upload validation utilities
"""
from pathlib import Path
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# File size limits (in bytes)
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_STEP_SIZE = 100 * 1024 * 1024  # 100 MB (CAD files can be large)
MAX_SVG_SIZE = 5 * 1024 * 1024  # 5 MB

# Magic bytes for file type validation
MAGIC_BYTES = {
    'pdf': [b'%PDF'],
    'step': [b'ISO-10303'],
    'svg': [b'<?xml', b'<svg']
}


def validate_file(
    file_path: str,
    file_type: str,
    max_size: int = None
) -> Path:
    """
    Validate uploaded file for security and format.

    Args:
        file_path: Path to file
        file_type: Expected type ('pdf', 'step', 'svg')
        max_size: Max size in bytes (uses defaults if None)

    Returns:
        Path object if valid

    Raises:
        HTTPException: If validation fails
    """
    # Convert to Path and resolve (prevents path traversal)
    try:
        path = Path(file_path).resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as e:
        logger.error(f"File validation failed - path error: {e}")
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")

    # Check file exists
    if not path.exists():
        raise HTTPException(status_code=400, detail="File does not exist")

    if not path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check file size
    size_limits = {
        'pdf': MAX_PDF_SIZE,
        'step': MAX_STEP_SIZE,
        'svg': MAX_SVG_SIZE
    }

    max_size = max_size or size_limits.get(file_type, 10 * 1024 * 1024)
    file_size = path.stat().st_size

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f}MB). Max: {max_size / 1024 / 1024}MB"
        )

    # Validate magic bytes (file type)
    if file_type in MAGIC_BYTES:
        with open(path, 'rb') as f:
            header = f.read(100)  # Read first 100 bytes

            valid = any(magic in header for magic in MAGIC_BYTES[file_type])

            if not valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {file_type.upper()} file (magic bytes check failed)"
                )

    logger.info(f"File validated: {path.name} ({file_size} bytes)")
    return path
