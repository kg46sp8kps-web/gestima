"""
GESTIMA - Material Calculator Service Tests

Comprehensive test coverage for app/services/material_calculator.py
Following ADR-014 (Price Tiers) and ADR-011 (Two-Tier Hierarchy).

Test Coverage:
1. Volume calculations (all shapes)
2. Weight calculations
3. Price tier selection
4. End-to-end calculation
5. Edge cases
"""

import pytest
import math
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialPriceTier
from app.models.enums import StockShape
from app.services.material_calculator import (
    calculate_volume_round_bar,
    calculate_volume_square_bar,
    calculate_volume_flat_bar,
    calculate_volume_hexagonal_bar,
    calculate_volume_plate,
    calculate_volume_tube,
    calculate_volume,
    find_price_tier,
    calculate_material_weight_and_price,
    MaterialCalculation,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def material_group(db_session):
    """Fixture: MaterialGroup with density"""
    group = MaterialGroup(
        code="TEST-OCEL",
        name="Test ocel konstrukční",
        density=7.85,  # kg/dm³ (steel)
        created_by="test"
    )
    db_session.add(group)
    await db_session.flush()
    return group


@pytest.fixture
async def price_category(db_session, material_group):
    """Fixture: MaterialPriceCategory linked to MaterialGroup"""
    category = MaterialPriceCategory(
        code="TEST-KRUHOVA",
        name="Test ocel - kruhová tyč",
        material_group_id=material_group.id,
        created_by="test"
    )
    db_session.add(category)
    await db_session.flush()
    return category


@pytest.fixture
async def price_tiers(db_session, price_category):
    """Fixture: 3 MaterialPriceTiers (0-15, 15-100, 100-null)"""
    tiers = [
        MaterialPriceTier(
            price_category_id=price_category.id,
            min_weight=0,
            max_weight=15,
            price_per_kg=49.4,
            created_by="test"
        ),
        MaterialPriceTier(
            price_category_id=price_category.id,
            min_weight=15,
            max_weight=100,
            price_per_kg=34.5,
            created_by="test"
        ),
        MaterialPriceTier(
            price_category_id=price_category.id,
            min_weight=100,
            max_weight=None,  # Infinite tier
            price_per_kg=26.3,
            created_by="test"
        ),
    ]
    for tier in tiers:
        db_session.add(tier)
    await db_session.flush()
    return tiers


# ============================================================================
# VOLUME CALCULATIONS - ALL SHAPES
# ============================================================================

@pytest.mark.asyncio
async def test_calculate_volume_round_bar():
    """Test ROUND_BAR volume: π × (D/2)² × L"""
    # Test case: D=20mm, L=100mm
    diameter = 20.0
    length = 100.0

    expected_volume = math.pi * (diameter / 2) ** 2 * length
    actual_volume = calculate_volume_round_bar(diameter, length)

    assert abs(actual_volume - expected_volume) < 0.01
    assert actual_volume > 0

    # Edge case: zero values
    assert calculate_volume_round_bar(0, 100) == 0.0
    assert calculate_volume_round_bar(20, 0) == 0.0
    assert calculate_volume_round_bar(-10, 100) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_square_bar():
    """Test SQUARE_BAR volume: side² × L"""
    # Test case: side=20mm, L=100mm
    side = 20.0
    length = 100.0

    expected_volume = side ** 2 * length
    actual_volume = calculate_volume_square_bar(side, length)

    assert actual_volume == expected_volume
    assert actual_volume == 40000.0  # 20² × 100 = 40,000 mm³

    # Edge case: zero values
    assert calculate_volume_square_bar(0, 100) == 0.0
    assert calculate_volume_square_bar(20, 0) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_flat_bar():
    """Test FLAT_BAR volume: width × thickness × L"""
    # Test case: width=30mm, thickness=10mm, L=100mm
    width = 30.0
    thickness = 10.0
    length = 100.0

    expected_volume = width * thickness * length
    actual_volume = calculate_volume_flat_bar(width, thickness, length)

    assert actual_volume == expected_volume
    assert actual_volume == 30000.0  # 30 × 10 × 100 = 30,000 mm³

    # Edge case: zero values
    assert calculate_volume_flat_bar(0, 10, 100) == 0.0
    assert calculate_volume_flat_bar(30, 0, 100) == 0.0
    assert calculate_volume_flat_bar(30, 10, 0) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_hexagonal_bar():
    """Test HEXAGONAL_BAR volume: 2.598 × side² × L"""
    # Test case: side=20mm, L=100mm
    side = 20.0
    length = 100.0

    hexagon_constant = 2.598076211353316
    expected_volume = hexagon_constant * side ** 2 * length
    actual_volume = calculate_volume_hexagonal_bar(side, length)

    assert abs(actual_volume - expected_volume) < 0.01
    assert actual_volume > 0

    # Edge case: zero values
    assert calculate_volume_hexagonal_bar(0, 100) == 0.0
    assert calculate_volume_hexagonal_bar(20, 0) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_plate():
    """Test PLATE volume: width × height × thickness"""
    # Test case: 200mm × 150mm × 10mm
    width = 200.0
    height = 150.0
    thickness = 10.0

    expected_volume = width * height * thickness
    actual_volume = calculate_volume_plate(width, height, thickness)

    assert actual_volume == expected_volume
    assert actual_volume == 300000.0  # 200 × 150 × 10 = 300,000 mm³

    # Edge case: zero values
    assert calculate_volume_plate(0, 150, 10) == 0.0
    assert calculate_volume_plate(200, 0, 10) == 0.0
    assert calculate_volume_plate(200, 150, 0) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_tube():
    """Test TUBE volume: π × ((D_outer/2)² - (D_inner/2)²) × L"""
    # Test case: outer_D=50mm, wall=5mm, L=100mm
    outer_diameter = 50.0
    wall_thickness = 5.0
    length = 100.0

    r_outer = outer_diameter / 2
    r_inner = r_outer - wall_thickness
    expected_volume = math.pi * (r_outer ** 2 - r_inner ** 2) * length

    actual_volume = calculate_volume_tube(outer_diameter, wall_thickness, length)

    assert abs(actual_volume - expected_volume) < 0.01
    assert actual_volume > 0

    # Edge case: zero values
    assert calculate_volume_tube(0, 5, 100) == 0.0
    assert calculate_volume_tube(50, 0, 100) == 0.0
    assert calculate_volume_tube(50, 5, 0) == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_tube_invalid_geometry():
    """Test TUBE with invalid geometry (wall >= radius) raises ValueError"""
    # Case: wall_thickness >= radius (invalid)
    outer_diameter = 50.0
    wall_thickness = 30.0  # 30 > radius (25) → invalid
    length = 100.0

    with pytest.raises(ValueError, match="Invalid tube geometry"):
        calculate_volume_tube(outer_diameter, wall_thickness, length)

    # Edge case: wall_thickness exactly equals radius
    with pytest.raises(ValueError, match="Invalid tube geometry"):
        calculate_volume_tube(50.0, 25.0, 100.0)


# ============================================================================
# WEIGHT CALCULATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_calculate_weight_from_volume():
    """Test weight calculation: volume_dm³ × density"""
    # Test case: Round bar D20×100mm, steel (7.85 kg/dm³)
    diameter = 20.0
    length = 100.0
    density = 7.85

    volume_mm3 = calculate_volume_round_bar(diameter, length)
    volume_dm3 = volume_mm3 / 1_000_000  # mm³ → dm³

    expected_weight = volume_dm3 * density

    # Verify calculation
    assert volume_dm3 > 0
    assert expected_weight > 0
    # D20×L100 steel bar ≈ 0.25 kg
    assert 0.24 < expected_weight < 0.26


@pytest.mark.asyncio
async def test_weight_with_different_densities():
    """Test weight calculation with different material densities"""
    # Same geometry, different materials
    diameter = 30.0
    length = 100.0
    volume_mm3 = calculate_volume_round_bar(diameter, length)
    volume_dm3 = volume_mm3 / 1_000_000

    # Steel (7.85 kg/dm³)
    weight_steel = volume_dm3 * 7.85

    # Aluminum (2.70 kg/dm³)
    weight_aluminum = volume_dm3 * 2.70

    # Brass (8.50 kg/dm³)
    weight_brass = volume_dm3 * 8.50

    # Verify aluminum is lighter than steel
    assert weight_aluminum < weight_steel

    # Verify brass is heavier than steel
    assert weight_brass > weight_steel

    # Approximate values for D30×L100
    assert 0.5 < weight_steel < 0.6
    assert 0.15 < weight_aluminum < 0.25
    assert 0.5 < weight_brass < 0.65


# ============================================================================
# PRICE TIER SELECTION
# ============================================================================

@pytest.mark.asyncio
async def test_find_price_tier_first_tier(db_session, price_category, price_tiers):
    """Test tier selection for 0-15kg range (highest price)"""
    # Test: 5 kg → should select first tier (0-15 kg, 49.4 Kč/kg)
    tier = await find_price_tier(price_category.id, 5.0, db_session)

    assert tier is not None
    assert tier.min_weight == 0
    assert tier.max_weight == 15
    assert tier.price_per_kg == 49.4


@pytest.mark.asyncio
async def test_find_price_tier_second_tier(db_session, price_category, price_tiers):
    """Test tier selection for 15-100kg range (middle price)"""
    # Test: 25 kg → should select second tier (15-100 kg, 34.5 Kč/kg)
    tier = await find_price_tier(price_category.id, 25.0, db_session)

    assert tier is not None
    assert tier.min_weight == 15
    assert tier.max_weight == 100
    assert tier.price_per_kg == 34.5


@pytest.mark.asyncio
async def test_find_price_tier_infinite_tier(db_session, price_category, price_tiers):
    """Test tier selection for 100+kg range (lowest price, max_weight=null)"""
    # Test: 150 kg → should select third tier (100+, 26.3 Kč/kg)
    tier = await find_price_tier(price_category.id, 150.0, db_session)

    assert tier is not None
    assert tier.min_weight == 100
    assert tier.max_weight is None  # Infinite
    assert tier.price_per_kg == 26.3


@pytest.mark.asyncio
async def test_find_price_tier_boundary_cases(db_session, price_category, price_tiers):
    """Test tier selection at exact boundaries"""
    # Test: exactly 15 kg → should select second tier (15-100)
    tier_15 = await find_price_tier(price_category.id, 15.0, db_session)
    assert tier_15.min_weight == 15
    assert tier_15.price_per_kg == 34.5

    # Test: exactly 100 kg → should select third tier (100+)
    tier_100 = await find_price_tier(price_category.id, 100.0, db_session)
    assert tier_100.min_weight == 100
    assert tier_100.price_per_kg == 26.3

    # Test: 14.99 kg → should select first tier (0-15)
    tier_14 = await find_price_tier(price_category.id, 14.99, db_session)
    assert tier_14.min_weight == 0
    assert tier_14.price_per_kg == 49.4


@pytest.mark.asyncio
async def test_find_price_tier_no_match(db_session, price_category):
    """Test tier selection when no matching tier exists"""
    # Create tier that starts at 10 kg (no tier for < 10 kg)
    tier = MaterialPriceTier(
        price_category_id=price_category.id,
        min_weight=10,
        max_weight=None,
        price_per_kg=30.0,
        created_by="test"
    )
    db_session.add(tier)
    await db_session.flush()

    # Test: 5 kg has no valid tier (min_weight=10)
    result = await find_price_tier(price_category.id, 5.0, db_session)
    assert result is None


# ============================================================================
# END-TO-END CALCULATION
# ============================================================================

@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_round_bar(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test complete calculation: ROUND_BAR geometry → weight → price"""
    # Test case: D20×100mm, quantity=1
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 20, 'length': 100},
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # Verify volume calculation
    expected_volume_mm3 = math.pi * (10 ** 2) * 100  # π × 10² × 100
    assert abs(result.volume_mm3 - expected_volume_mm3) < 1.0

    # Verify weight calculation (steel: 7.85 kg/dm³)
    expected_weight = result.volume_dm3 * 7.85
    assert abs(result.weight_kg - expected_weight) < 0.001
    assert result.density == 7.85

    # Verify tier selection (weight ≈ 0.25 kg → first tier)
    assert result.tier_id == price_tiers[0].id
    assert result.price_per_kg == 49.4
    assert result.tier_range == "0-15kg"

    # Verify cost calculation
    expected_cost = result.weight_kg * 49.4
    assert abs(result.cost_per_piece - expected_cost) < 0.01
    assert result.total_cost == result.cost_per_piece  # quantity=1


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_with_quantity(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test calculation with quantity > 1 (tier changes based on total weight)"""
    # Test case: D20×100mm, quantity=100
    # Single piece ≈ 0.25 kg → total ≈ 25 kg → should use second tier (15-100kg)
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 20, 'length': 100},
        price_category_id=price_category.id,
        quantity=100,
        db=db_session
    )

    # Verify quantity handling
    assert result.quantity == 100
    # Account for rounding (weight_kg is rounded to 3 decimals)
    assert abs(result.total_weight_kg - (result.weight_kg * 100)) < 0.5

    # Verify tier selection (total ≈ 25 kg → second tier)
    assert result.tier_id == price_tiers[1].id
    assert result.price_per_kg == 34.5
    assert result.tier_range == "15-100kg"

    # Verify cost calculation
    assert result.total_cost == result.cost_per_piece * 100


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_large_quantity(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test calculation with large quantity (third tier: 100+kg)"""
    # Test case: D50×100mm, quantity=100
    # Single piece ≈ 1.54 kg → total ≈ 154 kg → should use third tier (100+kg)
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 50, 'length': 100},
        price_category_id=price_category.id,
        quantity=100,
        db=db_session
    )

    # Verify tier selection (total > 100 kg → third tier)
    assert result.tier_id == price_tiers[2].id
    assert result.price_per_kg == 26.3
    assert result.tier_range == "100-∞"


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_square_bar(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test calculation with SQUARE_BAR shape"""
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.SQUARE_BAR,
        dimensions={'width': 20, 'length': 100},
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # Verify volume (20² × 100 = 40,000 mm³)
    assert result.volume_mm3 == 40000.0
    assert result.weight_kg > 0
    assert result.cost_per_piece > 0


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_plate(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test calculation with PLATE shape"""
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.PLATE,
        dimensions={'width': 200, 'height': 150, 'thickness': 10},
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # Verify volume (200 × 150 × 10 = 300,000 mm³)
    assert result.volume_mm3 == 300000.0
    assert result.weight_kg > 0
    assert result.cost_per_piece > 0


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_tube(
    db_session,
    material_group,
    price_category,
    price_tiers
):
    """Test calculation with TUBE shape"""
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.TUBE,
        dimensions={'diameter': 50, 'wall_thickness': 5, 'length': 100},
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # Verify volume and weight
    assert result.volume_mm3 > 0
    assert result.weight_kg > 0
    assert result.cost_per_piece > 0


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_missing_category(db_session):
    """Test calculation with non-existent price_category_id raises HTTPException"""
    with pytest.raises(HTTPException) as exc_info:
        await calculate_material_weight_and_price(
            stock_shape=StockShape.ROUND_BAR,
            dimensions={'diameter': 20, 'length': 100},
            price_category_id=9999,  # Non-existent
            quantity=1,
            db=db_session
        )

    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_missing_material_group(db_session):
    """Test calculation when price_category has no material_group raises HTTPException"""
    # Create price category WITHOUT material_group
    category = MaterialPriceCategory(
        code="NO-GROUP",
        name="Category without group",
        material_group_id=None,  # Missing!
        created_by="test"
    )
    db_session.add(category)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await calculate_material_weight_and_price(
            stock_shape=StockShape.ROUND_BAR,
            dimensions={'diameter': 20, 'length': 100},
            price_category_id=category.id,
            quantity=1,
            db=db_session
        )

    assert exc_info.value.status_code == 400
    assert "no MaterialGroup" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_invalid_density(
    db_session,
    price_category
):
    """Test calculation when MaterialGroup has invalid density raises HTTPException"""
    # Update material_group to have zero density
    stmt = select(MaterialGroup).where(MaterialGroup.id == price_category.material_group_id)
    result = await db_session.execute(stmt)
    group = result.scalar_one()
    group.density = 0.0
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await calculate_material_weight_and_price(
            stock_shape=StockShape.ROUND_BAR,
            dimensions={'diameter': 20, 'length': 100},
            price_category_id=price_category.id,
            quantity=1,
            db=db_session
        )

    assert exc_info.value.status_code == 400
    assert "invalid density" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_invalid_tube_geometry(
    db_session,
    price_category,
    price_tiers
):
    """Test calculation with invalid TUBE geometry raises HTTPException"""
    with pytest.raises(HTTPException) as exc_info:
        await calculate_material_weight_and_price(
            stock_shape=StockShape.TUBE,
            dimensions={'diameter': 50, 'wall_thickness': 30, 'length': 100},  # Invalid!
            price_category_id=price_category.id,
            quantity=1,
            db=db_session
        )

    assert exc_info.value.status_code == 400
    assert "Invalid geometry" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_calculate_material_weight_and_price_no_matching_tier(
    db_session,
    material_group
):
    """Test calculation when no matching tier exists raises HTTPException"""
    # Create category with tier that starts at 10 kg
    category = MaterialPriceCategory(
        code="HIGH-MIN",
        name="High minimum tier",
        material_group_id=material_group.id,
        created_by="test"
    )
    db_session.add(category)
    await db_session.flush()

    tier = MaterialPriceTier(
        price_category_id=category.id,
        min_weight=10,  # Starts at 10 kg!
        max_weight=None,
        price_per_kg=30.0,
        created_by="test"
    )
    db_session.add(tier)
    await db_session.flush()

    # Try to calculate for small part (< 10 kg)
    with pytest.raises(HTTPException) as exc_info:
        await calculate_material_weight_and_price(
            stock_shape=StockShape.ROUND_BAR,
            dimensions={'diameter': 10, 'length': 50},  # Very small → < 10 kg
            price_category_id=category.id,
            quantity=1,
            db=db_session
        )

    assert exc_info.value.status_code == 404
    assert "No matching price tier" in str(exc_info.value.detail)


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_zero_volume(db_session, price_category, price_tiers):
    """Test calculation with zero dimensions returns zero-cost result"""
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 0, 'length': 100},  # Zero diameter
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # Should return zero result, not error
    assert result.volume_mm3 == 0.0
    assert result.volume_dm3 == 0.0
    assert result.weight_kg == 0.0
    assert result.total_weight_kg == 0.0
    assert result.cost_per_piece == 0.0
    assert result.total_cost == 0.0


@pytest.mark.asyncio
async def test_calculate_volume_dispatcher():
    """Test calculate_volume dispatcher function for all shapes"""
    # ROUND_BAR
    vol_round = calculate_volume(
        StockShape.ROUND_BAR,
        {'diameter': 20, 'length': 100}
    )
    assert vol_round > 0

    # SQUARE_BAR
    vol_square = calculate_volume(
        StockShape.SQUARE_BAR,
        {'width': 20, 'length': 100}
    )
    assert vol_square > 0

    # FLAT_BAR
    vol_flat = calculate_volume(
        StockShape.FLAT_BAR,
        {'width': 30, 'height': 10, 'length': 100}
    )
    assert vol_flat > 0

    # HEXAGONAL_BAR
    vol_hex = calculate_volume(
        StockShape.HEXAGONAL_BAR,
        {'diameter': 20, 'length': 100}
    )
    assert vol_hex > 0

    # PLATE
    vol_plate = calculate_volume(
        StockShape.PLATE,
        {'width': 200, 'height': 150, 'thickness': 10}
    )
    assert vol_plate > 0

    # TUBE
    vol_tube = calculate_volume(
        StockShape.TUBE,
        {'diameter': 50, 'wall_thickness': 5, 'length': 100}
    )
    assert vol_tube > 0

    # CASTING (uses round_bar approximation)
    vol_casting = calculate_volume(
        StockShape.CASTING,
        {'diameter': 30, 'length': 80}
    )
    assert vol_casting > 0

    # FORGING (uses round_bar approximation)
    vol_forging = calculate_volume(
        StockShape.FORGING,
        {'diameter': 40, 'length': 90}
    )
    assert vol_forging > 0


@pytest.mark.asyncio
async def test_material_calculation_dataclass():
    """Test MaterialCalculation dataclass initialization"""
    calc = MaterialCalculation()

    # Verify default values
    assert calc.volume_mm3 == 0.0
    assert calc.volume_dm3 == 0.0
    assert calc.weight_kg == 0.0
    assert calc.total_weight_kg == 0.0
    assert calc.price_per_kg == 0.0
    assert calc.cost_per_piece == 0.0
    assert calc.total_cost == 0.0
    assert calc.density == 0.0
    assert calc.quantity == 1
    assert calc.tier_id is None
    assert calc.tier_range == ""


@pytest.mark.asyncio
async def test_rounding_precision(db_session, price_category, price_tiers):
    """Test that calculations use correct rounding precision"""
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 20, 'length': 100},
        price_category_id=price_category.id,
        quantity=1,
        db=db_session
    )

    # volume_mm3 should be rounded to 0 decimal places (integer)
    assert isinstance(result.volume_mm3, (int, float))
    assert result.volume_mm3 == round(result.volume_mm3, 0)

    # volume_dm3 should be rounded to 6 decimal places
    assert round(result.volume_dm3, 6) == result.volume_dm3

    # weight_kg should be rounded to 3 decimal places
    assert round(result.weight_kg, 3) == result.weight_kg
    assert round(result.total_weight_kg, 3) == result.total_weight_kg

    # costs should be rounded to 2 decimal places
    assert round(result.cost_per_piece, 2) == result.cost_per_piece
    assert round(result.total_cost, 2) == result.total_cost


@pytest.mark.asyncio
async def test_db_session_required():
    """Test that db parameter is required"""
    with pytest.raises(ValueError, match="DB session is required"):
        await calculate_material_weight_and_price(
            stock_shape=StockShape.ROUND_BAR,
            dimensions={'diameter': 20, 'length': 100},
            price_category_id=1,
            quantity=1,
            db=None  # Missing!
        )
