"""GESTIMA - Tests for parts filtering and search"""

import pytest
from sqlalchemy import select

from app.models.part import Part


@pytest.mark.asyncio
async def test_create_part_with_article_number(db_session):
    """Test creating part with article_number field"""
    part = Part(
        part_number="P-001",
        article_number="ART-12345",
        name="Test díl",
        material_item_id=db_session.test_material_item.id,
        length=100.0,
        created_by="test"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)

    assert part.id is not None
    assert part.article_number == "ART-12345"
    assert part.part_number == "P-001"


@pytest.mark.asyncio
async def test_part_article_number_optional(db_session):
    """Test that article_number is optional"""
    part = Part(
        part_number="P-002",
        name="Díl bez article",
        material_item_id=db_session.test_material_item.id,
        created_by="test"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)

    assert part.id is not None
    assert part.article_number is None


@pytest.mark.asyncio
async def test_search_by_id(db_session):
    """Test filtering parts by ID"""
    # Create test parts
    for i in range(1, 4):
        part = Part(
            part_number=f"P-{i:03d}",
            name=f"Díl {i}",
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Search by ID
    result = await db_session.execute(select(Part).where(Part.id == 2))
    part = result.scalar_one_or_none()

    assert part is not None
    assert part.part_number == "P-002"


@pytest.mark.asyncio
async def test_search_by_part_number(db_session):
    """Test filtering parts by part_number (ILIKE)"""
    # Create test parts
    parts_data = [
        ("P-100", "Hřídel"),
        ("P-200", "Pouzdro"),
        ("PR-100", "Příruba")
    ]
    for pn, name in parts_data:
        part = Part(
            part_number=pn,
            name=name,
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Search for "P-1" should find P-100
    result = await db_session.execute(
        select(Part).where(Part.part_number.ilike("%P-1%"))
    )
    parts = result.scalars().all()

    assert len(parts) == 1
    assert parts[0].part_number == "P-100"


@pytest.mark.asyncio
async def test_search_by_article_number(db_session):
    """Test filtering parts by article_number (ILIKE)"""
    # Create test parts with article numbers
    parts_data = [
        ("P-001", "ART-123", "Díl A"),
        ("P-002", "ART-456", "Díl B"),
        ("P-003", "ART-789", "Díl C")
    ]
    for pn, art, name in parts_data:
        part = Part(
            part_number=pn,
            article_number=art,
            name=name,
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Search for "456"
    result = await db_session.execute(
        select(Part).where(Part.article_number.ilike("%456%"))
    )
    parts = result.scalars().all()

    assert len(parts) == 1
    assert parts[0].article_number == "ART-456"


@pytest.mark.asyncio
async def test_search_by_name(db_session):
    """Test filtering parts by name (ILIKE)"""
    # Create test parts
    parts_data = [
        ("P-001", "Hřídel vstupní"),
        ("P-002", "Hřídel výstupní"),
        ("P-003", "Pouzdro")
    ]
    for pn, name in parts_data:
        part = Part(
            part_number=pn,
            name=name,
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Search for "hřídel" (case insensitive)
    result = await db_session.execute(
        select(Part).where(Part.name.ilike("%hřídel%"))
    )
    parts = result.scalars().all()

    assert len(parts) == 2
    assert all("Hřídel" in p.name for p in parts)


@pytest.mark.asyncio
async def test_multi_field_search(db_session):
    """Test searching across multiple fields (OR logic)"""
    from sqlalchemy import or_

    # Create diverse test data
    parts_data = [
        ("TEST-001", "ART-001", "Alpha"),
        ("P-002", "TEST-002", "Beta"),
        ("P-003", "ART-003", "Gamma TEST")
    ]
    for pn, art, name in parts_data:
        part = Part(
            part_number=pn,
            article_number=art,
            name=name,
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Search for "TEST" across all fields
    search_term = "%TEST%"
    result = await db_session.execute(
        select(Part).where(
            or_(
                Part.part_number.ilike(search_term),
                Part.article_number.ilike(search_term),
                Part.name.ilike(search_term)
            )
        )
    )
    parts = result.scalars().all()

    assert len(parts) == 3  # All three contain "TEST" in some field


@pytest.mark.asyncio
async def test_part_duplicate_check(db_session):
    """Test that duplicate part_number is prevented"""
    part1 = Part(
        part_number="DUP-001",
        material_item_id=db_session.test_material_item.id,
        created_by="test"
    )
    db_session.add(part1)
    await db_session.commit()

    # Try to create duplicate
    part2 = Part(
        part_number="DUP-001",  # Same part_number
        material_item_id=db_session.test_material_item.id,
        created_by="test"
    )
    db_session.add(part2)

    with pytest.raises(Exception):  # IntegrityError expected
        await db_session.commit()


@pytest.mark.asyncio
async def test_empty_search_returns_all(db_session):
    """Test that empty search returns all parts"""
    # Create test parts
    for i in range(1, 6):
        part = Part(
            part_number=f"P-{i:03d}",
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Empty search
    result = await db_session.execute(select(Part))
    parts = result.scalars().all()

    assert len(parts) == 5


@pytest.mark.asyncio
async def test_pagination(db_session):
    """Test pagination with offset and limit"""
    # Create 10 test parts
    for i in range(1, 11):
        part = Part(
            part_number=f"P-{i:03d}",
            material_item_id=db_session.test_material_item.id,
            created_by="test"
        )
        db_session.add(part)
    await db_session.commit()

    # Page 1 (offset=0, limit=5)
    result = await db_session.execute(
        select(Part).order_by(Part.id).offset(0).limit(5)
    )
    page1 = result.scalars().all()

    # Page 2 (offset=5, limit=5)
    result = await db_session.execute(
        select(Part).order_by(Part.id).offset(5).limit(5)
    )
    page2 = result.scalars().all()

    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0].id != page2[0].id  # Different results
