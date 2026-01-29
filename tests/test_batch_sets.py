"""GESTIMA - BatchSet Tests (ADR-022)

Tests for BatchSet model, number generation, and basic functionality.
"""

import pytest
from datetime import datetime

from app.models.batch_set import (
    BatchSet,
    BatchSetCreate,
    BatchSetUpdate,
    BatchSetResponse,
    generate_batch_set_name
)
from app.models.part import Part
from app.models.batch import Batch
from app.services.number_generator import NumberGenerator


class TestBatchSetModel:
    """Test BatchSet SQLAlchemy model"""

    @pytest.mark.asyncio
    async def test_create_batch_set(self, db_session):
        """Test creating a BatchSet"""
        # Create a Part first
        part = Part(
            part_number="10000001",
            name="Test Part",
            created_by="test"
        )
        db_session.add(part)
        await db_session.flush()

        # Create BatchSet
        batch_set = BatchSet(
            set_number="35000001",
            part_id=part.id,
            name="2026-01-28 14:35",
            status="draft",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.commit()

        assert batch_set.id is not None
        assert batch_set.set_number == "35000001"
        assert batch_set.part_id == part.id
        assert batch_set.status == "draft"
        assert batch_set.frozen_at is None

    @pytest.mark.asyncio
    async def test_batch_set_with_batches(self, db_session):
        """Test BatchSet with Batch relationship"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Create Part
        part = Part(
            part_number="10000002",
            name="Test Part 2",
            created_by="test"
        )
        db_session.add(part)
        await db_session.flush()

        # Create BatchSet
        batch_set = BatchSet(
            set_number="35000002",
            part_id=part.id,
            name="2026-01-28 15:00",
            status="draft",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.flush()
        set_id = batch_set.id

        # Create Batches in the set
        batch1 = Batch(
            batch_number="30000001",
            part_id=part.id,
            batch_set_id=set_id,
            quantity=1,
            created_by="test"
        )
        batch2 = Batch(
            batch_number="30000002",
            part_id=part.id,
            batch_set_id=set_id,
            quantity=10,
            created_by="test"
        )
        db_session.add_all([batch1, batch2])
        await db_session.commit()

        # Reload with eager loading to avoid async lazy load issue
        result = await db_session.execute(
            select(BatchSet)
            .where(BatchSet.id == set_id)
            .options(selectinload(BatchSet.batches))
        )
        loaded_set = result.scalar_one()

        assert len(loaded_set.batches) == 2
        assert batch1.batch_set_id == set_id
        assert batch2.batch_set_id == set_id

    @pytest.mark.asyncio
    async def test_batch_set_part_nullable(self, db_session):
        """Test BatchSet with nullable part_id (for orphaned sets)"""
        batch_set = BatchSet(
            set_number="35000003",
            part_id=None,  # No part
            name="Orphaned Set",
            status="frozen",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.commit()

        assert batch_set.id is not None
        assert batch_set.part_id is None


class TestBatchSetNameGeneration:
    """Test auto-naming for BatchSets"""

    def test_generate_batch_set_name_format(self):
        """Test that generated name is in correct format"""
        name = generate_batch_set_name()

        # Should be in format "YYYY-MM-DD HH:MM"
        assert len(name) == 16
        assert name[4] == "-"
        assert name[7] == "-"
        assert name[10] == " "
        assert name[13] == ":"

    def test_generate_batch_set_name_is_current(self):
        """Test that generated name reflects current time"""
        now = datetime.now()
        name = generate_batch_set_name()

        # Should contain current date
        assert name.startswith(now.strftime("%Y-%m-%d"))


class TestBatchSetNumberGeneration:
    """Test number generation for BatchSets"""

    @pytest.mark.asyncio
    async def test_generate_batch_set_number(self, db_session):
        """Test generating a single batch set number"""
        number = await NumberGenerator.generate_batch_set_number(db_session)

        assert number is not None
        assert len(number) == 8
        assert number.startswith("35")  # ADR-022: 35XXXXXX range

    @pytest.mark.asyncio
    async def test_generate_batch_set_numbers_batch(self, db_session):
        """Test generating multiple batch set numbers at once"""
        numbers = await NumberGenerator.generate_batch_set_numbers_batch(db_session, 5)

        assert len(numbers) == 5
        assert len(set(numbers)) == 5  # All unique

        for num in numbers:
            assert len(num) == 8
            assert num.startswith("35")
            assert 35000000 <= int(num) <= 35999999

    @pytest.mark.asyncio
    async def test_generate_batch_set_number_uniqueness(self, db_session):
        """Test that generated numbers don't collide with existing"""
        # Generate first number
        number1 = await NumberGenerator.generate_batch_set_number(db_session)

        # Create BatchSet with that number
        batch_set = BatchSet(
            set_number=number1,
            part_id=None,
            name="Test",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.commit()

        # Generate more numbers - should not include the existing one
        more_numbers = await NumberGenerator.generate_batch_set_numbers_batch(db_session, 10)

        assert number1 not in more_numbers


class TestBatchSetPydanticSchemas:
    """Test Pydantic schemas for BatchSet"""

    def test_batch_set_create_schema(self):
        """Test BatchSetCreate schema validation"""
        # Valid
        data = BatchSetCreate(part_id=1)
        assert data.part_id == 1

        # Invalid: part_id must be > 0
        with pytest.raises(Exception):  # Pydantic ValidationError
            BatchSetCreate(part_id=0)

        with pytest.raises(Exception):
            BatchSetCreate(part_id=-1)

    def test_batch_set_update_schema(self):
        """Test BatchSetUpdate schema validation"""
        # Valid with name
        data = BatchSetUpdate(name="Custom Name", version=1)
        assert data.name == "Custom Name"
        assert data.version == 1

        # Valid without name (only version required)
        data = BatchSetUpdate(version=2)
        assert data.name is None
        assert data.version == 2

    def test_batch_set_response_schema(self):
        """Test BatchSetResponse schema"""
        data = {
            "id": 1,
            "set_number": "35000001",
            "part_id": 5,
            "name": "2026-01-28 14:35",
            "status": "draft",
            "frozen_at": None,
            "frozen_by_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": 0
        }

        response = BatchSetResponse(**data)
        assert response.id == 1
        assert response.set_number == "35000001"
        assert response.status == "draft"


class TestBatchSetStatus:
    """Test BatchSet status transitions"""

    @pytest.mark.asyncio
    async def test_draft_status(self, db_session):
        """Test draft status is default"""
        batch_set = BatchSet(
            set_number="35000010",
            part_id=None,
            name="Draft Test",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.commit()

        assert batch_set.status == "draft"
        assert batch_set.frozen_at is None
        assert batch_set.frozen_by_id is None

    @pytest.mark.asyncio
    async def test_freeze_batch_set(self, db_session):
        """Test freezing a batch set"""
        # Create user first
        from app.models import User
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = User(
            username="testadmin",
            email="admin@test.com",
            hashed_password=pwd_context.hash("test123"),
            created_by="test"
        )
        db_session.add(user)
        await db_session.flush()

        # Create batch set
        batch_set = BatchSet(
            set_number="35000011",
            part_id=None,
            name="To Freeze",
            status="draft",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.flush()

        # Freeze it
        now = datetime.utcnow()
        batch_set.status = "frozen"
        batch_set.frozen_at = now
        batch_set.frozen_by_id = user.id

        await db_session.commit()
        await db_session.refresh(batch_set)

        assert batch_set.status == "frozen"
        assert batch_set.frozen_at is not None
        assert batch_set.frozen_by_id == user.id


class TestBatchSetCascadeDelete:
    """Test cascade delete behavior"""

    @pytest.mark.asyncio
    async def test_batches_cascade_on_set_delete(self, db_session):
        """Test that batches are deleted when batch_set is deleted (CASCADE)"""
        # Create Part
        part = Part(
            part_number="10000010",
            name="Cascade Test Part",
            created_by="test"
        )
        db_session.add(part)
        await db_session.flush()

        # Create BatchSet
        batch_set = BatchSet(
            set_number="35000020",
            part_id=part.id,
            name="Cascade Test",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.flush()
        set_id = batch_set.id

        # Create Batch in the set
        batch = Batch(
            batch_number="30000010",
            part_id=part.id,
            batch_set_id=set_id,
            quantity=5,
            created_by="test"
        )
        db_session.add(batch)
        await db_session.commit()
        batch_id = batch.id

        # Delete the set
        await db_session.delete(batch_set)
        await db_session.commit()

        # Batch should also be deleted (CASCADE)
        from sqlalchemy import select
        result = await db_session.execute(select(Batch).where(Batch.id == batch_id))
        deleted_batch = result.scalar_one_or_none()

        assert deleted_batch is None

    @pytest.mark.asyncio
    async def test_set_survives_part_delete(self, db_session):
        """Test that batch_set survives when part is deleted (SET NULL)"""
        # Create Part
        part = Part(
            part_number="10000011",
            name="Delete Test Part",
            created_by="test"
        )
        db_session.add(part)
        await db_session.flush()
        part_id = part.id

        # Create BatchSet
        batch_set = BatchSet(
            set_number="35000021",
            part_id=part_id,
            name="Survive Test",
            created_by="test"
        )
        db_session.add(batch_set)
        await db_session.commit()
        set_id = batch_set.id

        # Delete the part
        await db_session.delete(part)
        await db_session.commit()

        # BatchSet should survive with NULL part_id
        from sqlalchemy import select
        result = await db_session.execute(select(BatchSet).where(BatchSet.id == set_id))
        surviving_set = result.scalar_one_or_none()

        assert surviving_set is not None
        assert surviving_set.part_id is None  # SET NULL
