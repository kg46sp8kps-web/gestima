"""
Test Enhanced STEP Parser - Reference Resolution and Classification

Tests the upgraded step_parser.py with:
- Multi-line entity parsing
- Reference resolution (AXIS2_PLACEMENT_3D → CARTESIAN_POINT)
- Inner/outer surface classification (ADVANCED_FACE .T./.F. sense)
- Rotation axis detection
- Exact Z-positions for all features
"""

import pytest
from app.services.step_parser import StepParser


def test_step_parser_enhanced_pdm_249322():
    """Test enhanced parser on PDM-249322_03.stp reference file"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    assert result['success'] is True
    assert result['format'] == 'step'
    assert result['source'] in ('step_geometry', 'step_regex', 'occt')
    assert result['confidence'] == 1.0


def test_rotation_axis_detection():
    """Test that rotation axis is detected correctly"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    assert result['rotation_axis'] == 'z', "Should detect Z-axis rotation for this part"


def test_advanced_faces_classification():
    """Test ADVANCED_FACE parsing and inner/outer classification"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    assert 'advanced_faces' in result
    assert len(result['advanced_faces']) == 19, "Should parse 19 ADVANCED_FACE entities"

    # Check specific surfaces
    advanced_faces = result['advanced_faces']

    # #91 = Ø55 flange, OUTER (.T.)
    assert 91 in advanced_faces
    assert advanced_faces[91]['sense'] == 'T'

    # #92 = Ø19 bore, INNER (.F.)
    assert 92 in advanced_faces
    assert advanced_faces[92]['sense'] == 'F'

    # #95, #96 = Ø7 bolt holes, INNER (.F.)
    assert 95 in advanced_faces
    assert advanced_faces[95]['sense'] == 'F'
    assert 96 in advanced_faces
    assert advanced_faces[96]['sense'] == 'F'


def test_cylindrical_surfaces_with_positions():
    """Test cylindrical surface parsing with exact positions"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    features = result['features']
    cylinders = [f for f in features if f['type'] == 'cylindrical']

    # Note: #96 is deduplicated (same diameter/position as #95 except y-coordinate)
    # After deduplication we have 5 unique cylinders
    assert len(cylinders) == 5

    # Find specific cylinders by entity_id
    cyl_91 = next(f for f in cylinders if f['entity_id'] == 91)
    cyl_92 = next(f for f in cylinders if f['entity_id'] == 92)
    cyl_93 = next(f for f in cylinders if f['entity_id'] == 93)
    cyl_94 = next(f for f in cylinders if f['entity_id'] == 94)
    cyl_95 = next(f for f in cylinders if f['entity_id'] == 95)
    # cyl_96 is deduplicated (same as #95)

    # #91: Ø55 flange at z=0, OUTER
    assert cyl_91['diameter'] == 55.0
    assert cyl_91['z_position'] == 0.0
    assert cyl_91.get('is_inner') is not True
    assert 'axis_direction' in cyl_91

    # #92: Ø19 bore at z=-8.9, INNER
    assert cyl_92['diameter'] == 19.0
    assert cyl_92['z_position'] == -8.9
    assert cyl_92['is_inner'] is True

    # #93: Ø30 shaft at z=89, OUTER
    assert cyl_93['diameter'] == 30.0
    assert cyl_93['z_position'] == 89.0
    assert cyl_93.get('is_inner') is not True

    # #94: Ø27 section at z=0, OUTER
    assert cyl_94['diameter'] == 27.0
    assert cyl_94['z_position'] == 0.0
    assert cyl_94.get('is_inner') is not True

    # #95: Ø7 bolt hole at y=-20, INNER
    assert cyl_95['diameter'] == 7.0
    assert cyl_95['z_position'] == 0.0
    assert cyl_95['y_position'] == -20.0
    assert cyl_95['is_inner'] is True

    # #96 was deduplicated (same diameter, z-position, just different y-coordinate)


