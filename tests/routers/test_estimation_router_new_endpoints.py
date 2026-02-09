"""Tests for new estimation router endpoints (Phase 2-3: Validation + Auto-estimate + Finalize)

Tests 3 new endpoints:
1. PATCH /api/estimation/validate/{record_id} - User feature validation
2. POST /api/estimation/auto-estimate/{record_id} - Physics-based MRR time calculation
3. PATCH /api/estimation/finalize-estimate/{record_id} - Final user estimate

Requires:
- Existing STEP file in uploads/drawings/
- TurningEstimation OR MillingEstimation record in DB
"""

import pytest
from pathlib import Path
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import select

from app.models.turning_estimation import TurningEstimation
from app.models.milling_estimation import MillingEstimation


@pytest.mark.asyncio
async def test_validate_features_turning(client: AsyncClient, db_session):
    """Test PATCH /api/estimation/validate/{record_id} for turning parts."""
    # Create test record
    record = TurningEstimation(
        filename="test_turning.step",
        part_type="ROT",
        extraction_timestamp=datetime.utcnow(),
        part_volume_mm3=1000.0,
        stock_volume_mm3=1500.0,
        removal_volume_mm3=500.0,
        removal_ratio=0.33,
        surface_area_mm2=500.0,
        surface_to_volume_ratio=0.5,
        part_mass_kg=0.008,
        removal_mass_kg=0.004,
        bbox_x_mm=50.0,
        bbox_y_mm=50.0,
        bbox_z_mm=100.0,
        bbox_diagonal_mm=120.0,
        bbox_volume_ratio=0.67,
        aspect_ratio_xy=1.0,
        aspect_ratio_xz=0.5,
        aspect_ratio_yz=0.5,
        bbox_orientation_score=0.9,
        max_dimension_mm=100.0,
        planar_surface_count=2,
        planar_surface_area_mm2=100.0,
        planar_surface_ratio=0.2,
        cylindrical_surface_count=3,
        cylindrical_surface_area_mm2=400.0,
        cylindrical_surface_ratio=0.8,
        conical_surface_count=0,
        conical_surface_area_mm2=0.0,
        toroidal_surface_count=0,
        toroidal_surface_area_mm2=0.0,
        bspline_surface_count=0,
        bspline_surface_area_mm2=0.0,
        surface_type_diversity=0.4,
        largest_planar_face_area_mm2=50.0,
        average_face_area_mm2=100.0,
        total_edge_count=20,
        linear_edge_count=10,
        circular_edge_count=10,
        bspline_edge_count=0,
        edge_type_diversity=0.5,
        total_edge_length_mm=300.0,
        average_edge_length_mm=15.0,
        min_edge_length_mm=5.0,
        max_edge_length_mm=50.0,
        edge_length_std_dev=10.0,
        concave_edge_count=5,
        concave_edge_ratio=0.25,
        shell_count=1,
        face_count=5,
        edge_count=20,
        vertex_count=16,
        euler_characteristic=2,
        genus=0,
        hole_count_estimate=0,
        closed_loop_count=4,
        rotational_score=0.85,
        cylindrical_axis_alignment=0.95,
        diameter_to_length_ratio=0.5,
        cross_section_circularity=0.9,
        cross_section_variance=0.1,
        open_side_count=2,
        undercut_score=0.0,
        thin_wall_score=0.0,
        pocket_volume_estimate_mm3=0.0,
        pocket_count_estimate=0,
        pocket_depth_avg_mm=0.0,
        pocket_depth_max_mm=0.0,
        groove_volume_estimate_mm3=0.0,
        feature_density=0.0,
        min_wall_thickness_mm=3.0,
        max_wall_thickness_mm=10.0,
        min_hole_diameter_mm=0.0,
        max_hole_diameter_mm=0.0,
        min_pocket_width_mm=0.0,
        aspect_ratio_max_feature=1.0,
        material_group_code="20910000",
        material_machinability_index=0.8,
        material_hardness_hb=150.0,
        validation_status="pending"
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Call validation endpoint
    response = await client.patch(
        f"/api/estimation/validate/{record.id}?part_type=ROT",
        json={
            "corrected_material_code": "20910001",
            "corrected_bbox_x_mm": 51.0,
            "corrected_bbox_y_mm": 51.0,
            "corrected_bbox_z_mm": 101.0,
            "correction_notes": "Corrected dimensions from drawing"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "validated"
    assert data["corrected_material_code"] == "20910001"
    assert data["corrected_bbox_x_mm"] == 51.0
    assert data["validated_by_user_id"] == 1
    assert data["validation_date"] is not None


@pytest.mark.asyncio
async def test_finalize_estimate_milling(client: AsyncClient, db_session):
    """Test PATCH /api/estimation/finalize-estimate/{record_id} for milling parts."""
    # Create test record
    record = MillingEstimation(
        filename="test_milling.step",
        part_type="PRI",
        extraction_timestamp=datetime.utcnow(),
        part_volume_mm3=2000.0,
        stock_volume_mm3=3000.0,
        removal_volume_mm3=1000.0,
        removal_ratio=0.33,
        surface_area_mm2=1000.0,
        surface_to_volume_ratio=0.5,
        part_mass_kg=0.016,
        removal_mass_kg=0.008,
        bbox_x_mm=100.0,
        bbox_y_mm=80.0,
        bbox_z_mm=50.0,
        bbox_diagonal_mm=140.0,
        bbox_volume_ratio=0.67,
        aspect_ratio_xy=1.25,
        aspect_ratio_xz=2.0,
        aspect_ratio_yz=1.6,
        bbox_orientation_score=0.7,
        max_dimension_mm=100.0,
        planar_surface_count=6,
        planar_surface_area_mm2=800.0,
        planar_surface_ratio=0.8,
        cylindrical_surface_count=2,
        cylindrical_surface_area_mm2=200.0,
        cylindrical_surface_ratio=0.2,
        conical_surface_count=0,
        conical_surface_area_mm2=0.0,
        toroidal_surface_count=0,
        toroidal_surface_area_mm2=0.0,
        bspline_surface_count=0,
        bspline_surface_area_mm2=0.0,
        surface_type_diversity=0.3,
        largest_planar_face_area_mm2=800.0,
        average_face_area_mm2=125.0,
        total_edge_count=24,
        linear_edge_count=20,
        circular_edge_count=4,
        bspline_edge_count=0,
        edge_type_diversity=0.33,
        total_edge_length_mm=400.0,
        average_edge_length_mm=16.67,
        min_edge_length_mm=10.0,
        max_edge_length_mm=100.0,
        edge_length_std_dev=20.0,
        concave_edge_count=8,
        concave_edge_ratio=0.33,
        shell_count=1,
        face_count=8,
        edge_count=24,
        vertex_count=18,
        euler_characteristic=2,
        genus=0,
        hole_count_estimate=2,
        closed_loop_count=6,
        rotational_score=0.25,
        cylindrical_axis_alignment=0.3,
        diameter_to_length_ratio=0.8,
        cross_section_circularity=0.3,
        cross_section_variance=0.7,
        open_side_count=0,
        undercut_score=0.0,
        thin_wall_score=0.0,
        pocket_volume_estimate_mm3=200.0,
        pocket_count_estimate=1,
        pocket_depth_avg_mm=20.0,
        pocket_depth_max_mm=30.0,
        groove_volume_estimate_mm3=0.0,
        feature_density=0.5,
        min_wall_thickness_mm=5.0,
        max_wall_thickness_mm=20.0,
        min_hole_diameter_mm=10.0,
        max_hole_diameter_mm=15.0,
        min_pocket_width_mm=20.0,
        aspect_ratio_max_feature=1.5,
        material_group_code="20910000",
        material_machinability_index=0.8,
        material_hardness_hb=150.0,
        validation_status="validated",
        auto_estimated_time_min=45.5
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Call finalize endpoint
    response = await client.patch(
        f"/api/estimation/finalize-estimate/{record.id}?part_type=PRI",
        json={
            "estimated_time_min": 50.0,
            "correction_reason": "Added safety factor for complex pockets"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "estimated"
    assert data["estimated_time_min"] == 50.0
    assert data["correction_reason"] == "Added safety factor for complex pockets"
    assert data["estimated_by_user_id"] == 1
    assert data["estimation_date"] is not None


@pytest.mark.asyncio
async def test_validate_404_not_found(client: AsyncClient):
    """Test validation endpoint returns 404 for non-existent record."""
    response = await client.patch(
        "/api/estimation/validate/999999?part_type=ROT",
        json={"correction_notes": "Test"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_finalize_estimate_validation_error(client: AsyncClient):
    """Test finalize endpoint validates estimated_time_min > 0."""
    response = await client.patch(
        "/api/estimation/finalize-estimate/1?part_type=ROT",
        json={"estimated_time_min": -5.0}
    )
    assert response.status_code == 422  # Pydantic validation error
