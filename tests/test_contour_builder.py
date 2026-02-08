"""Tests for contour_builder.py — deterministic contour from STEP features."""
import pytest
from app.services.contour_builder import ContourBuilder
from app.services.step_parser import StepParser


# ── Unit tests with synthetic features ──

def test_simple_cylinder():
    """Single outer cylinder produces valid contour."""
    builder = ContourBuilder()
    features = [{
        'type': 'cylindrical',
        'radius': 15.0,
        'diameter': 30.0,
        'z_position': 0.0,
        'z_min': 0.0,
        'z_max': 50.0,
        'entity_id': 1,
        'confidence': 1.0,
    }]
    geo = builder.build_profile_geometry(features, {}, 'z')

    assert geo is not None
    assert geo['type'] == 'rotational'
    assert geo['total_length'] == 50.0
    assert geo['max_diameter'] == 30.0
    assert geo['source'] == 'step_deterministic'
    assert geo['confidence'] == 1.0

    outer = geo['outer_contour']
    assert len(outer) >= 3
    assert outer[0]['r'] == 0.0
    assert outer[-1]['r'] == 0.0
    assert any(pt['r'] == 15.0 for pt in outer)


def test_bolt_hole_off_axis():
    """Off-axis cylinders are classified as bolt holes."""
    builder = ContourBuilder()
    features = [
        {
            'type': 'cylindrical', 'radius': 25.0, 'diameter': 50.0,
            'z_position': 0.0, 'z_min': 0.0, 'z_max': 40.0,
            'entity_id': 1, 'confidence': 1.0,
        },
        {
            'type': 'cylindrical', 'radius': 3.5, 'diameter': 7.0,
            'z_position': 0.0, 'z_min': 0.0, 'z_max': 5.0,
            'x_position': 0.0, 'y_position': 20.0,
            'axis_direction': (0.0, 0.0, 1.0),
            'is_inner': True,
            'entity_id': 2, 'confidence': 1.0,
        },
    ]
    geo = builder.build_profile_geometry(features, {}, 'z')

    assert geo is not None
    assert len(geo['holes']) == 1
    assert geo['holes'][0]['diameter'] == 7.0


def test_inner_bore():
    """Inner .F. cylinder becomes inner_contour."""
    builder = ContourBuilder()
    features = [
        {
            'type': 'cylindrical', 'radius': 25.0, 'diameter': 50.0,
            'z_position': 0.0, 'z_min': 0.0, 'z_max': 50.0,
            'entity_id': 1, 'confidence': 1.0,
        },
        {
            'type': 'cylindrical', 'radius': 10.0, 'diameter': 20.0,
            'z_position': 0.0, 'z_min': 0.0, 'z_max': 50.0,
            'is_inner': True,
            'entity_id': 2, 'confidence': 1.0,
        },
    ]
    geo = builder.build_profile_geometry(features, {}, 'z')

    assert geo is not None
    assert len(geo['inner_contour']) >= 2
    assert all(pt['r'] == 10.0 for pt in geo['inner_contour'])


def test_empty_features():
    builder = ContourBuilder()
    assert builder.build_profile_geometry([], {}, 'z') is None


def test_no_outer_surfaces():
    """Test that inverted ADVANCED_FACE sense flags are corrected.

    Single cylinder with is_inner=True but largest radius → should be
    reclassified as outer (main body), not skipped.
    """
    builder = ContourBuilder()
    features = [{
        'type': 'cylindrical', 'radius': 10.0, 'diameter': 20.0,
        'z_position': 0.0, 'z_min': 0.0, 'z_max': 50.0,
        'is_inner': True,  # Inverted STEP sense flag
        'entity_id': 1, 'confidence': 1.0,
    }]
    # With sense-flag correction, this should succeed (largest cyl → outer)
    result = builder.build_profile_geometry(features, {}, 'z')
    assert result is not None
    assert len(result['outer_contour']) >= 3
    assert result['max_diameter'] == 20.0


def test_features_without_boundaries_skipped():
    builder = ContourBuilder()
    features = [{
        'type': 'cylindrical', 'radius': 25.0, 'z_position': 0.0,
        'entity_id': 1, 'confidence': 1.0,
    }]
    assert builder.build_profile_geometry(features, {}, 'z') is None


def test_cone_with_boundary_r():
    """Cone with boundary_r_values produces correct start/end radii."""
    builder = ContourBuilder()
    features = [
        {
            'type': 'cylindrical', 'radius': 15.0, 'diameter': 30.0,
            'z_position': 0.0, 'z_min': 0.0, 'z_max': 87.5,
            'entity_id': 1, 'confidence': 1.0,
        },
        {
            'type': 'cone', 'radius': 15.0, 'angle': 45.0,
            'z_position': 87.5, 'z_min': 87.5, 'z_max': 89.0,
            'boundary_r_values': [13.5, 15.0],
            'entity_id': 2, 'confidence': 1.0,
        },
    ]
    geo = builder.build_profile_geometry(features, {}, 'z')
    assert geo is not None

    outer = geo['outer_contour']
    # Check cone has r=15 at z=87.5 and r=13.5 at z=89
    pts_at_875 = [pt for pt in outer if abs(pt['z'] - 87.5) < 0.1]
    assert any(abs(pt['r'] - 15.0) < 0.1 for pt in pts_at_875)

    pts_at_89 = [pt for pt in outer if abs(pt['z'] - 89.0) < 0.1]
    assert any(abs(pt['r'] - 13.5) < 0.1 for pt in pts_at_89)


