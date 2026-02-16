"""Tests for FileService (ADR-044)

Tests:
- store() - happy path
- store() - magic bytes validation
- store() - file size validation
- store() - DB rollback on failure
- link() - create link
- link() - UPSERT existing link
- link() - set primary (unset others)
- unlink() - soft delete
- delete() - soft delete FileRecord
- get_files_for_entity() - JOIN query
- get_primary() - primary file lookup
- cleanup_temp() - expire temp files
- find_orphans() - files without links
"""


import hashlib
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.file_record import FileRecord, FileLink
from app.services.file_service import file_service


@pytest_asyncio.fixture
async def db():
    """Create fresh in-memory database for each test."""
    # Create in-memory SQLite engine for each test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Create and yield session
    async with AsyncSessionLocal() as session:
        yield session
    
    # Clean up engine
    await engine.dispose()

@pytest.fixture
def temp_uploads_dir(tmp_path):
    """Temporary uploads directory."""
    original_dir = file_service.UPLOADS_DIR
    file_service.UPLOADS_DIR = tmp_path
    yield tmp_path
    file_service.UPLOADS_DIR = original_dir


def create_pdf_upload(filename: str = "test.pdf") -> UploadFile:
    """Create a fake PDF UploadFile with magic bytes."""
    content = b"%PDF-1.4\n%Test PDF content"
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj)


def create_step_upload(filename: str = "test.step") -> UploadFile:
    """Create a fake STEP UploadFile with magic bytes."""
    content = b"ISO-10303-21;HEADER;ENDSEC;DATA;ENDSEC;END-ISO-10303-21;"
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj)


# ==================== STORE TESTS ====================

@pytest.mark.asyncio
async def test_store_pdf_happy_path(db, temp_uploads_dir):
    """Test store() - PDF upload happy path."""
    file = create_pdf_upload("test_drawing.pdf")

    record = await file_service.store(
        file=file,
        directory="parts/10900635",
        db=db,
        created_by="test_user"
    )

    # Check DB record
    assert record.id is not None
    assert record.file_type == "pdf"
    assert record.mime_type == "application/pdf"
    assert record.original_filename == "test_drawing.pdf"
    assert record.file_size > 0
    assert record.status == "active"
    assert record.created_by == "test_user"
    assert len(record.file_hash) == 64  # SHA-256 hex digest

    # Check file on disk
    file_path = temp_uploads_dir / record.file_path
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"%PDF")


@pytest.mark.asyncio
async def test_store_step_happy_path(db, temp_uploads_dir):
    """Test store() - STEP upload happy path."""
    file = create_step_upload("model.step")

    record = await file_service.store(
        file=file,
        directory="parts/10900635",
        db=db,
        allowed_types=["step"]
    )

    assert record.file_type == "step"
    assert record.mime_type == "application/step"

    file_path = temp_uploads_dir / record.file_path
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"ISO-10303")


@pytest.mark.asyncio
async def test_store_invalid_magic_bytes(db, temp_uploads_dir):
    """Test store() - reject file with invalid magic bytes."""
    # Create file with .pdf extension but non-PDF content
    content = b"This is not a PDF file"
    file_obj = BytesIO(content)
    file = UploadFile(filename="fake.pdf", file=file_obj)

    with pytest.raises(HTTPException) as exc_info:
        await file_service.store(file=file, directory="test", db=db)

    assert exc_info.value.status_code == 400
    assert "magic bytes" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_store_file_too_large(db, temp_uploads_dir):
    """Test store() - reject file exceeding size limit."""
    # Create file larger than 10MB PDF limit
    large_content = b"%PDF-1.4\n" + (b"x" * (11 * 1024 * 1024))
    file_obj = BytesIO(large_content)
    file = UploadFile(filename="large.pdf", file=file_obj)

    with pytest.raises(HTTPException) as exc_info:
        await file_service.store(file=file, directory="test", db=db)

    assert exc_info.value.status_code == 413
    assert "too large" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_store_allowed_types_filter(db, temp_uploads_dir):
    """Test store() - allowed_types filter."""
    file = create_pdf_upload()

    # PDF not in allowed_types
    with pytest.raises(HTTPException) as exc_info:
        await file_service.store(
            file=file,
            directory="test",
            db=db,
            allowed_types=["step"]
        )

    assert exc_info.value.status_code == 400
    assert "not allowed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_store_duplicate_filename(db, temp_uploads_dir):
    """Test store() - handle duplicate filename with UUID suffix."""
    file1 = create_pdf_upload("duplicate.pdf")
    file2 = create_pdf_upload("duplicate.pdf")

    record1 = await file_service.store(file=file1, directory="test", db=db)
    record2 = await file_service.store(file=file2, directory="test", db=db)

    # Different paths due to UUID suffix
    assert record1.file_path != record2.file_path
    assert "duplicate_" in record2.file_path  # UUID suffix added


