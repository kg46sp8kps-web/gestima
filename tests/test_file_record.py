"""Test FileRecord and FileLink models (ADR-044)"""

import pytest
from sqlalchemy import select
from app.models import FileRecord, FileLink


class TestFileRecordModel:
    """Test FileRecord model schema and relationships"""

    @pytest.mark.asyncio
    async def test_file_record_creation(self, db_session):
        """Test basic FileRecord creation"""
        record = FileRecord(
            file_hash="abc123" * 10 + "1234",  # 64-char SHA-256
            file_path="parts/10900635/rev_A.pdf",
            original_filename="výkres_v3.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            status="active",
            created_by="test_user",
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        assert record.id is not None
        assert record.file_hash == "abc123" * 10 + "1234"
        assert record.file_path == "parts/10900635/rev_A.pdf"
        assert record.status == "active"
        assert record.created_by == "test_user"
        assert record.version == 0

    @pytest.mark.asyncio
    async def test_file_path_unique_constraint(self, db_session):
        """Test file_path is unique"""
        record1 = FileRecord(
            file_hash="abc123" * 10 + "1111",
            file_path="parts/10900635/rev_A.pdf",
            original_filename="výkres_v3.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record1)
        await db_session.commit()

        # Same file_path → should fail
        record2 = FileRecord(
            file_hash="abc123" * 10 + "2222",  # Different hash
            file_path="parts/10900635/rev_A.pdf",  # SAME path
            original_filename="different.pdf",
            file_size=1024,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record2)

        with pytest.raises(Exception):  # IntegrityError in async context
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_file_hash_not_unique(self, db_session):
        """Test file_hash is NOT unique (same file can be uploaded multiple times)"""
        same_hash = "abc123" * 10 + "9999"

        record1 = FileRecord(
            file_hash=same_hash,
            file_path="parts/10900635/rev_A.pdf",
            original_filename="výkres_v3.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record1)
        await db_session.commit()

        # Same hash, different path → should succeed
        record2 = FileRecord(
            file_hash=same_hash,  # SAME hash
            file_path="quotes/Q-0001/uploaded.pdf",  # Different path
            original_filename="výkres_v3.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record2)
        await db_session.commit()
        await db_session.refresh(record2)

        assert record2.id != record1.id
        assert record2.file_hash == record1.file_hash


class TestFileLinkModel:
    """Test FileLink model schema and relationships"""

    @pytest.mark.asyncio
    async def test_file_link_creation(self, db_session):
        """Test basic FileLink creation"""
        # Create FileRecord first
        record = FileRecord(
            file_hash="abc123" * 10 + "5555",
            file_path="parts/10900635/rev_A.pdf",
            original_filename="výkres_v3.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # Create link
        link = FileLink(
            file_id=record.id,
            entity_type="part",
            entity_id=123,
            is_primary=True,
            revision="A",
            link_type="drawing",
            created_by="test_user",
        )
        db_session.add(link)
        await db_session.commit()
        await db_session.refresh(link)

        assert link.id is not None
        assert link.file_id == record.id
        assert link.entity_type == "part"
        assert link.entity_id == 123
        assert link.is_primary is True
        assert link.revision == "A"
        assert link.link_type == "drawing"

    @pytest.mark.asyncio
    async def test_unique_file_link_constraint(self, db_session):
        """Test unique constraint: one file can be linked to same entity only once"""
        # Create FileRecord
        record = FileRecord(
            file_hash="abc123" * 10 + "6666",
            file_path="parts/10900635/rev_B.pdf",
            original_filename="výkres_v4.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # First link
        link1 = FileLink(
            file_id=record.id,
            entity_type="part",
            entity_id=123,
            is_primary=True,
            created_by="test_user",
        )
        db_session.add(link1)
        await db_session.commit()

        # Duplicate link (same file_id + entity_type + entity_id) → should fail
        link2 = FileLink(
            file_id=record.id,
            entity_type="part",
            entity_id=123,
            is_primary=False,
            created_by="test_user",
        )
        db_session.add(link2)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_one_file_multiple_entities(self, db_session):
        """Test one file can be linked to multiple different entities"""
        # Create FileRecord
        record = FileRecord(
            file_hash="abc123" * 10 + "7777",
            file_path="loose/JR_810665.pdf",
            original_filename="JR_810665.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # Link to Part 123
        link1 = FileLink(
            file_id=record.id,
            entity_type="part",
            entity_id=123,
            is_primary=True,
            created_by="test_user",
        )
        db_session.add(link1)
        await db_session.commit()

        # Link to TimeVision estimation 42
        link2 = FileLink(
            file_id=record.id,
            entity_type="timevision",
            entity_id=42,
            is_primary=False,
            created_by="test_user",
        )
        db_session.add(link2)
        await db_session.commit()

        # Both should succeed
        result = await db_session.execute(
            select(FileLink).where(FileLink.file_id == record.id)
        )
        links = result.scalars().all()
        assert len(links) == 2
        assert {link.entity_type for link in links} == {"part", "timevision"}

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session):
        """Test FileLinks are deleted when FileRecord is deleted"""
        # Create FileRecord
        record = FileRecord(
            file_hash="abc123" * 10 + "8888",
            file_path="parts/10900635/rev_C.pdf",
            original_filename="výkres_v5.pdf",
            file_size=2048576,
            file_type="pdf",
            mime_type="application/pdf",
            created_by="test_user",
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # Create link
        link = FileLink(
            file_id=record.id,
            entity_type="part",
            entity_id=999,
            created_by="test_user",
        )
        db_session.add(link)
        await db_session.commit()
        link_id = link.id

        # Delete FileRecord
        await db_session.delete(record)
        await db_session.commit()

        # Link should be deleted (cascade)
        result = await db_session.execute(
            select(FileLink).where(FileLink.id == link_id)
        )
        assert result.scalar_one_or_none() is None
