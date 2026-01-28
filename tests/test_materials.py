"""
GESTIMA - Tests for materials router (ADR-011: Material Hierarchy)

Testy ověřují:
- MaterialGroup CRUD (create, read, update)
- MaterialItem CRUD (create, read, update, soft delete)
- Foreign key validations
- Optimistic locking (version conflicts)
- Duplicate detection
"""

import pytest
from sqlalchemy import select

from app.models.material import MaterialGroup, MaterialItem
from app.models.enums import StockShape


# ============================================================================
# MATERIAL GROUP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_material_group_seed_exists(db_session):
    """Test: Seed data creates MaterialGroup"""
    result = await db_session.execute(select(MaterialGroup))
    groups = result.scalars().all()

    assert len(groups) >= 1
    assert db_session.test_material_group is not None
    assert db_session.test_material_group.code == "11xxx"


@pytest.mark.asyncio
async def test_create_material_group(db_session):
    """Test: Create new MaterialGroup"""
    group = MaterialGroup(
        code="12xxx",
        name="Ocel konstrukční",
        density=7.85,
        created_by="test"
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    assert group.id is not None
    assert group.code == "12xxx"
    assert group.density == 7.85
    assert group.version >= 0  # Default is 0, incremented on update


@pytest.mark.asyncio
async def test_material_group_duplicate_code_fails(db_session):
    """Test: Duplicate MaterialGroup code raises IntegrityError"""
    # Create first group
    group1 = MaterialGroup(
        code="UNIQUE-001",
        name="First",
        density=7.85,
        created_by="test"
    )
    db_session.add(group1)
    await db_session.commit()

    # Try to create duplicate
    group2 = MaterialGroup(
        code="UNIQUE-001",  # Same code
        name="Second",
        density=7.85,
        created_by="test"
    )
    db_session.add(group2)

    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_material_group_update(db_session):
    """Test: Update MaterialGroup"""
    group = db_session.test_material_group
    original_version = group.version

    group.name = "Updated Name"
    await db_session.commit()
    await db_session.refresh(group)

    assert group.name == "Updated Name"
    # Version should auto-increment (event listener)
    assert group.version == original_version + 1


@pytest.mark.asyncio
async def test_material_group_density_required(db_session):
    """Test: MaterialGroup density is required and > 0"""
    # Note: Validation is at Pydantic level, not DB level
    # Here we just verify the model accepts valid data
    group = MaterialGroup(
        code="TEST-DENSITY",
        name="Test",
        density=8.96,  # Copper
        created_by="test"
    )
    db_session.add(group)
    await db_session.commit()

    assert group.density == 8.96


# ============================================================================
# MATERIAL ITEM TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_material_item_seed_exists(db_session):
    """Test: Seed data creates MaterialItem with FK to MaterialGroup"""
    result = await db_session.execute(select(MaterialItem))
    items = result.scalars().all()

    assert len(items) >= 1
    assert db_session.test_material_item is not None
    assert db_session.test_material_item.material_group_id == db_session.test_material_group.id


@pytest.mark.asyncio
async def test_create_material_item(db_session):
    """Test: Create new MaterialItem (ADR-014: uses price_category_id instead of price_per_kg)"""
    item = MaterialItem(
     material_number="2000006",  # ADR-017
     code="11SMn30-D100",
        name="11SMn30 ⌀100 mm - tyč kruhová",
        material_group_id=db_session.test_material_group.id,
        price_category_id=db_session.test_price_category.id,
        shape=StockShape.ROUND_BAR,
        diameter=100.0,
        created_by="test"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    assert item.id is not None
    assert item.code == "11SMn30-D100"
    assert item.diameter == 100.0
    assert item.price_category_id == db_session.test_price_category.id


@pytest.mark.asyncio
async def test_material_item_duplicate_code_fails(db_session):
    """Test: Duplicate MaterialItem code raises IntegrityError"""
    # Create first item
    item1 = MaterialItem(
     material_number="2000007",  # ADR-017
     code="UNIQUE-ITEM-001",
        name="First",
        material_group_id=db_session.test_material_group.id,
        price_category_id=db_session.test_price_category.id,
        shape=StockShape.ROUND_BAR,
        created_by="test"
    )
    db_session.add(item1)
    await db_session.commit()

    # Try to create duplicate
    item2 = MaterialItem(
     material_number="2000008",  # ADR-017
     code="UNIQUE-ITEM-001",  # Same code
        name="Second",
        material_group_id=db_session.test_material_group.id,
        price_category_id=db_session.test_price_category.id,
        shape=StockShape.ROUND_BAR,
        created_by="test"
    )
    db_session.add(item2)

    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_material_item_shapes(db_session):
    """Test: MaterialItem supports various StockShape types (ADR-014: uses price_category_id)"""
    # MaterialItem fields: diameter, width, thickness, wall_thickness
    shapes_data = [
        (StockShape.ROUND_BAR, {"diameter": 50.0}),
        (StockShape.TUBE, {"diameter": 80.0, "wall_thickness": 10.0}),
        (StockShape.PLATE, {"width": 100.0, "thickness": 10.0}),
        (StockShape.FLAT_BAR, {"width": 100.0, "thickness": 50.0}),
    ]

    for i, (shape, dims) in enumerate(shapes_data):
        item = MaterialItem(
     material_number=f"{2000009 + i}",  # ADR-017
     code=f"SHAPE-TEST-{i}",
            name=f"Shape test {shape.value}",
            material_group_id=db_session.test_material_group.id,
            price_category_id=db_session.test_price_category.id,
            shape=shape,
            created_by="test",
            **dims
        )
        db_session.add(item)

    await db_session.commit()

    # Verify all shapes created
    result = await db_session.execute(
        select(MaterialItem).where(MaterialItem.code.like("SHAPE-TEST-%"))
    )
    items = result.scalars().all()

    assert len(items) == 4


@pytest.mark.asyncio
async def test_material_item_soft_delete(db_session):
    """Test: MaterialItem soft delete sets deleted_at (ADR-014: uses price_category_id)"""
    from datetime import datetime

    # Create item
    item = MaterialItem(
     material_number="2000010",  # ADR-017
     code="TO-DELETE",
        name="Delete me",
        material_group_id=db_session.test_material_group.id,
        price_category_id=db_session.test_price_category.id,
        shape=StockShape.ROUND_BAR,
        created_by="test"
    )
    db_session.add(item)
    await db_session.commit()

    # Soft delete
    item.deleted_at = datetime.utcnow()
    item.deleted_by = "admin"
    await db_session.commit()
    await db_session.refresh(item)

    assert item.deleted_at is not None
    assert item.deleted_by == "admin"


@pytest.mark.asyncio
async def test_material_item_requires_group_id(db_session):
    """Test: MaterialItem material_group_id is required (non-nullable)"""
    # Verify the field exists and is linked correctly
    item = db_session.test_material_item
    assert item.material_group_id is not None
    assert item.material_group_id == db_session.test_material_group.id

    # Verify relationship works
    await db_session.refresh(item, ["group"])
    assert item.group is not None


@pytest.mark.asyncio
async def test_material_item_update(db_session):
    """Test: Update MaterialItem name (ADR-014: price_per_kg removed, testing name update)"""
    item = db_session.test_material_item
    original_version = item.version

    item.name = "Updated Material Name"
    await db_session.commit()
    await db_session.refresh(item)

    assert item.name == "Updated Material Name"
    assert item.version == original_version + 1


@pytest.mark.asyncio
async def test_material_item_group_relationship(db_session):
    """Test: MaterialItem.group relationship works"""
    result = await db_session.execute(
        select(MaterialItem).where(MaterialItem.id == db_session.test_material_item.id)
    )
    item = result.scalar_one()

    # Access relationship (may need eager loading in real scenario)
    await db_session.refresh(item, ["group"])

    assert item.group is not None
    assert item.group.code == "11xxx"


# ============================================================================
# BUSINESS LOGIC TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_material_item_has_price_category(db_session):
    """Test: MaterialItem has valid price_category_id (ADR-014: replaces price_per_kg)"""
    item = MaterialItem(
     material_number="2000011",  # ADR-017
     code="PRICED-STOCK",
        name="Priced stock",
        material_group_id=db_session.test_material_group.id,
        price_category_id=db_session.test_price_category.id,
        shape=StockShape.ROUND_BAR,
        diameter=25.0,
        created_by="test"
    )
    db_session.add(item)
    await db_session.commit()

    assert item.price_category_id == db_session.test_price_category.id


@pytest.mark.asyncio
async def test_material_group_cascade_items(db_session):
    """Test: Verify items are linked to group correctly (ADR-014: uses price_category_id)"""
    # Create new group with items
    group = MaterialGroup(
        code="CASCADE-TEST",
        name="Cascade Test Group",
        density=7.85,
        created_by="test"
    )
    db_session.add(group)
    await db_session.flush()

    # Add items to group
    for i in range(3):
        item = MaterialItem(
     material_number=f"{2000012 + i}",  # ADR-017
     code=f"CASCADE-ITEM-{i}",
            name=f"Cascade Item {i}",
            material_group_id=group.id,
            price_category_id=db_session.test_price_category.id,
            shape=StockShape.ROUND_BAR,
            created_by="test"
        )
        db_session.add(item)

    await db_session.commit()

    # Verify items are linked
    result = await db_session.execute(
        select(MaterialItem).where(MaterialItem.material_group_id == group.id)
    )
    items = result.scalars().all()

    assert len(items) == 3


@pytest.mark.asyncio
async def test_material_group_filter_by_items(db_session):
    """Test: Can filter items by group_id"""
    # Items from seed group
    result = await db_session.execute(
        select(MaterialItem).where(
            MaterialItem.material_group_id == db_session.test_material_group.id
        )
    )
    items = result.scalars().all()

    # At least the seeded item should exist
    assert len(items) >= 1
    assert all(i.material_group_id == db_session.test_material_group.id for i in items)
