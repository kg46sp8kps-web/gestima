"""GESTIMA - Drawing upload tests

Security-focused tests for PDF drawing upload system:
- Magic bytes validation
- Path traversal prevention
- File size limits
- Temp file lifecycle
- Transaction handling
"""

import pytest
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO

from fastapi import UploadFile
from httpx import AsyncClient
from starlette.datastructures import Headers

from app.services.drawing_service import DrawingService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def drawing_service():
    """Create DrawingService instance"""
    service = DrawingService()
    yield service
    # Cleanup test files after each test
    if service.TEMP_DIR.exists():
        for file in service.TEMP_DIR.glob("*.pdf"):
            file.unlink()


@pytest.fixture
def valid_pdf_bytes():
    """Valid PDF file content (minimal PDF)"""
    # Minimal valid PDF (just header + trailer)
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n>>\n%%EOF"


@pytest.fixture
def invalid_pdf_bytes():
    """Invalid PDF file content (fake extension attack)"""
    return b"This is not a PDF file, just text!"


@pytest.fixture
def mock_upload_file(valid_pdf_bytes):
    """Create mock UploadFile with valid PDF"""
    def _create(filename="test.pdf", content=None, content_type="application/pdf"):
        if content is None:
            content = valid_pdf_bytes

        file = BytesIO(content)
        # UploadFile extracts content_type from headers
        headers = Headers({"content-type": content_type})
        upload = UploadFile(file=file, filename=filename, headers=headers)
        return upload

    return _create


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_validate_pdf_success(drawing_service, mock_upload_file):
    """Valid PDF passes magic bytes check"""
    file = mock_upload_file()

    # Should not raise exception
    await drawing_service.validate_pdf(file)

    # File pointer should be reset to start
    assert file.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_pdf_invalid_extension(drawing_service, valid_pdf_bytes):
    """Reject file with invalid extension"""
    file = BytesIO(valid_pdf_bytes)
    headers = Headers({"content-type": "application/pdf"})
    upload = UploadFile(file=file, filename="test.txt", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_pdf(upload)

    assert exc_info.value.status_code == 400
    assert "extension" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_pdf_invalid_content_type(drawing_service, valid_pdf_bytes):
    """Reject file with invalid Content-Type"""
    file = BytesIO(valid_pdf_bytes)
    headers = Headers({"content-type": "text/plain"})
    upload = UploadFile(file=file, filename="test.pdf", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_pdf(upload)

    assert exc_info.value.status_code == 400
    assert "content type" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_pdf_magic_bytes_check(drawing_service, invalid_pdf_bytes):
    """SECURITY: Reject file with invalid magic bytes (even if extension/MIME OK)"""
    file = BytesIO(invalid_pdf_bytes)
    headers = Headers({"content-type": "application/pdf"})
    upload = UploadFile(file=file, filename="test.pdf", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_pdf(upload)

    assert exc_info.value.status_code == 400
    assert "magic bytes" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_file_size_success(drawing_service, mock_upload_file):
    """Valid file size passes check"""
    file = mock_upload_file()

    file_size = await drawing_service.validate_file_size(file)

    assert file_size > 0
    assert file_size <= drawing_service.MAX_FILE_SIZE
    # File pointer should be reset
    assert file.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_file_size_too_large(drawing_service):
    """SECURITY: Reject file exceeding size limit"""
    # Create 11MB file (exceeds 10MB limit)
    large_content = b"%PDF-1.4\n" + b"X" * (11 * 1024 * 1024)
    file = BytesIO(large_content)
    headers = Headers({"content-type": "application/pdf"})
    upload = UploadFile(file=file, filename="huge.pdf", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_file_size(upload)

    assert exc_info.value.status_code == 413
    assert "too large" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_file_size_empty(drawing_service):
    """Reject empty file"""
    file = BytesIO(b"")
    headers = Headers({"content-type": "application/pdf"})
    upload = UploadFile(file=file, filename="empty.pdf", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_file_size(upload)

    assert exc_info.value.status_code == 400
    assert "empty" in str(exc_info.value.detail).lower()


def test_sanitize_part_number_success(drawing_service):
    """Valid part numbers pass sanitization"""
    valid_numbers = [
        "10123456",
        "PART-001",
        "ABC_123",
        "test-part_v2"
    ]

    for part_number in valid_numbers:
        result = drawing_service.sanitize_part_number(part_number)
        assert result == part_number


def test_sanitize_part_number_path_traversal(drawing_service):
    """SECURITY: Block path traversal attempts"""
    malicious_inputs = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "part/../../../secret",
        "part/../../data",
        "../../uploads/temp/secret.pdf"
    ]

    for malicious in malicious_inputs:
        with pytest.raises(Exception) as exc_info:
            drawing_service.sanitize_part_number(malicious)

        assert exc_info.value.status_code == 400
        assert "invalid" in str(exc_info.value.detail).lower()


def test_sanitize_part_number_special_chars(drawing_service):
    """SECURITY: Block special characters"""
    invalid_inputs = [
        "part; rm -rf /",
        "part | cat /etc/passwd",
        "part && echo hacked",
        "part<script>alert('xss')</script>",
        "../../secret"
    ]

    for invalid in invalid_inputs:
        with pytest.raises(Exception) as exc_info:
            drawing_service.sanitize_part_number(invalid)

        assert exc_info.value.status_code == 400


# ============================================================================
# TEMP FILE OPERATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_save_temp_success(drawing_service, mock_upload_file):
    """Save temp file successfully"""
    file = mock_upload_file()
    temp_id = str(uuid.uuid4())

    temp_path, file_size = await drawing_service.save_temp(file, temp_id)

    # Verify file created
    assert temp_path.exists()
    assert temp_path.name == f"{temp_id}.pdf"
    assert file_size > 0

    # Cleanup
    temp_path.unlink()


@pytest.mark.asyncio
async def test_move_temp_to_permanent_success(drawing_service, mock_upload_file):
    """Move temp file to permanent storage"""
    file = mock_upload_file()
    temp_id = str(uuid.uuid4())
    part_number = "10123456"

    # Create temp file
    temp_path, _ = await drawing_service.save_temp(file, temp_id)
    assert temp_path.exists()

    # Move to permanent
    permanent_path = await drawing_service.move_temp_to_permanent(temp_id, part_number)

    # Verify
    assert permanent_path == f"drawings/{part_number}.pdf"
    assert not temp_path.exists()  # Temp file should be gone
    assert (drawing_service.DRAWINGS_DIR / f"{part_number}.pdf").exists()

    # Cleanup
    (drawing_service.DRAWINGS_DIR / f"{part_number}.pdf").unlink()


@pytest.mark.asyncio
async def test_move_temp_to_permanent_not_found(drawing_service):
    """Fail gracefully when temp file missing"""
    temp_id = str(uuid.uuid4())
    part_number = "10123456"

    with pytest.raises(Exception) as exc_info:
        await drawing_service.move_temp_to_permanent(temp_id, part_number)

    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail).lower()


# ============================================================================
# PERMANENT FILE OPERATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_save_permanent_success(drawing_service, mock_upload_file):
    """Save file directly to permanent storage"""
    file = mock_upload_file()
    part_number = "10123456"

    drawing_path, file_size = await drawing_service.save_permanent(file, part_number)

    # Verify
    assert drawing_path == f"drawings/{part_number}.pdf"
    assert file_size > 0
    assert (drawing_service.DRAWINGS_DIR / f"{part_number}.pdf").exists()

    # Cleanup
    (drawing_service.DRAWINGS_DIR / f"{part_number}.pdf").unlink()


def test_get_drawing_path_success(drawing_service, valid_pdf_bytes):
    """Get path to existing drawing"""
    part_number = "10123456"

    # Create test file
    test_path = drawing_service.DRAWINGS_DIR / f"{part_number}.pdf"
    test_path.write_bytes(valid_pdf_bytes)

    # Get path
    result = drawing_service.get_drawing_path(part_number)

    assert result == test_path
    assert result.exists()

    # Cleanup
    test_path.unlink()


def test_get_drawing_path_not_found(drawing_service):
    """Fail when drawing doesn't exist"""
    part_number = "99999999"

    with pytest.raises(Exception) as exc_info:
        drawing_service.get_drawing_path(part_number)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_drawing_success(drawing_service, valid_pdf_bytes):
    """Delete drawing file"""
    part_number = "10123456"

    # Create test file
    test_path = drawing_service.DRAWINGS_DIR / f"{part_number}.pdf"
    test_path.write_bytes(valid_pdf_bytes)
    assert test_path.exists()

    # Delete
    await drawing_service.delete_drawing(part_number)

    # Verify deleted
    assert not test_path.exists()


@pytest.mark.asyncio
async def test_delete_drawing_not_found(drawing_service):
    """Fail when trying to delete non-existent drawing"""
    part_number = "99999999"

    with pytest.raises(Exception) as exc_info:
        await drawing_service.delete_drawing(part_number)

    assert exc_info.value.status_code == 404


# ============================================================================
# CLEANUP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_expired_temp_files(drawing_service, valid_pdf_bytes):
    """Delete temp files older than 24h"""
    # Create old temp file (simulate 25h old)
    old_file = drawing_service.TEMP_DIR / f"{uuid.uuid4()}.pdf"
    old_file.write_bytes(valid_pdf_bytes)

    # Modify mtime to 25 hours ago
    old_time = datetime.now() - timedelta(hours=25)
    old_timestamp = old_time.timestamp()
    old_file.touch()
    import os
    os.utime(old_file, (old_timestamp, old_timestamp))

    # Create fresh file (1 hour old)
    fresh_file = drawing_service.TEMP_DIR / f"{uuid.uuid4()}.pdf"
    fresh_file.write_bytes(valid_pdf_bytes)

    # Run cleanup
    deleted_count = await drawing_service.cleanup_expired_temp_files()

    # Verify
    assert deleted_count == 1
    assert not old_file.exists()  # Old file deleted
    assert fresh_file.exists()    # Fresh file kept

    # Cleanup
    fresh_file.unlink()


@pytest.mark.asyncio
async def test_cleanup_no_expired_files(drawing_service, valid_pdf_bytes):
    """Cleanup when no expired files"""
    # Create fresh file
    fresh_file = drawing_service.TEMP_DIR / f"{uuid.uuid4()}.pdf"
    fresh_file.write_bytes(valid_pdf_bytes)

    # Run cleanup
    deleted_count = await drawing_service.cleanup_expired_temp_files()

    # Verify
    assert deleted_count == 0
    assert fresh_file.exists()

    # Cleanup
    fresh_file.unlink()


# ============================================================================
# INTEGRATION TESTS (require test client + DB)
# ============================================================================

# NOTE: These tests require pytest-asyncio and test database setup
# Run with: pytest tests/test_drawings.py -v

# TODO: Add integration tests with actual HTTP requests:
# - POST /api/uploads/temp (temp upload)
# - POST /api/parts/{part_number}/drawing (permanent upload)
# - GET /api/parts/{part_number}/drawing (download)
# - DELETE /api/parts/{part_number}/drawing (delete)
# - POST /api/parts with temp_drawing_id (create with drawing)
