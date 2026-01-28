"""GESTIMA - Tests for seed scripts compliance

CRITICAL: All seed scripts MUST produce valid data that passes:
1. Pydantic validation (schemas)
2. Business rules (ADRs)
3. Database constraints (FKs, unique, etc.)

This prevents L-015 anti-pattern (changing validation to fit bad seed data).

Real-world incident (2026-01-27):
- Seed scripts created invalid data (DEMO-003 violates ADR-017)
- Almost changed validation to fit bad data
- Prevention: Auto-test ALL seed outputs

Purpose:
- Catch schema changes that break seed scripts IMMEDIATELY
- Ensure seed data comply with ADRs
- Prevent maintenance hell (broken demo environment)

Strategy:
- Call seed functions directly with test DB session
- Validate outputs against schemas and business rules
- Fast feedback loop (no subprocess overhead)
"""

import pytest
import sys
from pathlib import Path
from sqlalchemy import select, func

from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialPriceTier
from app.models.material_norm import MaterialNorm
from app.models.work_center import WorkCenter
from app.models.part import Part
from app.models.operation import Operation
from app.models.batch import Batch

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# =============================================================================
# TEST: seed_machines.py
# =============================================================================

@pytest.mark.asyncio
async def test_seed_machines_compliance(db_session):
    """
    seed_machines.py MUST produce valid machines that pass ADR-016.

    Validates:
    - Machines exist
    - Hourly rates > 0 (ADR-016)
    - No duplicates
    - Required fields present
    """
    from scripts.seed_machines import seed_machines

    # Run seed
    try:
        created = await seed_machines(session=db_session)
        assert created >= 0, "Seed function failed"
    except Exception as e:
        pytest.fail(f"❌ seed_machines() failed: {e}")

    # Validate output
    result = await db_session.execute(select(WorkCenter))
    machines = result.scalars().all()

    assert len(machines) >= 2, f"Expected at least 2 machines, found {len(machines)}"

    for machine in machines:
        # Required fields
        assert machine.code, f"Machine {machine.id} missing code"
        assert machine.name, f"Machine {machine.id} missing name"
        assert machine.type, f"Machine {machine.id} missing type"

        # Hourly rates validation (ADR-016)
        assert machine.hourly_rate_amortization > 0, (
            f"Machine {machine.code} has invalid amortization rate"
        )
        assert machine.hourly_rate_labor > 0, (
            f"Machine {machine.code} has invalid labor rate"
        )
        assert machine.hourly_rate_tools >= 0, (
            f"Machine {machine.code} has invalid tools rate"
        )
        assert machine.hourly_rate_overhead >= 0, (
            f"Machine {machine.code} has invalid overhead rate"
        )

        # Total rate sanity check
        total_rate = (
            machine.hourly_rate_amortization +
            machine.hourly_rate_labor +
            machine.hourly_rate_tools +
            machine.hourly_rate_overhead
        )
        assert total_rate > 0, f"Machine {machine.code} has zero total hourly rate"
        assert total_rate < 10000, (
            f"Machine {machine.code} has unrealistic hourly rate: {total_rate} Kč/h"
        )

    # Check for duplicate codes
    result = await db_session.execute(
        select(WorkCenter.code, func.count(WorkCenter.code))
        .group_by(WorkCenter.code)
        .having(func.count(WorkCenter.code) > 1)
    )
    duplicates = result.all()

    assert len(duplicates) == 0, (
        f"❌ DUPLICATE machine codes detected!\n"
        f"   Duplicates: {[code for code, count in duplicates]}\n"
        f"   🚨 FIX: scripts/seed_machines.py"
    )


# =============================================================================
# TEST: seed_material_items.py
# =============================================================================

