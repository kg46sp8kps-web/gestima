"""Tests for MaterialGroup cutting parameters functionality.

ADR-040: Machining Time Estimation System
Tests CRUD operations and validation for cutting parameters on MaterialGroup model.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.material import MaterialGroup


@pytest.mark.asyncio
async def test_material_group_with_cutting_params(test_db_session: AsyncSession):
    """Test creating MaterialGroup with cutting parameters."""
    # Create material group with all cutting params
    material = MaterialGroup(
        code="TEST-MAT",
        name="Test Material",
        density=7.85,
        iso_group="P",
        hardness_hb=200.0,
        mrr_turning_roughing=300.0,
        mrr_turning_finishing=180.0,
        mrr_milling_roughing=250.0,
        mrr_milling_finishing=150.0,
        cutting_speed_turning=180.0,
        cutting_speed_milling=160.0,
        feed_turning=0.30,
        feed_milling=0.22,
        deep_pocket_penalty=1.6,
        thin_wall_penalty=2.3,
        cutting_data_source="Test Source 2024"
    )

    test_db_session.add(material)

    try:
        await test_db_session.commit()
        await test_db_session.refresh(material)
    except Exception:
        await test_db_session.rollback()
        raise

    # Verify all fields are set
    assert material.id is not None
    assert material.code == "TEST-MAT"
    assert material.iso_group == "P"
    assert material.hardness_hb == 200.0
    assert material.mrr_milling_roughing == 250.0
    assert material.cutting_speed_turning == 180.0
    assert material.deep_pocket_penalty == 1.6
    assert material.cutting_data_source == "Test Source 2024"


@pytest.mark.asyncio
async def test_material_group_query_with_cutting_params(test_db_session: AsyncSession):
    """Test querying MaterialGroups with cutting parameters."""
    # Create test materials
    mat1 = MaterialGroup(
        code="TEST-Q1",
        name="Test Query Material 1",
        density=7.85,
        iso_group="P",
        mrr_milling_roughing=250.0
    )
    mat2 = MaterialGroup(
        code="TEST-Q2",
        name="Test Query Material 2",
        density=2.70,
        iso_group="N",
        mrr_milling_roughing=800.0
    )
    test_db_session.add_all([mat1, mat2])

    try:
        await test_db_session.commit()
    except Exception:
        await test_db_session.rollback()
        raise

    # Query all materials with MRR defined
    result = await test_db_session.execute(
        select(MaterialGroup).filter(
            MaterialGroup.mrr_milling_roughing.isnot(None)
        )
    )
    materials = result.scalars().all()

    # Should have at least 2 materials we just created
    assert len(materials) >= 2

    # Check one specific material
    result = await test_db_session.execute(
        select(MaterialGroup).filter(MaterialGroup.code == "TEST-Q1")
    )
    test_mat = result.scalar_one_or_none()

    assert test_mat is not None
    assert test_mat.name == "Test Query Material 1"
    assert test_mat.iso_group == "P"
    assert test_mat.mrr_milling_roughing == 250.0


@pytest.mark.asyncio
async def test_material_group_update_cutting_params(test_db_session: AsyncSession):
    """Test updating cutting parameters on existing MaterialGroup."""
    # Create material
    material = MaterialGroup(
        code="UPD-TEST",
        name="Update Test Material",
        density=7.85,
        mrr_milling_roughing=100.0
    )
    test_db_session.add(material)

    try:
        await test_db_session.commit()
        await test_db_session.refresh(material)
    except Exception:
        await test_db_session.rollback()
        raise

    # Update cutting params
    material.iso_group = "M"
    material.hardness_hb = 190.0
    material.mrr_milling_roughing = 150.0
    material.cutting_data_source = "Updated Source"

    try:
        await test_db_session.commit()
        await test_db_session.refresh(material)
    except Exception:
        await test_db_session.rollback()
        raise

    # Verify updates
    assert material.iso_group == "M"
    assert material.hardness_hb == 190.0
    assert material.mrr_milling_roughing == 150.0
    assert material.cutting_data_source == "Updated Source"


@pytest.mark.asyncio
async def test_material_group_nullable_cutting_params(test_db_session: AsyncSession):
    """Test that cutting parameters are nullable for backward compatibility."""
    # Create material without cutting params
    material = MaterialGroup(
        code="MIN-TEST",
        name="Minimal Test Material",
        density=2.70
    )
    test_db_session.add(material)

    try:
        await test_db_session.commit()
        await test_db_session.refresh(material)
    except Exception:
        await test_db_session.rollback()
        raise

    # Verify it was created without cutting params
    assert material.id is not None
    assert material.density == 2.70
    assert material.iso_group is None
    assert material.mrr_milling_roughing is None
    assert material.cutting_data_source is None


@pytest.mark.asyncio
async def test_machining_time_estimation_service_with_material_group(test_db_session: AsyncSession):
    """Test that machining time estimation service can fetch MaterialGroup cutting params."""
    from pathlib import Path
    from app.services.machining_time_estimation_service import MachiningTimeEstimationService

    # Check if OCCT is available
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        occt_available = True
    except ImportError:
        occt_available = False

    if not occt_available:
        pytest.skip("OCCT not available - skipping integration test")

    # Find a test STEP file
    test_step_file = Path("uploads/drawings/STEP/3DM_90001234.stp")
    if not test_step_file.exists():
        pytest.skip("Test STEP file not found - skipping integration test")

    # Test estimation with OCEL-AUTO (should exist from seed)
    try:
        result = MachiningTimeEstimationService.estimate_time(
            step_path=test_step_file,
            material="OCEL-AUTO",
            stock_type="bbox"
        )

        # Verify result structure
        assert "total_time_min" in result
        assert "roughing_time_min" in result
        assert "finishing_time_min" in result
        assert "setup_time_min" in result
        assert "breakdown" in result
        assert result["deterministic"] is True

        # Verify material info in breakdown
        breakdown = result["breakdown"]
        assert breakdown["material"] == "OCEL-AUTO"
        assert breakdown["iso_group"] == "P"
        assert breakdown["mrr_roughing_cm3_min"] == 300.0  # From seed data

    except ValueError as e:
        # If material not found, fail the test
        if "not found" in str(e):
            pytest.fail(f"Material OCEL-AUTO should exist after seed: {e}")
        raise


@pytest.mark.asyncio
async def test_material_groups_with_iso_groups(test_db_session: AsyncSession):
    """Test querying materials by ISO group."""
    # Create test materials with different ISO groups
    mat_p1 = MaterialGroup(code="TEST-P1", name="Test P1", density=7.85, iso_group="P")
    mat_p2 = MaterialGroup(code="TEST-P2", name="Test P2", density=7.85, iso_group="P")
    mat_p3 = MaterialGroup(code="TEST-P3", name="Test P3", density=7.85, iso_group="P")
    mat_n = MaterialGroup(code="TEST-N", name="Test N", density=2.70, iso_group="N")

    test_db_session.add_all([mat_p1, mat_p2, mat_p3, mat_n])

    try:
        await test_db_session.commit()
    except Exception:
        await test_db_session.rollback()
        raise

    # Query ISO P materials (steels)
    result = await test_db_session.execute(
        select(MaterialGroup).filter(MaterialGroup.iso_group == "P")
    )
    p_materials = result.scalars().all()

    # Should have at least 3 P materials
    assert len(p_materials) >= 3

    # Verify they all have P group
    for mat in p_materials:
        assert mat.iso_group == "P"


@pytest.mark.asyncio
async def test_material_group_penalty_factors(test_db_session: AsyncSession):
    """Test penalty factor fields."""
    material = MaterialGroup(
        code="PEN-TEST",
        name="Penalty Test",
        density=7.85,
        deep_pocket_penalty=2.0,
        thin_wall_penalty=3.0
    )
    test_db_session.add(material)

    try:
        await test_db_session.commit()
        await test_db_session.refresh(material)
    except Exception:
        await test_db_session.rollback()
        raise

    assert material.deep_pocket_penalty == 2.0
    assert material.thin_wall_penalty == 3.0