# ==================== LINK TESTS ====================

@pytest.mark.asyncio
async def test_link_create(db, temp_uploads_dir):
    """Test link() - create new link."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="test", db=db)

    link = await file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db,
        is_primary=True,
        revision="A",
        created_by="test_user"
    )

    assert link.file_id == record.id
    assert link.entity_type == "part"
    assert link.entity_id == 123
    assert link.is_primary is True
    assert link.revision == "A"
    assert link.link_type == "drawing"


@pytest.mark.asyncio
async def test_link_upsert(db, temp_uploads_dir):
    """Test link() - UPSERT existing link."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="test", db=db)

    # Create initial link
    link1 = await file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db,
        revision="A"
    )
    link1_id = link1.id

    # UPSERT same link with different revision
    link2 = await file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db,
        revision="B",
        is_primary=True
    )

    # Same ID (updated, not created)
    assert link2.id == link1_id
    assert link2.revision == "B"
    assert link2.is_primary is True


@pytest.mark.asyncio
async def test_link_set_primary_unsets_others(db, temp_uploads_dir):
    """Test link() - setting primary unsets other primary links."""
    file1 = create_pdf_upload("file1.pdf")
    file2 = create_pdf_upload("file2.pdf")
    record1 = await file_service.store(file=file1, directory="test", db=db)
    record2 = await file_service.store(file=file2, directory="test", db=db)

    # Link file1 as primary
    link1 = await file_service.link(
        file_id=record1.id,
        entity_type="part",
        entity_id=123,
        db=db,
        is_primary=True
    )
    await db.commit()

    # Link file2 as primary (should unset link1)
    link2 = await file_service.link(
        file_id=record2.id,
        entity_type="part",
        entity_id=123,
        db=db,
        is_primary=True
    )
    await db.commit()

    # Refresh link1 from DB
    await db.refresh(link1)
    assert link1.is_primary is False
    assert link2.is_primary is True


# ==================== UNLINK / DELETE TESTS ====================

@pytest.mark.asyncio
async def test_unlink_soft_delete(db, temp_uploads_dir):
    """Test unlink() - soft delete FileLink."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="test", db=db)
    link = await file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db
    )
    await db.commit()

    # Unlink
    await file_service.unlink(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db
    )
    await db.commit()

    # Check soft delete
    await db.refresh(link)
    assert link.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_soft_delete_record(db, temp_uploads_dir):
    """Test delete() - soft delete FileRecord."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="test", db=db)
    await db.commit()
    record_id = record.id

    # Delete
    await file_service.delete(file_id=record_id, db=db)
    await db.commit()

    # Check soft delete
    await db.refresh(record)
    assert record.deleted_at is not None

    # File still on disk (safety)
    file_path = temp_uploads_dir / record.file_path
    assert file_path.exists()


# ==================== QUERY HELPER TESTS ====================

@pytest.mark.asyncio
async def test_get_files_for_entity(db, temp_uploads_dir):
    """Test get_files_for_entity() - JOIN query."""
    file1 = create_pdf_upload("file1.pdf")
    file2 = create_pdf_upload("file2.pdf")
    record1 = await file_service.store(file=file1, directory="test", db=db)
    record2 = await file_service.store(file=file2, directory="test", db=db)

    await file_service.link(record1.id, "part", 123, db)
    await file_service.link(record2.id, "part", 123, db)

    files = await file_service.get_files_for_entity("part", 123, db)

    assert len(files) == 2
    assert record1.id in [f.id for f in files]
    assert record2.id in [f.id for f in files]


@pytest.mark.asyncio
async def test_get_primary(db, temp_uploads_dir):
    """Test get_primary() - primary file lookup."""
    file1 = create_pdf_upload("file1.pdf")
    file2 = create_pdf_upload("file2.pdf")
    record1 = await file_service.store(file=file1, directory="test", db=db)
    record2 = await file_service.store(file=file2, directory="test", db=db)

    await file_service.link(record1.id, "part", 123, db, is_primary=False)
    await file_service.link(record2.id, "part", 123, db, is_primary=True)

    primary = await file_service.get_primary("part", 123, db)

    assert primary is not None
    assert primary.id == record2.id


