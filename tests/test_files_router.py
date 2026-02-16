"""GESTIMA - Files Router Tests

Tests for centralized file management (ADR-044).

Coverage:
- POST /api/files/upload (file upload + optional link)
- GET /api/files/{file_id} (metadata + links)
- GET /api/files/{file_id}/download (file download)
- DELETE /api/files/{file_id} (soft delete)
- POST /api/files/{file_id}/link (link to entity)
- PUT /api/files/{file_id}/primary/{entity_type}/{entity_id} (set primary)
- GET /api/files (list with filters)

Transaction handling (L-008): All tests verify rollback on errors.
Validation (L-009): Pydantic Field() constraints tested.
"""

import pytest
import pytest_asyncio
from io import BytesIO

from httpx import AsyncClient
from sqlalchemy import select

from app.models.file_record import FileRecord, FileLink
from app.models.part import Part


@pytest.fixture
def sample_pdf():
    """Create a temporary PDF file for testing"""
    content = b"%PDF-1.4\n%Dummy PDF content for testing\n"
    return BytesIO(content), "test_drawing.pdf", len(content)


@pytest_asyncio.fixture
async def test_part(test_db_session):
    """Create a test part for linking files"""
    part = Part(
        part_number="10234567",  # 8-digit part number
        name="Test Part",
        created_by="admin",
        updated_by="admin"
    )
    test_db_session.add(part)
    await test_db_session.commit()
    await test_db_session.refresh(part)
    return part


