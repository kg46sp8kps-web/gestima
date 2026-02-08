"""GESTIMA - STEP file support tests

Tests for STEP (.step, .stp) file upload support:
- File type detection
- STEP magic bytes validation
- File size limits (100MB for STEP vs 10MB for PDF)
"""

import pytest
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
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


@pytest.fixture
def valid_step_bytes():
    """Valid STEP file content (minimal STEP header)"""
    # Minimal valid STEP file with ISO-10303 magic bytes
    return b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('test'),'2;1');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;"


@pytest.fixture
def invalid_step_bytes():
    """Invalid STEP file content (fake extension attack)"""
    return b"This is not a STEP file, just text!"


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile"""
    def _create(filename="test.step", content=b"ISO-10303", content_type="application/step"):
        file = BytesIO(content)
        headers = Headers({"content-type": content_type})
        upload = UploadFile(file=file, filename=filename, headers=headers)
        return upload

    return _create


# ============================================================================
# FILE TYPE DETECTION TESTS
# ============================================================================

def test_detect_file_type_pdf(drawing_service):
    """Detect PDF from extension"""
    assert drawing_service.detect_file_type("drawing.pdf") == "pdf"
    assert drawing_service.detect_file_type("DRAWING.PDF") == "pdf"


def test_detect_file_type_step(drawing_service):
    """Detect STEP from extension"""
    assert drawing_service.detect_file_type("model.step") == "step"
    assert drawing_service.detect_file_type("model.stp") == "step"
    assert drawing_service.detect_file_type("MODEL.STEP") == "step"
    assert drawing_service.detect_file_type("MODEL.STP") == "step"


def test_detect_file_type_unsupported(drawing_service):
    """Reject unsupported file types"""
    with pytest.raises(Exception) as exc_info:
        drawing_service.detect_file_type("document.txt")
    assert exc_info.value.status_code == 400
    assert "unsupported" in str(exc_info.value.detail).lower()


# ============================================================================
# STEP VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_validate_step_success(drawing_service, valid_step_bytes):
    """Valid STEP file passes magic bytes check"""
    file = BytesIO(valid_step_bytes)
    headers = Headers({"content-type": "application/step"})
    upload = UploadFile(file=file, filename="test.step", headers=headers)

    # Should not raise exception
    await drawing_service.validate_step(upload)

    # File pointer should be reset to start
    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_step_invalid_extension(drawing_service, valid_step_bytes):
    """Reject file with invalid extension"""
    file = BytesIO(valid_step_bytes)
    headers = Headers({"content-type": "application/step"})
    upload = UploadFile(file=file, filename="test.txt", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_step(upload)

    assert exc_info.value.status_code == 400
    assert "extension" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_step_invalid_magic_bytes(drawing_service, invalid_step_bytes):
    """Reject file with invalid magic bytes"""
    file = BytesIO(invalid_step_bytes)
    headers = Headers({"content-type": "application/step"})
    upload = UploadFile(file=file, filename="test.step", headers=headers)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_step(upload)

    assert exc_info.value.status_code == 400
    assert "magic bytes" in str(exc_info.value.detail).lower()


# ============================================================================
# FILE SIZE LIMIT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_validate_file_size_step_within_limit(drawing_service, mock_upload_file):
    """STEP file under 100MB passes validation"""
    # Create 50MB STEP file (well under 100MB limit)
    content = b"ISO-10303" + b"x" * (50 * 1024 * 1024 - 9)
    file = mock_upload_file(filename="large.step", content=content)

    file_size = await drawing_service.validate_file_size(
        file,
        max_size=drawing_service.MAX_STEP_FILE_SIZE
    )

    assert file_size == len(content)


@pytest.mark.asyncio
async def test_validate_file_size_step_over_limit(drawing_service, mock_upload_file):
    """STEP file over 100MB fails validation"""
    # Create 101MB STEP file (over 100MB limit)
    content = b"ISO-10303" + b"x" * (101 * 1024 * 1024 - 9)
    file = mock_upload_file(filename="toolarge.step", content=content)

    with pytest.raises(Exception) as exc_info:
        await drawing_service.validate_file_size(
            file,
            max_size=drawing_service.MAX_STEP_FILE_SIZE
        )

    assert exc_info.value.status_code == 413
    assert "too large" in str(exc_info.value.detail).lower()


# ============================================================================
# CONSTANTS VERIFICATION
# ============================================================================

def test_step_constants(drawing_service):
    """Verify STEP file constants are defined correctly"""
    assert drawing_service.STEP_MAGIC == b"ISO-10303"
    assert drawing_service.STEP_EXTENSIONS == {'.step', '.stp'}
    assert drawing_service.PDF_EXTENSIONS == {'.pdf'}
    assert drawing_service.MAX_STEP_FILE_SIZE == 100 * 1024 * 1024  # 100MB
    assert drawing_service.MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB
