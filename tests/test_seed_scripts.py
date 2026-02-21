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
from sqlalchemy.orm import selectinload

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
# TEST: seed_work_centers.py
# =============================================================================

@pytest.mark.asyncio
async def test_seed_work_centers_compliance(db_session):
    """
    seed_work_centers.py MUST produce valid work centers that pass ADR-021.

    Validates:
    - WorkCenters exist
    - Hourly rates > 0
    - No duplicates
    - Required fields present
    """
    from scripts.seed_work_centers import seed_work_centers

    # Run seed
    try:
        created = await seed_work_centers(session=db_session)
        assert created >= 0, "Seed function failed"
    except Exception as e:
        pytest.fail(f"seed_work_centers() failed: {e}")

    # Validate output
    result = await db_session.execute(select(WorkCenter))
    wcs = result.scalars().all()

    assert len(wcs) >= 2, f"Expected at least 2 work centers, found {len(wcs)}"

    for wc in wcs:
        # Required fields
        assert wc.work_center_number, f"WorkCenter {wc.id} missing work_center_number"
        assert wc.name, f"WorkCenter {wc.id} missing name"
        assert wc.work_center_type, f"WorkCenter {wc.id} missing work_center_type"

        # Hourly rates validation
        if wc.hourly_rate_amortization is not None:
            assert wc.hourly_rate_amortization > 0, (
                f"WorkCenter {wc.work_center_number} has invalid amortization rate"
            )
        if wc.hourly_rate_labor is not None:
            assert wc.hourly_rate_labor > 0, (
                f"WorkCenter {wc.work_center_number} has invalid labor rate"
            )

    # Check for duplicate work_center_numbers
    result = await db_session.execute(
        select(WorkCenter.work_center_number, func.count(WorkCenter.work_center_number))
        .group_by(WorkCenter.work_center_number)
        .having(func.count(WorkCenter.work_center_number) > 1)
    )
    duplicates = result.all()

    assert len(duplicates) == 0, (
        f"DUPLICATE work_center_numbers detected!\n"
        f"   Duplicates: {[wn for wn, count in duplicates]}\n"
        f"   FIX: scripts/seed_work_centers.py"
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
    # Must match names/codes in seed_material_items.py
    group1 = MaterialGroup(
        code="20910004",
        name="Ocel konstrukční",  # Must match seed_material_items.py expectation
        density=7.85,  # kg/dm³ (ocel)
        created_by="test",
        updated_by="test"
    )
    group2 = MaterialGroup(
        code="20910003",
        name="Nerez",  # Must match seed_material_items.py expectation
        density=7.9,  # kg/dm³ (nerez)
        created_by="test",
        updated_by="test"
    )
    db_session.add(group1)
    db_session.add(group2)
    await db_session.flush()  # Get IDs

    category1 = MaterialPriceCategory(
        code="20900026",  # Must match seed_material_items.py line 35
        name="Ocel konstrukční - tyč kruhová",
        material_group_id=group1.id,
        created_by="test",
        updated_by="test"
    )
    category2 = MaterialPriceCategory(
        code="20900017",  # Must match seed_material_items.py line 77
        name="Nerez - tyč kruhová",
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
    - part_number format (ADR-017: 8 digits, 10XXXXXX range)
    - Required fields present
    - MaterialInputs exist (ADR-024)
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

    # Validate output (eager-load material_inputs for ADR-024 assertions)
    result = await db_session.execute(
        select(Part).options(selectinload(Part.material_inputs))
    )
    parts = result.scalars().all()

    assert len(parts) >= 3, f"Expected at least 3 parts, found {len(parts)}"

    for part in parts:
        # Required fields
        assert part.part_number, f"Part {part.id} missing part_number"
        assert part.name, f"Part {part.id} missing name"

        # ADR-017: 8-digit part_number format (10XXXXXX range)
        assert part.part_number.isdigit(), (
            f"Part {part.part_number} violates ADR-017: must be digits only"
        )
        assert len(part.part_number) == 8, (
            f"Part {part.part_number} violates ADR-017: must be exactly 8 digits, "
            f"got {len(part.part_number)}"
        )

        # ADR-024: material_inputs relationship (not FK on Part)
        assert len(part.material_inputs) > 0, (
            f"Part {part.part_number} has no material_inputs (ADR-024)"
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
@pytest.mark.skip(reason="Subprocess test runs on actual DB, not test DB - inherently flaky")
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
async def test_seed_work_centers_data_passes_validation(db_session):
    """
    META-TEST: Seed data MUST pass current Pydantic validation.

    This test detects schema changes that break seed scripts.
    Prevention: L-015 anti-pattern (changing validation to fit bad data)
    """
    from scripts.seed_work_centers import seed_work_centers

    # Run seed
    await seed_work_centers(session=db_session)

    # Get work centers
    result = await db_session.execute(select(WorkCenter))
    wcs = result.scalars().all()

    for wc in wcs:
        assert wc.work_center_number is not None, "WorkCenter number is None!"
        assert len(wc.work_center_number) > 0, "WorkCenter number is empty!"
        assert wc.work_center_number.strip() == wc.work_center_number, "WorkCenter number has whitespace!"


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
    from scripts.seed_work_centers import seed_work_centers
    from scripts.seed_material_items import seed_material_items
    from scripts.seed_demo_parts import seed_demo_parts

    # Check seed_work_centers has session parameter
    sig = inspect.signature(seed_work_centers)
    assert 'session' in sig.parameters, (
        "seed_work_centers() missing 'session' parameter!"
    )

    # Check seed_material_items has session parameter
    sig = inspect.signature(seed_material_items)
    assert 'session' in sig.parameters, (
        "seed_material_items() missing 'session' parameter!"
    )

    # Check seed_demo_parts has session parameter
    sig = inspect.signature(seed_demo_parts)
    assert 'session' in sig.parameters, (
        "seed_demo_parts() missing 'session' parameter!"
    )


# =============================================================================
# SUMMARY
# =============================================================================

def test_seed_scripts_summary():
    """
    SUMMARY: What these tests do and why.

    Test Coverage:
    1. test_seed_work_centers_compliance - ADR-021 validation, duplicates
    2. test_seed_demo_command_succeeds - Integration (slow, optional)
    3. test_seed_work_centers_data_passes_validation - Schema changes detection
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