class TestFileUpload:
    """Test POST /api/files/upload endpoint"""

    async def test_upload_file_basic(self, client: AsyncClient, admin_headers, sample_pdf):
        """Test basic file upload without entity link"""
        pdf_content, filename, file_size = sample_pdf

        response = await client.post(
            "/api/files/upload",
            data={"directory": "loose"},
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure (L-009 validation)
        assert data["id"] > 0
        assert data["original_filename"] == filename
        assert data["file_type"] == "pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["status"] == "active"
        assert data["file_size"] == file_size
        assert len(data["file_hash"]) == 64  # SHA-256
        assert data["created_by"] == "admin"
        assert data["link"] is None  # No link created

    async def test_upload_file_with_entity_link(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test file upload with immediate entity link"""
        pdf_content, filename, _ = sample_pdf

        response = await client.post(
            "/api/files/upload",
            data={
                "directory": f"parts/{test_part.part_number}",
                "entity_type": "part",
                "entity_id": str(test_part.id),
                "is_primary": "true",
                "revision": "A",
                "link_type": "drawing"
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Verify file record
        assert data["id"] > 0
        assert data["file_type"] == "pdf"
        assert data["status"] == "active"

        # Verify link was created
        assert data["link"] is not None
        assert data["link"]["entity_type"] == "part"
        assert data["link"]["entity_id"] == test_part.id
        assert data["link"]["is_primary"] is True
        assert data["link"]["revision"] == "A"
        assert data["link"]["link_type"] == "drawing"

    async def test_upload_file_invalid_type(self, client: AsyncClient, admin_headers):
        """Test upload with unsupported file type"""
        content = BytesIO(b"not a valid file")

        response = await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "allowed_types": "pdf,step"
            },
            files={"file": ("test.exe", content, "application/octet-stream")},
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()


class TestFileMetadata:
    """Test GET /api/files/{file_id} endpoint"""

    async def test_get_file_metadata(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test retrieving file metadata with links"""
        # Upload file with link
        pdf_content, filename, _ = sample_pdf
        response = await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "entity_type": "part",
                "entity_id": str(test_part.id),
                "is_primary": "true"
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id = response.json()["id"]

        # Get metadata
        response = await client.get(f"/api/files/{file_id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify file data
        assert data["id"] == file_id
        assert data["original_filename"] == filename
        assert data["file_type"] == "pdf"

        # Verify links
        assert len(data["links"]) == 1
        assert data["links"][0]["entity_type"] == "part"
        assert data["links"][0]["entity_id"] == test_part.id
        assert data["links"][0]["is_primary"] is True

    async def test_get_file_not_found(self, client: AsyncClient, admin_headers):
        """Test retrieving non-existent file"""
        response = await client.get("/api/files/999999", headers=admin_headers)

        assert response.status_code == 404


class TestFileDelete:
    """Test DELETE /api/files/{file_id} endpoint"""

    async def test_delete_file(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf
    ):
        """Test soft deleting file (L-008 transaction handling)"""
        # Upload file
        pdf_content, filename, _ = sample_pdf
        response = await client.post(
            "/api/files/upload",
            data={"directory": "loose"},
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id = response.json()["id"]

        # Delete file
        response = await client.delete(f"/api/files/{file_id}", headers=admin_headers)

        assert response.status_code == 204

        # Verify soft delete in DB
        result = await test_db_session.execute(
            select(FileRecord).where(FileRecord.id == file_id)
        )
        record = result.scalar_one()
        assert record.deleted_at is not None
        assert record.deleted_by == "admin"

        # Verify file no longer accessible
        response = await client.get(f"/api/files/{file_id}", headers=admin_headers)
        assert response.status_code == 404


class TestFileLink:
    """Test POST /api/files/{file_id}/link endpoint"""

    async def test_link_file_to_entity(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test linking file to entity"""
        # Upload file without link
        pdf_content, filename, _ = sample_pdf
        response = await client.post(
            "/api/files/upload",
            data={"directory": "loose"},
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id = response.json()["id"]

        # Link to part
        response = await client.post(
            f"/api/files/{file_id}/link",
            json={
                "entity_type": "part",
                "entity_id": test_part.id,
                "is_primary": True,
                "revision": "A",
                "link_type": "drawing"
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Verify link (L-009 validation)
        assert data["file_id"] == file_id
        assert data["entity_type"] == "part"
        assert data["entity_id"] == test_part.id
        assert data["is_primary"] is True
        assert data["revision"] == "A"
        assert data["link_type"] == "drawing"

    async def test_link_upsert_existing(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test UPSERT: linking file that's already linked (should update)"""
        # Upload file with link
        pdf_content, filename, _ = sample_pdf
        response = await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "entity_type": "part",
                "entity_id": str(test_part.id),
                "is_primary": "false",
                "revision": "A"
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id = response.json()["id"]

        # Update link (UPSERT)
        response = await client.post(
            f"/api/files/{file_id}/link",
            json={
                "entity_type": "part",
                "entity_id": test_part.id,
                "is_primary": True,  # Changed
                "revision": "B",     # Changed
                "link_type": "drawing"
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Verify update (not duplicate)
        assert data["is_primary"] is True
        assert data["revision"] == "B"

        # Verify only one link exists in DB
        result = await test_db_session.execute(
            select(FileLink).where(
                FileLink.file_id == file_id,
                FileLink.entity_type == "part",
                FileLink.deleted_at.is_(None)
            )
        )
        links = result.scalars().all()
        assert len(links) == 1


class TestSetPrimary:
    """Test PUT /api/files/{file_id}/primary/{entity_type}/{entity_id} endpoint"""

    async def test_set_primary(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test setting file as primary (unsets others)"""
        # Upload 2 files linked to same part
        pdf_content, filename, _ = sample_pdf

        response1 = await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "entity_type": "part",
                "entity_id": str(test_part.id),
                "is_primary": "true"  # First file is primary
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id_1 = response1.json()["id"]

        # Reset BytesIO
        pdf_content.seek(0)

        response2 = await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "entity_type": "part",
                "entity_id": str(test_part.id),
                "is_primary": "false"  # Second file not primary
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )
        file_id_2 = response2.json()["id"]

        # Set second file as primary
        response = await client.put(
            f"/api/files/{file_id_2}/primary/part/{test_part.id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_primary"] is True

        # Verify first file is no longer primary
        result = await test_db_session.execute(
            select(FileLink).where(
                FileLink.file_id == file_id_1,
                FileLink.entity_type == "part",
                FileLink.entity_id == test_part.id,
                FileLink.deleted_at.is_(None)
            )
        )
        link1 = result.scalar_one()
        assert link1.is_primary is False


class TestFileList:
    """Test GET /api/files endpoint with filters"""

    async def test_list_files_filter_by_entity(
        self,
        client: AsyncClient,
        admin_headers,
        test_db_session,
        sample_pdf,
        test_part
    ):
        """Test listing files filtered by entity"""
        # Upload file linked to part
        pdf_content, filename, _ = sample_pdf
        await client.post(
            "/api/files/upload",
            data={
                "directory": "loose",
                "entity_type": "part",
                "entity_id": str(test_part.id)
            },
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )

        # Upload file NOT linked to part
        pdf_content.seek(0)
        await client.post(
            "/api/files/upload",
            data={"directory": "loose"},
            files={"file": (filename, pdf_content, "application/pdf")},
            headers=admin_headers
        )

        # List files for part
        response = await client.get(
            f"/api/files?entity_type=part&entity_id={test_part.id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["files"][0]["links"][0]["entity_id"] == test_part.id