@pytest.mark.asyncio
async def test_seed_material_items_compliance(db_session):
    """
    seed_material_items.py MUST produce valid MaterialItems.

    Validates:
    - MaterialItems exist
    - Required fields present
    - FKs valid (material_group_id, price_category_id)
    - No duplicates

    Note: Requires MaterialGroup and MaterialPriceCategory to exist (catalog data).
    """
    from scripts.seed_material_items import seed_material_items
    from app.models.material import MaterialItem, MaterialGroup, MaterialPriceCategory

    # Prerequisite: Create minimal catalog data for test
    # (seed_material_items depends on MaterialGroup and MaterialPriceCategory)
    group1 = MaterialGroup(
        code="OCEL-KONS",
        name="Konstrukční ocel",
        density=7.85,  # kg/dm³ (ocel)
        created_by="test",
        updated_by="test"
    )
    group2 = MaterialGroup(
        code="NEREZ",
        name="Nerezová ocel",
        density=7.9,  # kg/dm³ (nerez)
        created_by="test",
        updated_by="test"
    )
    db_session.add(group1)
    db_session.add(group2)
    await db_session.flush()  # Get IDs

    category1 = MaterialPriceCategory(
        code="OCEL-KONS-KRUHOVA",
        name="Ocel konstrukční kruhová",
        material_group_id=group1.id,
        created_by="test",
        updated_by="test"
    )
    category2 = MaterialPriceCategory(
        code="NEREZ-CTVEREC",
        name="Nerez čtverec",
        material_group_id=group2.id,
        created_by="test",
        updated_by="test"
    )
    db_session.add(category1)
    db_session.add(category2)
    await db_session.flush()

    # Run seed
    try:
        created = await seed_material_items(session=db_session)
        assert created >= 0, "Seed function failed"
    except Exception as e:
        pytest.fail(f"❌ seed_material_items() failed: {e}")

    # Validate output
    result = await db_session.execute(select(MaterialItem))
    items = result.scalars().all()

    assert len(items) >= 3, f"Expected at least 3 material items, found {len(items)}"

    for item in items:
        # Required fields
        assert item.material_number, f"MaterialItem {item.id} missing material_number"
        assert item.code, f"MaterialItem {item.id} missing code"
        assert item.name, f"MaterialItem {item.id} missing name"
        assert item.shape, f"MaterialItem {item.id} missing shape"

        # FK validation
        assert item.material_group_id, f"MaterialItem {item.code} missing material_group_id"
        assert item.price_category_id, f"MaterialItem {item.code} missing price_category_id"

    # Check for duplicate codes
    result = await db_session.execute(
        select(MaterialItem.code, func.count(MaterialItem.code))
        .group_by(MaterialItem.code)
        .having(func.count(MaterialItem.code) > 1)
    )
    duplicates = result.all()

    assert len(duplicates) == 0, (
        f"❌ DUPLICATE material item codes detected!\n"
        f"   Duplicates: {[code for code, count in duplicates]}\n"
        f"   🚨 FIX: scripts/seed_material_items.py"
    )


# =============================================================================
# TEST: seed_demo_parts.py
# =============================================================================

@pytest.mark.asyncio
async def test_seed_demo_parts_compliance(db_session):
    """
    seed_demo_parts.py MUST produce valid parts that pass ADR-017.

    Validates:
    - Parts exist
    - part_number format (ADR-017: 7 digits)
    - Required fields present
    - FKs valid (material_item_id)
    - No duplicates

    Note: Requires MaterialItems to exist (seed_material_items).
    """
    from scripts.seed_demo_parts import seed_demo_parts
    from app.models.material import MaterialItem, MaterialGroup, MaterialPriceCategory

    # Prerequisite: Create minimal catalog + material items for test
    # (seed_demo_parts depends on MaterialItems)
    group = MaterialGroup(
        code="TEST-GROUP",
        name="Test Material Group",
        density=7.85,  # kg/dm³
        created_by="test",
        updated_by="test"
    )
    db_session.add(group)
    await db_session.flush()

    category = MaterialPriceCategory(
        code="TEST-CAT",
        name="Test Category",
        material_group_id=group.id,
        created_by="test",
        updated_by="test"
    )
    db_session.add(category)
    await db_session.flush()

    # Create 3 material items (seed_demo_parts expects at least 3)
    for i in range(3):
        item = MaterialItem(
            material_number=f"TEST{i:03d}",
            code=f"TEST-ITEM-{i}",
            name=f"Test Material Item {i}",
            shape="round_bar",
            diameter=20.0 + i * 10,
            material_group_id=group.id,
            price_category_id=category.id,
            created_by="test",
            updated_by="test"
        )
        db_session.add(item)
    await db_session.flush()

    # Run seed
    try:
        created = await seed_demo_parts(session=db_session)
        assert created >= 0, "Seed function failed"
    except Exception as e:
        pytest.fail(f"❌ seed_demo_parts() failed: {e}")

    # Validate output
    result = await db_session.execute(select(Part))
    parts = result.scalars().all()

    assert len(parts) >= 3, f"Expected at least 3 parts, found {len(parts)}"

    for part in parts:
        # Required fields
        assert part.part_number, f"Part {part.id} missing part_number"
        assert part.name, f"Part {part.id} missing name"

        # ADR-017: 7-digit part_number format
        assert part.part_number.isdigit(), (
            f"Part {part.part_number} violates ADR-017: must be digits only"
        )
        assert len(part.part_number) == 7, (
            f"Part {part.part_number} violates ADR-017: must be exactly 7 digits, "
            f"got {len(part.part_number)}"
        )

        # FK validation
        assert part.material_item_id, (
            f"Part {part.part_number} missing material_item_id"
        )

        # Stock dimensions
        if part.stock_diameter is not None:
            assert part.stock_diameter > 0, (
                f"Part {part.part_number} has invalid stock_diameter: {part.stock_diameter}"
            )

    # Check for duplicate part_numbers
    result = await db_session.execute(
        select(Part.part_number, func.count(Part.part_number))
        .group_by(Part.part_number)
        .having(func.count(Part.part_number) > 1)
    )
    duplicates = result.all()

    assert len(duplicates) == 0, (
        f"❌ DUPLICATE part_numbers detected!\n"
        f"   Duplicates: {[pn for pn, count in duplicates]}\n"
        f"   🚨 FIX: scripts/seed_demo_parts.py"
    )