# ==================== CLEANUP TESTS ====================

@pytest.mark.asyncio
async def test_cleanup_temp_expired(db, temp_uploads_dir):
    """Test cleanup_temp() - delete expired temp files."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="temp", db=db)

    # Mark as temp and set old creation time
    record.status = "temp"
    record.created_at = datetime.utcnow() - timedelta(hours=25)
    await db.commit()

    # Cleanup
    deleted_count = await file_service.cleanup_temp(db, max_age_hours=24)
    await db.commit()

    assert deleted_count == 1

    # Check soft delete
    await db.refresh(record)
    assert record.deleted_at is not None


@pytest.mark.asyncio
async def test_cleanup_temp_keep_recent(db, temp_uploads_dir):
    """Test cleanup_temp() - keep recent temp files."""
    file = create_pdf_upload()
    record = await file_service.store(file=file, directory="temp", db=db)

    # Mark as temp (created now = recent)
    record.status = "temp"
    await db.commit()

    # Cleanup
    deleted_count = await file_service.cleanup_temp(db, max_age_hours=24)
    await db.commit()

    assert deleted_count == 0

    # Still active
    await db.refresh(record)
    assert record.deleted_at is None


@pytest.mark.asyncio
async def test_find_orphans(db, temp_uploads_dir):
    """Test find_orphans() - files without links."""
    file1 = create_pdf_upload("orphan.pdf")
    file2 = create_pdf_upload("linked.pdf")

    record1 = await file_service.store(file=file1, directory="test", db=db)
    record2 = await file_service.store(file=file2, directory="test", db=db)

    # Link only file2
    await file_service.link(record2.id, "part", 123, db)

    # Find orphans
    orphans = await file_service.find_orphans(db)

    assert len(orphans) == 1
    assert orphans[0].id == record1.id


# ==================== VALIDATION HELPER TESTS ====================

def test_detect_file_type():
    """Test _detect_file_type()."""
    assert file_service._detect_file_type("test.pdf") == "pdf"
    assert file_service._detect_file_type("model.step") == "step"
    assert file_service._detect_file_type("model.stp") == "step"
    assert file_service._detect_file_type("program.nc") == "nc"

    with pytest.raises(HTTPException) as exc_info:
        file_service._detect_file_type("unknown.xyz")
    assert exc_info.value.status_code == 400


def test_sanitize_filename():
    """Test _sanitize_filename()."""
    # Valid filenames
    assert file_service._sanitize_filename("test.pdf") == "test.pdf"
    assert file_service._sanitize_filename("my_file-v2.pdf") == "my_file-v2.pdf"

    # Path traversal blocked
    with pytest.raises(HTTPException):
        file_service._sanitize_filename("../etc/passwd")

    with pytest.raises(HTTPException):
        file_service._sanitize_filename("test/../file.pdf")


def test_calculate_hash(temp_uploads_dir):
    """Test _calculate_hash()."""
    # Create test file
    test_file = temp_uploads_dir / "test.txt"
    test_file.write_bytes(b"test content")

    # Calculate hash
    file_hash = file_service._calculate_hash(test_file)

    # Verify (known SHA-256 of "test content")
    expected_hash = hashlib.sha256(b"test content").hexdigest()
    assert file_hash == expected_hash
    assert len(file_hash) == 64


# ==================== INTEGRATION TEST ====================

@pytest.mark.asyncio
async def test_full_workflow(db, temp_uploads_dir):
    """Test full workflow: store → link → get → unlink → delete."""
    # 1. Store file
    file = create_pdf_upload("workflow.pdf")
    record = await file_service.store(file=file, directory="parts/123", db=db)
    await db.commit()

    # 2. Link to entity
    link = await file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=123,
        db=db,
        is_primary=True
    )
    await db.commit()

    # 3. Get files for entity
    files = await file_service.get_files_for_entity("part", 123, db)
    assert len(files) == 1

    # 4. Get primary
    primary = await file_service.get_primary("part", 123, db)
    assert primary.id == record.id

    # 5. Unlink
    await file_service.unlink(record.id, "part", 123, db)
    await db.commit()

    # 6. Verify unlinked
    files = await file_service.get_files_for_entity("part", 123, db)
    assert len(files) == 0

    # 7. Delete file record
    await file_service.delete(record.id, db)
    await db.commit()

    # 8. Verify deleted
    with pytest.raises(HTTPException) as exc_info:
        await file_service.get_async(record.id, db)
    assert exc_info.value.status_code == 404
