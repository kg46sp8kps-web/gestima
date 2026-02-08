"""
Integration test for Phase A - Feature Zone Mapping

Tests the complete flow:
1. map_features_to_zones() maps operations to zones
2. render_profile_svg() renders SVG with feature zones
3. SVG contains proper data attributes for interactivity
"""

import pytest


def test_feature_zone_mapper_rotational():
    """Test mapping rotational operations to SVG zones."""
    from app.services.feature_position_mapper import map_features_to_zones

    profile_geometry = {
        'type': 'rotational',
        'outer_contour': [
            {'r': 0, 'z': 0},
            {'r': 15, 'z': 0},
            {'r': 15, 'z': 50},
            {'r': 0, 'z': 50}
        ],
        'inner_contour': [],
        'total_length': 50,
        'max_diameter': 30
    }

    operations = [
        {
            'feature_type': 'od_rough',
            'params': {
                'from_diameter': 31,
                'to_diameter': 30,
                'length': 50
            }
        },
        {
            'feature_type': 'drill',
            'params': {
                'to_diameter': 10,
                'depth': 30
            }
        }
    ]

    zones = map_features_to_zones(profile_geometry, operations)

    assert len(zones) >= 1, "Should map at least one zone"
    assert zones[0].feature_type in ['od_rough', 'drill']
    assert zones[0].category in ['turning', 'drilling']
    assert zones[0].color.startswith('#'), "Color should be hex"
    assert zones[0].feature_index >= 0


def test_svg_with_feature_zones():
    """Test SVG rendering with feature zones."""
    from app.services.profile_svg_renderer import render_profile_svg
    from app.services.feature_position_mapper import map_features_to_zones, FeatureZone

    profile_geometry = {
        'type': 'rotational',
        'outer_contour': [
            {'r': 0, 'z': 0},
            {'r': 15, 'z': 0},
            {'r': 15, 'z': 50},
            {'r': 0, 'z': 50}
        ],
        'total_length': 50,
        'max_diameter': 30
    }

    operations = [
        {
            'feature_type': 'od_rough',
            'from_diameter': 31,
            'to_diameter': 30,
            'length': 50
        }
    ]

    zones = map_features_to_zones(profile_geometry, operations)
    svg = render_profile_svg(profile_geometry, feature_zones=zones)

    assert svg is not None
    assert '<svg' in svg
    assert 'feature-zone' in svg, "SVG should contain feature zone elements"
    assert 'data-feature-id' in svg, "SVG should have data attributes"
    assert 'data-category' in svg


def test_svg_without_feature_zones():
    """Test backward compatibility - SVG renders without zones."""
    from app.services.profile_svg_renderer import render_profile_svg

    profile_geometry = {
        'type': 'rotational',
        'outer_contour': [
            {'r': 0, 'z': 0},
            {'r': 15, 'z': 0},
            {'r': 15, 'z': 50},
            {'r': 0, 'z': 50}
        ],
        'total_length': 50,
        'max_diameter': 30
    }

    svg = render_profile_svg(profile_geometry)

    assert svg is not None
    assert '<svg' in svg
    # Should work fine without zones


def test_feature_zone_schema():
    """Test FeatureZoneSchema validation."""
    from app.schemas.feature_recognition import FeatureZoneSchema

    zone = FeatureZoneSchema(
        feature_index=0,
        feature_type='od_rough',
        category='turning',
        z_start=0,
        z_end=30,
        r_inner=14,
        r_outer=15,
        color='#2563eb',
        label='od_rough Ø30'
    )

    assert zone.feature_index == 0
    assert zone.feature_type == 'od_rough'
    assert zone.category == 'turning'
    assert zone.z_start == 0
    assert zone.z_end == 30


def test_category_color_mapping():
    """Test that all categories have colors."""
    from app.services.feature_position_mapper import CATEGORY_COLORS

    expected_categories = [
        'turning', 'drilling', 'threading', 'milling',
        'grinding', 'finishing', 'live_tooling'
    ]

    for cat in expected_categories:
        assert cat in CATEGORY_COLORS, f"Missing color for {cat}"
        assert CATEGORY_COLORS[cat].startswith('#'), f"Invalid color for {cat}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