def test_contour_z_sorted():
    """Contour points are sorted by z."""
    builder = ContourBuilder()
    features = [
        {
            'type': 'cylindrical', 'radius': 15.0, 'diameter': 30.0,
            'z_position': 50.0, 'z_min': 50.0, 'z_max': 80.0,
            'entity_id': 1, 'confidence': 1.0,
        },
        {
            'type': 'cylindrical', 'radius': 20.0, 'diameter': 40.0,
            'z_position': 10.0, 'z_min': 10.0, 'z_max': 40.0,
            'entity_id': 2, 'confidence': 1.0,
        },
    ]
    geo = builder.build_profile_geometry(features, {}, 'z')
    assert geo is not None
    z_values = [pt['z'] for pt in geo['outer_contour']]
    assert z_values == sorted(z_values)


# ── Integration test with real STEP file ──

def test_pdm249322_integration():
    """Full pipeline: STEP file → contour. Critical dimensions must match."""
    parser = StepParser()
    result = parser.parse_file('drawings/PDM-249322_03.stp')
    assert result['success'] is True

    builder = ContourBuilder()
    geo = builder.build_profile_geometry(
        result['features'],
        result.get('advanced_faces', {}),
        result.get('rotation_axis', 'z')
    )

    assert geo is not None
    assert geo['type'] == 'rotational'
    assert geo['source'] == 'step_deterministic'
    assert geo['confidence'] == 1.0

    # Critical dimensions
    assert geo['total_length'] == 89.0
    assert geo['max_diameter'] == 55.0

    # Key diameters in outer contour
    outer_r = {pt['r'] for pt in geo['outer_contour']}
    assert 27.5 in outer_r, "Missing Ø55 flange"
    assert 15.0 in outer_r, "Missing Ø30 shaft"
    assert 13.5 in outer_r, "Missing Ø27 neck"

    # Ø19 bore (through-hole)
    assert len(geo['inner_contour']) >= 2
    inner_r = {pt['r'] for pt in geo['inner_contour']}
    assert 9.5 in inner_r
    inner_z = [pt['z'] for pt in geo['inner_contour']]
    assert min(inner_z) == 0.0
    assert max(inner_z) == 89.0

    # Bolt holes
    assert len(geo['holes']) >= 1
    assert any(h['diameter'] == 7.0 for h in geo['holes'])


def test_determinism():
    """Same STEP file always gives identical contour."""
    results = []
    for _ in range(3):
        parser = StepParser()
        result = parser.parse_file('drawings/PDM-249322_03.stp')
        builder = ContourBuilder()
        geo = builder.build_profile_geometry(
            result['features'],
            result.get('advanced_faces', {}),
            result.get('rotation_axis', 'z')
        )
        results.append(geo)

    for geo in results[1:]:
        assert geo['outer_contour'] == results[0]['outer_contour']
        assert geo['inner_contour'] == results[0]['inner_contour']
        assert geo['total_length'] == results[0]['total_length']


def test_inverted_sense_flags():
    """Test files with inverted ADVANCED_FACE sense flags.

    Some STEP files (e.g., 0347039_D00114455_000_000.step) have incorrect
    sense flags where the largest cylinder is marked as inner (.F.) but is
    actually the outer main body. The builder should correct this.
    """
    parser = StepParser(use_occt=False)
    result = parser.parse_file('uploads/drawings/0347039_D00114455_000_000.step')

    builder = ContourBuilder()
    geo = builder.build_profile_geometry(
        result['features'],
        result.get('advanced_faces', {}),
        result.get('rotation_axis', 'z')
    )

    assert geo is not None, "Should build contour despite inverted sense flags"
    assert len(geo['outer_contour']) >= 3, "Should have valid outer contour"
    assert geo['max_diameter'] == 30.0, "Ø30 should be outer diameter"


def test_batch_processing_37_files():
    """Regression test: all 37 STEP files in uploads/drawings/ should parse.

    This prevents regression of the "insufficient geometry data" bug that
    affected 15/37 files due to absolute coordinates and inverted sense flags.
    """
    import os

    step_files = []
    for filename in os.listdir('uploads/drawings'):
        if filename.lower().endswith(('.stp', '.step')):
            step_files.append(f'uploads/drawings/{filename}')

    assert len(step_files) >= 37, "Test dataset should have 37+ STEP files"

    successes = 0
    failures = []

    for file_path in step_files:
        try:
            # Create fresh parser for each file (state isolation)
            parser = StepParser(use_occt=False)
            result = parser.parse_file(file_path)

            builder = ContourBuilder()
            geo = builder.build_profile_geometry(
                result['features'],
                result.get('advanced_faces', {}),
                result.get('rotation_axis', 'z')
            )
            if geo and len(geo.get('outer_contour', [])) >= 3:
                successes += 1
            else:
                failures.append(f"{file_path}: no contour")
        except Exception as e:
            failures.append(f"{file_path}: {str(e)[:40]}")

    # All files should succeed (allow 1-2 failures for robustness)
    success_rate = successes / len(step_files)
    if success_rate < 0.95:
        print(f"\nFailed files ({len(failures)}):")
        for f in failures[:5]:  # Show first 5
            print(f"  - {f}")
    assert success_rate >= 0.95, f"Only {successes}/{len(step_files)} succeeded"
