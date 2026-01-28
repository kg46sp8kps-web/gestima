"""
Tests for Material Price Tiers (ADR-014)
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.material import MaterialPriceCategory, MaterialPriceTier, MaterialItem, MaterialGroup
from app.models.enums import StockShape
from app.models.part import Part
from app.services.price_calculator import get_price_per_kg_for_weight, calculate_stock_cost_from_part


@pytest.mark.asyncio
async def test_tier_selection_small_quantity(db_session):
    """Malé množství (5 kg) → malý tier (highest price)"""
    # Setup: Create price category with tiers
    category = MaterialPriceCategory(
        code="TEST-OCEL-SMALL",
        name="Test ocel - kruhová (small)",
        created_by="test"
    )
    db_session.add(category)
    await db_session.flush()

    # Create tiers
    tiers = [
        MaterialPriceTier(price_category_id=category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=100, max_weight=None, price_per_kg=26.3, created_by="test"),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()

    # Load category with tiers
    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: 5 kg should select first tier (0-15 kg)
    price = await get_price_per_kg_for_weight(category, 5.0, db_session)
    assert price == 49.4


@pytest.mark.asyncio
async def test_tier_selection_medium_quantity(db_session):
    """Střední množství (25 kg) → střední tier"""
    # Setup (reuse from previous test)
    category = MaterialPriceCategory(code="TEST-OCEL2", name="Test ocel 2", created_by="test")
    db_session.add(category)
    await db_session.flush()

    tiers = [
        MaterialPriceTier(price_category_id=category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=100, max_weight=None, price_per_kg=26.3, created_by="test"),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()

    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: 25 kg should select second tier (15-100 kg)
    price = await get_price_per_kg_for_weight(category, 25.0, db_session)
    assert price == 34.5


@pytest.mark.asyncio
async def test_tier_selection_large_quantity(db_session):
    """Velké množství (150 kg) → velký tier (lowest price)"""
    category = MaterialPriceCategory(code="TEST-OCEL3", name="Test ocel 3", created_by="test")
    db_session.add(category)
    await db_session.flush()

    tiers = [
        MaterialPriceTier(price_category_id=category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=100, max_weight=None, price_per_kg=26.3, created_by="test"),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()

    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: 150 kg should select third tier (100+ kg)
    price = await get_price_per_kg_for_weight(category, 150.0, db_session)
    assert price == 26.3


@pytest.mark.asyncio
async def test_tier_selection_boundary_exact(db_session):
    """Boundary test: exactly 15 kg → should use first tier (0-15)"""
    category = MaterialPriceCategory(code="TEST-BOUNDARY", name="Test boundary", created_by="test")
    db_session.add(category)
    await db_session.flush()

    tiers = [
        MaterialPriceTier(price_category_id=category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()

    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: 15 kg is boundary - should select higher min_weight tier (15-100)
    price = await get_price_per_kg_for_weight(category, 15.0, db_session)
    assert price == 34.5  # Second tier because 15 >= 15


@pytest.mark.asyncio
async def test_batch_pricing_with_tiers(db_session):
    """Výpočet batch ceny s dynamickými tiers - different quantity = different price"""
    # Setup: Create material group, price category, material item
    group = MaterialGroup(code="TEST-GROUP", name="Test ocel", density=7.85, created_by="test")
    db_session.add(group)
    await db_session.flush()

    category = MaterialPriceCategory(code="TEST-BATCH", name="Test batch pricing", created_by="test")
    db_session.add(category)
    await db_session.flush()

    tiers = [
        MaterialPriceTier(price_category_id=category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
        MaterialPriceTier(price_category_id=category.id, min_weight=100, max_weight=None, price_per_kg=26.3, created_by="test"),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()

    item = MaterialItem(
     material_number="2000005",  # ADR-017
     code="TEST-D20",
        name="Test Ø20mm",
        shape=StockShape.ROUND_BAR,
        diameter=20,
        material_group_id=group.id,
        price_category_id=category.id,
        created_by="test"
    )
    db_session.add(item)
    await db_session.flush()

    # Create part
    part = Part(
        part_number="TEST-PART",
        name="Test díl",
        material_item_id=item.id,
        stock_diameter=20.0,
        stock_length=100.0,
        created_by="test"
    )
    db_session.add(part)
    await db_session.flush()

    # Load part with relations
    result = await db_session.execute(
        select(Part)
        .options(
            selectinload(Part.material_item).selectinload(MaterialItem.group),
            selectinload(Part.material_item).selectinload(MaterialItem.price_category).selectinload(MaterialPriceCategory.tiers)
        )
        .where(Part.id == part.id)
    )
    part = result.scalar_one()

    # Calculate material cost for different quantities
    # Part weight: π × (10mm)² × 100mm × 7.85 kg/dm³ ≈ 0.25 kg

    # Batch 10 ks = 2.5 kg → small tier (49.4 Kč/kg)
    cost_10 = await calculate_stock_cost_from_part(part, quantity=10, db=db_session)
    assert cost_10.price_per_kg == 49.4

    # Batch 100 ks = 25 kg → medium tier (34.5 Kč/kg)
    cost_100 = await calculate_stock_cost_from_part(part, quantity=100, db=db_session)
    assert cost_100.price_per_kg == 34.5

    # Batch 500 ks = 125 kg → large tier (26.3 Kč/kg)
    cost_500 = await calculate_stock_cost_from_part(part, quantity=500, db=db_session)
    assert cost_500.price_per_kg == 26.3


@pytest.mark.asyncio
async def test_tier_with_single_flat_price(db_session):
    """Kategorie s jedním tier (flat price) - např. OCEL-DESKY"""
    category = MaterialPriceCategory(code="TEST-FLAT", name="Test flat price", created_by="test")
    db_session.add(category)
    await db_session.flush()

    # Only one tier (0 - ∞)
    tier = MaterialPriceTier(
        price_category_id=category.id,
        min_weight=0,
        max_weight=None,
        price_per_kg=30.0,
        created_by="test"
    )
    db_session.add(tier)
    await db_session.flush()

    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: Any quantity should use the same price
    assert await get_price_per_kg_for_weight(category, 5.0, db_session) == 30.0
    assert await get_price_per_kg_for_weight(category, 50.0, db_session) == 30.0
    assert await get_price_per_kg_for_weight(category, 500.0, db_session) == 30.0


@pytest.mark.asyncio
async def test_no_valid_tier_returns_zero(db_session):
    """Edge case: Žádný tier pro danou váhu → vrátí 0 (error handling)"""
    category = MaterialPriceCategory(code="TEST-EMPTY", name="Test empty", created_by="test")
    db_session.add(category)
    await db_session.flush()

    # Tier starts at 10 kg (no tier for < 10 kg)
    tier = MaterialPriceTier(
        price_category_id=category.id,
        min_weight=10,
        max_weight=None,
        price_per_kg=30.0,
        created_by="test"
    )
    db_session.add(tier)
    await db_session.flush()

    result = await db_session.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category.id)
    )
    category = result.scalar_one()

    # Test: 5 kg has no valid tier (min_weight=10)
    price = await get_price_per_kg_for_weight(category, 5.0, db_session)
    assert price == 0  # Error case