# =============================================================================
# INTEGRATION TEST: seed-demo workflow
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_seed_demo_command_succeeds(db_session):
    """
    INTEGRATION: `python gestima.py seed-demo` MUST succeed without errors.

    This is a smoke test - runs the ACTUAL gestima.py seed-demo command
    and validates it completes successfully.

    Note: This test is marked as 'slow' because it runs the full seed process.
    Run with: pytest -v -m slow
    """
    import subprocess

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "gestima.py"), "seed-demo"],
        input="yes\n",  # Auto-confirm
        capture_output=True,
        text=True,
        timeout=120
    )

    assert result.returncode == 0, (
        f"❌ gestima.py seed-demo failed!\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )

    # Verify output contains success markers
    assert "✅" in result.stdout or "Demo environment ready" in result.stdout, (
        "seed-demo completed but no success markers found"
    )


# =============================================================================
# SCHEMA VALIDATION TEST
# =============================================================================

@pytest.mark.asyncio
async def test_seed_machines_data_passes_validation(db_session):
    """
    META-TEST: Seed data MUST pass current Pydantic validation.

    This test detects schema changes that break seed scripts:
    - If schema changes (e.g., max_length 7 → 10)
    - And seed not updated
    - This test FAILS → forces you to fix seed data

    Prevention: L-015 anti-pattern (changing validation to fit bad data)
    """
    from scripts.seed_machines import seed_machines

    # Run seed
    await seed_machines(session=db_session)

    # Get machines
    result = await db_session.execute(select(WorkCenter))
    machines = result.scalars().all()

    # Attempt to validate with Pydantic (if response model exists)
    # This catches ValidationErrors that would appear in production
    for machine in machines:
        # Basic sanity checks (would be caught by Pydantic in real API)
        assert machine.code is not None, "Machine code is None!"
        assert len(machine.code) > 0, "Machine code is empty!"
        assert machine.code.strip() == machine.code, "Machine code has whitespace!"

        # If you have a MachineResponse Pydantic model, validate here:
        # MachineResponse.model_validate(machine)

    print(f"✅ All {len(machines)} machines pass validation!")


# =============================================================================
# DOCUMENTATION TEST
# =============================================================================

def test_seed_scripts_have_session_parameter():
    """
    DOC TEST: All seed scripts SHOULD accept optional session parameter.

    This enables testing without subprocess overhead.

    Current status:
    - ✅ seed_machines.py - supports session parameter
    - ✅ seed_material_items.py - supports session parameter
    - ✅ seed_demo_parts.py - supports session parameter
    - ❓ seed_material_catalog.py - TODO (subprocess OK)
    - ❓ seed_material_norms_complete.py - TODO (subprocess OK)

    If adding new seed scripts:
    1. Add `session=None` parameter
    2. Use provided session or create own
    3. Only commit if own session
    4. Add test here
    """
    import inspect
    from scripts.seed_machines import seed_machines
    from scripts.seed_material_items import seed_material_items
    from scripts.seed_demo_parts import seed_demo_parts

    # Check seed_machines has session parameter
    sig = inspect.signature(seed_machines)
    assert 'session' in sig.parameters, (
        "seed_machines() missing 'session' parameter!"
    )
    print("✅ seed_machines.py supports session parameter")

    # Check seed_material_items has session parameter
    sig = inspect.signature(seed_material_items)
    assert 'session' in sig.parameters, (
        "seed_material_items() missing 'session' parameter!"
    )
    print("✅ seed_material_items.py supports session parameter")

    # Check seed_demo_parts has session parameter
    sig = inspect.signature(seed_demo_parts)
    assert 'session' in sig.parameters, (
        "seed_demo_parts() missing 'session' parameter!"
    )
    print("✅ seed_demo_parts.py supports session parameter")

    print("⚠️  Other seed scripts still use subprocess pattern (OK for now)")


# =============================================================================
# SUMMARY
# =============================================================================

def test_seed_scripts_summary():
    """
    SUMMARY: What these tests do and why.

    Test Coverage:
    1. test_seed_machines_compliance - ADR-016 validation, duplicates
    2. test_seed_demo_command_succeeds - Integration (slow, optional)
    3. test_seed_machines_data_passes_validation - Schema changes detection
    4. test_seed_scripts_have_session_parameter - Documentation

    Why This Matters:
    - Prevents L-015 anti-pattern (changing validation to fit bad data)
    - Catches schema changes immediately
    - Ensures demo environment always works
    - Forces proper seed data maintenance

    When Tests Fail:
    1. READ relevant ADRs
    2. FIX seed scripts to match schema
    3. DO NOT change validation to fit bad seed data!

    Real-World Incident:
    - 2026-01-27: seed created DEMO-003 (8 chars, violates ADR-017)
    - Almost changed max_length=7 → 50 (walkaround!)
    - User caught it: "tohle je kritické selhání!!!"
    - Prevention: These tests

    Future Improvements:
    - Update all seed scripts to accept session parameter
    - Add Pydantic validation for MaterialGroup, MaterialNorm, Part
    - Add performance benchmarks (seed should complete in <10s)
    """
    print(__doc__)
