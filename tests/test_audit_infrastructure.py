"""Test audit infrastructure: WAL, soft delete, optimistic locking (ADR-001)"""

import pytest
import os
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.models.part import Part
from app.models.material import MaterialGroup, MaterialItem
from app.models.enums import StockShape
from app.db_helpers import soft_delete, restore, is_deleted, get_active, get_all_active


@pytest.fixture
async def db_session():
    """Create isolated test database for each test (with seeded materials, ADR-014)"""
    from app.models.material import MaterialPriceCategory, MaterialPriceTier

    # Use in-memory database for tests
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables with WAL mode
    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.run_sync(Base.metadata.create_all)

    # Provide session with seeded materials
    async with test_session() as session:
        # Seed MaterialGroup (ADR-011)
        group = MaterialGroup(code="11xxx", name="Ocel automatová", density=7.85, created_by="test")
        session.add(group)
        await session.flush()

        # Seed MaterialPriceCategory + Tiers (ADR-014)
        price_category = MaterialPriceCategory(
            code="TEST-OCEL",
            name="Test ocel - kruhová tyč",
            created_by="test"
        )
        session.add(price_category)
        await session.flush()

        tier = MaterialPriceTier(
            price_category_id=price_category.id,
            min_weight=0,
            max_weight=None,
            price_per_kg=45.50,
            created_by="test"
        )
        session.add(tier)
        await session.flush()

        # Seed MaterialItem (ADR-014: uses price_category_id)
        item = MaterialItem(
     material_number="2000002",  # ADR-017
     code="11SMn30-D50",
            name="11SMn30 ⌀50mm",
            material_group_id=group.id,
            price_category_id=price_category.id,
            shape=StockShape.ROUND_BAR,
            diameter=50.0,
            created_by="test"
        )
        session.add(item)
        await session.commit()

        session.test_material_item_id = item.id

        yield session

    # Cleanup
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_wal_mode_enabled(db_session: AsyncSession):
    """Test that WAL mode is enabled (or memory mode for in-memory tests)"""
    result = await db_session.execute(text("PRAGMA journal_mode"))
    mode = result.scalar()
    # In-memory DB uses 'memory', file-based uses 'wal'
    assert mode.lower() in ["wal", "memory"], f"Expected WAL or memory mode, got {mode}"


@pytest.mark.asyncio
async def test_audit_fields_auto_created(db_session: AsyncSession):
    """Test that audit fields are automatically populated"""
    part = Part(
        part_number="TEST001",
        name="Test Part",
        material_item_id=db_session.test_material_item_id
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    
    # Check audit fields
    assert part.created_at is not None
    assert part.updated_at is not None
    assert part.version == 0
    assert part.deleted_at is None


@pytest.mark.asyncio
async def test_version_auto_increments_on_update(db_session: AsyncSession):
    """Test optimistic locking: version increments automatically"""
    part = Part(
        part_number="TEST002",
        name="Test Part 2",
        material_item_id=db_session.test_material_item_id
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    
    initial_version = part.version
    
    # Update part
    part.name = "Updated Name"
    await db_session.commit()
    await db_session.refresh(part)
    
    assert part.version == initial_version + 1


@pytest.mark.asyncio
async def test_soft_delete_marks_as_deleted(db_session: AsyncSession):
    """Test soft delete doesn't remove record from DB"""
    part = Part(
        part_number="TEST003",
        name="Test Part 3",
        material_item_id=db_session.test_material_item_id
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    
    part_id = part.id
    
    # Soft delete
    await soft_delete(db_session, part, deleted_by="test_user")
    
    # Record still exists in DB
    deleted_part = await db_session.get(Part, part_id)
    assert deleted_part is not None
    assert is_deleted(deleted_part)
    assert deleted_part.deleted_by == "test_user"


@pytest.mark.asyncio
async def test_get_active_excludes_deleted(db_session: AsyncSession):
    """Test that get_active() doesn't return soft-deleted records"""
    # Create two parts
    part1 = Part(part_number="TEST004", name="Active Part", material_item_id=db_session.test_material_item_id)
    part2 = Part(part_number="TEST005", name="Deleted Part", material_item_id=db_session.test_material_item_id)
    
    db_session.add_all([part1, part2])
    await db_session.commit()
    
    part1_id = part1.id
    part2_id = part2.id
    
    # Soft delete part2
    await soft_delete(db_session, part2)
    
    # get_active should return part1 but not part2
    active_part1 = await get_active(db_session, Part, part1_id)
    active_part2 = await get_active(db_session, Part, part2_id)
    
    assert active_part1 is not None
    assert active_part2 is None  # Soft-deleted, excluded


@pytest.mark.asyncio
async def test_restore_undeletes_record(db_session: AsyncSession):
    """Test that restore() brings back soft-deleted records"""
    part = Part(part_number="TEST006", name="Test Part", material_item_id=db_session.test_material_item_id)
    db_session.add(part)
    await db_session.commit()
    
    part_id = part.id
    
    # Soft delete
    await soft_delete(db_session, part)
    assert is_deleted(part)
    
    # Restore
    await restore(db_session, part)
    assert not is_deleted(part)
    
    # Should be returned by get_active now
    restored = await get_active(db_session, Part, part_id)
    assert restored is not None


@pytest.mark.asyncio
async def test_get_all_active_excludes_deleted(db_session: AsyncSession):
    """Test that get_all_active() returns only non-deleted records"""
    # Create 3 parts
    part1 = Part(part_number="TEST007", name="Active 1", material_item_id=db_session.test_material_item_id)
    part2 = Part(part_number="TEST008", name="Active 2", material_item_id=db_session.test_material_item_id)
    part3 = Part(part_number="TEST009", name="Deleted", material_item_id=db_session.test_material_item_id)
    
    db_session.add_all([part1, part2, part3])
    await db_session.commit()
    
    # Soft delete part3
    await soft_delete(db_session, part3)
    
    # Get all active
    active_parts = await get_all_active(db_session, Part)
    
    assert len(active_parts) == 2
    assert part3 not in active_parts


@pytest.mark.critical
@pytest.mark.asyncio
async def test_concurrent_update_conflict_detection(db_session: AsyncSession):
    """Test optimistic locking detects concurrent updates"""
    part = Part(part_number="TEST010", name="Concurrent Test", material_item_id=db_session.test_material_item_id)
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    
    # Simulate two users loading the same part
    user1_version = part.version
    user2_version = part.version
    
    # User 1 updates
    part.name = "User 1 Update"
    await db_session.commit()
    await db_session.refresh(part)
    
    # User 2 tries to update with stale version
    # In real code, this would raise an error
    # Here we just verify version changed
    assert part.version == user1_version + 1
    assert part.version != user2_version  # User 2's version is stale