def test_conical_surfaces_with_positions():
    """Test conical surface parsing with exact positions and angles"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    features = result['features']
    cones = [f for f in features if f['type'] == 'cone']

    # Note: #171 is deduplicated (same as #168: r=15, 45°, z=87.5)
    assert len(cones) == 3

    # Find specific cones by entity_id
    cone_168 = next(f for f in cones if f['entity_id'] == 168)
    cone_169 = next(f for f in cones if f['entity_id'] == 169)
    cone_170 = next(f for f in cones if f['entity_id'] == 170)
    # cone_171 is deduplicated

    # #168: r=15, 45° at z=87.5
    assert cone_168['radius'] == 15.0
    assert cone_168['angle'] == 45.0
    assert cone_168['z_position'] == 87.5

    # #169: r=15, 30.96° at z=10.5
    assert cone_169['radius'] == 15.0
    assert cone_169['angle'] == pytest.approx(31.0, abs=0.1)  # 30.9637...
    assert cone_169['z_position'] == 10.5

    # #170: r=13.5, 81.87° at z=5.5
    assert cone_170['radius'] == 13.5
    assert cone_170['angle'] == pytest.approx(81.9, abs=0.1)  # 81.869...
    assert cone_170['z_position'] == 5.5

    # #171 was deduplicated (same as #168: r=15, 45°, z=87.5)


def test_toroidal_surfaces_with_positions():
    """Test toroidal (fillet) surface parsing with positions"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    features = result['features']
    tori = [f for f in features if f['type'] == 'radius']

    # Note: #89 and #90 are deduplicated (all R1.0, different z-positions)
    # After deduplication we have 1 unique torus
    assert len(tori) == 1

    # Find specific torus by entity_id
    torus_88 = next(f for f in tori if f['entity_id'] == 88)
    # torus_89 and torus_90 are deduplicated

    # #88: R1.0 at z=2.633
    assert torus_88['radius'] == 1.0
    assert torus_88['z_position'] == pytest.approx(2.633, abs=0.001)

    # #89 and #90 were deduplicated (same radius R1.0)


def test_multi_line_entity_parsing():
    """Test that multi-line entities (like CLOSED_SHELL) are parsed correctly"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    # Check that entity #87 (CLOSED_SHELL with multi-line params) was parsed
    assert 87 in parser.entities
    assert parser.entities[87]['type'] == 'CLOSED_SHELL'

    # The params should contain all face references (was split across 2 lines)
    params = parser.entities[87]['params']
    assert '#149' in params
    assert '#167' in params  # Last face ref from second line


def test_angle_units_handling():
    """Test that cone angles are NOT converted (already in degrees for AP203)"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    features = result['features']
    cones = [f for f in features if f['type'] == 'cone']

    # Cone #168 has angle 45. in STEP file
    # Old code did math.degrees(45) = 2578° (WRONG!)
    # New code uses 45 directly = 45° (CORRECT!)
    cone_168 = next(f for f in cones if f['entity_id'] == 168)
    assert cone_168['angle'] == 45.0, "Angle should be 45°, not converted to 2578°"


def test_placement_reference_chain():
    """Test that reference resolution chain works: Surface → Placement → Point"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    features = result['features']

    # Cylinder #93 → placement #379 → point #534 = (0,0,89)
    cyl_93 = next(f for f in features if f['entity_id'] == 93 and f['type'] == 'cylindrical')

    assert cyl_93['placement_id'] == 379
    assert cyl_93['z_position'] == 89.0

    # Verify the chain in parser.entities
    assert 93 in parser.entities
    assert 379 in parser.entities
    assert 534 in parser.entities

    assert parser.entities[93]['type'] == 'CYLINDRICAL_SURFACE'
    assert parser.entities[379]['type'] == 'AXIS2_PLACEMENT_3D'
    assert parser.entities[534]['type'] == 'CARTESIAN_POINT'


def test_metadata_extraction():
    """Test that STEP metadata is extracted correctly"""
    parser = StepParser()
    result = parser.parse_file('uploads/drawings/PDM-249322_03.stp')

    metadata = result['metadata']

    assert 'schema' in metadata
    assert 'AP203' in metadata['schema']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
