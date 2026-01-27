"""
Tests for Batch Recalculation (P0-CRITICAL: Batch costs calculation)

Verifies that batches are automatically recalculated with correct costs
based on Part material + Operations + Machines.
"""

import pytest
from sqlalchemy import select

from app.models.batch import Batch
from app.models.part import Part
from app.models.operation import Operation
from app.models.machine import MachineDB
from app.models.material import MaterialGroup, MaterialItem, MaterialPriceCategory, MaterialPriceTier
from app.models.enums import StockShape
from app.services.batch_service import recalculate_batch_costs


@pytest.mark.asyncio
async def test_recalculate_batch_costs_basic(db_session):
    """Test basic batch recalculation with material + operations"""

    # 1. Setup Material (ocel s price tiers)
    group = MaterialGroup(
        code="OCEL",
        name="Ocel",
        density=7.85,  # kg/dm³
        created_by="test"
    )
    db_session.add(group)
    await db_session.flush()

    category = MaterialPriceCategory(
        code="OCEL-KRUH",
        name="Ocel kruhová",
        created_by="test"
    )
    db_session.add(category)
    await db_session.flush()

    tier = MaterialPriceTier(
        price_category_id=category.id,
        min_weight=0,
        max_weight=None,
        price_per_kg=50.0,  # 50 Kč/kg
        created_by="test"
    )
    db_session.add(tier)
    await db_session.flush()

    material_item = MaterialItem(
        code="11523",
        name="11523",
        shape=StockShape.ROUND_BAR,
        diameter=30.0,  # mm
        material_group_id=group.id,
        price_category_id=category.id,
        created_by="test"
    )
    db_session.add(material_item)
    await db_session.flush()

    # 2. Setup Part (tyč Ø30 × 100mm)
    part = Part(
        part_number="TEST-001",
        name="Test díl",
        material_item_id=material_item.id,
        length=100.0,  # mm
        stock_diameter=30.0,
        stock_length=100.0,
        created_by="test"
    )
    db_session.add(part)
    await db_session.flush()

    # 3. Setup Machine
    # hourly_rate_operation = amortization + labor + tools + overhead = 1200
    # hourly_rate_setup = amortization + labor + overhead (BEZ tools) = 1000
    machine = MachineDB(
        code="INDEX-32",
        name="INDEX Sprint 32",
        type="lathe",
        hourly_rate_amortization=300.0,
        hourly_rate_labor=600.0,
        hourly_rate_tools=200.0,
        hourly_rate_overhead=100.0,
        created_by="test"
    )
    db_session.add(machine)
    await db_session.flush()

    # 4. Setup Operation (soustružení 10 min tp, 30 min tj)
    operation = Operation(
        part_id=part.id,
        seq=10,
        name="OP10 - Soustružení",
        type="turning",
        machine_id=machine.id,
        operation_time_min=10.0,  # tp
        setup_time_min=30.0,  # tj
        is_coop=False,
        created_by="test"
    )
    db_session.add(operation)
    await db_session.flush()

    # 5. Create Batch (quantity=10)
    batch = Batch(
        part_id=part.id,
        quantity=10,
        created_by="test"
    )
    db_session.add(batch)
    await db_session.flush()

    # 6. Recalculate batch costs
    await recalculate_batch_costs(batch, db_session)

    # 7. Verify costs
    # Material cost:
    #   - Volume: π × (15mm)² × 100mm = 70686 mm³ = 0.0707 dm³
    #   - Weight: 0.0707 dm³ × 7.85 kg/dm³ = 0.555 kg
    #   - Cost per piece: 0.555 kg × 50 Kč/kg = 27.75 Kč
    assert batch.material_cost == pytest.approx(27.75, abs=0.5), \
        f"Material cost should be ~27.75 Kč, got {batch.material_cost}"

    # Machining cost (používá hourly_rate_operation = 1200):
    #   - 10 min × (1200 Kč/60 min) = 10 × 20 = 200 Kč per piece
    assert batch.machining_cost == 200.0, \
        f"Machining cost should be 200 Kč, got {batch.machining_cost}"

    # Setup cost (starý calculate_batch_prices používá hourly_rate = 1200):
    #   - 30 min × (1200 Kč/60 min) / 10 = 30 × 20 / 10 = 60 Kč per piece
    # Poznámka: Nový ADR-016 kalkulátor používá hourly_rate_setup (1000), ale tento test používá starší funkci
    assert batch.setup_cost == 60.0, \
        f"Setup cost should be 60 Kč, got {batch.setup_cost}"

    # Coop cost: 0
    assert batch.coop_cost == 0.0

    # Unit cost: 27.75 + 200 + 60 = ~287.75 Kč
    assert batch.unit_cost == pytest.approx(287.75, abs=0.5), \
        f"Unit cost should be ~287.75 Kč, got {batch.unit_cost}"

    # Total cost: 287.75 × 10 = ~2877.5 Kč
    assert batch.total_cost == pytest.approx(2877.5, abs=5), \
        f"Total cost should be ~2877.5 Kč, got {batch.total_cost}"

    # Unit time: 10 min
    assert batch.unit_time_min == 10.0


@pytest.mark.asyncio
async def test_recalculate_batch_no_material(db_session):
    """Test batch recalculation when Part has no material_item"""

    # Setup Part without material
    part = Part(
        part_number="TEST-002",
        name="Test díl bez materiálu",
        created_by="test"
    )
    db_session.add(part)
    await db_session.flush()

    # Create Batch
    batch = Batch(
        part_id=part.id,
        quantity=1,
        created_by="test"
    )
    db_session.add(batch)
    await db_session.flush()

    # Recalculate (should not fail, just set material_cost=0)
    await recalculate_batch_costs(batch, db_session)

    # Verify
    assert batch.material_cost == 0.0
    assert batch.machining_cost == 0.0  # No operations
    assert batch.unit_cost == 0.0


@pytest.mark.asyncio
async def test_recalculate_batch_with_coop(db_session):
    """Test batch recalculation with cooperation operation"""

    # Setup Part (simple, no material for this test)
    part = Part(
        part_number="TEST-003",
        name="Test díl s kooperací",
        created_by="test"
    )
    db_session.add(part)
    await db_session.flush()

    # Setup Cooperation Operation
    coop_op = Operation(
        part_id=part.id,
        seq=10,
        name="OP10 - Kalení",
        type="cooperation",
        is_coop=True,
        coop_price=50.0,  # 50 Kč per piece
        coop_min_price=200.0,  # Minimum 200 Kč total
        created_by="test"
    )
    db_session.add(coop_op)
    await db_session.flush()

    # Create Batch (quantity=3)
    batch = Batch(
        part_id=part.id,
        quantity=3,
        created_by="test"
    )
    db_session.add(batch)
    await db_session.flush()

    # Recalculate
    await recalculate_batch_costs(batch, db_session)

    # Verify:
    # Coop cost: max(50 × 3, 200) / 3 = 200 / 3 = 66.67 Kč per piece
    assert batch.coop_cost == pytest.approx(66.67, abs=0.1), \
        f"Coop cost should be ~66.67 Kč, got {batch.coop_cost}"

    # Unit cost: 0 + 0 + 0 + 66.67 = 66.67 Kč
    assert batch.unit_cost == pytest.approx(66.67, abs=0.1)
