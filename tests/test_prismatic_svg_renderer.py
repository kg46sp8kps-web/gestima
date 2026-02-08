"""
Tests for prismatic multi-view SVG renderer.

Covers:
- Multi-view rendering (top, front, side, isometric)
- Integration with profile_svg_renderer router
- Feature zones overlay
- Backward compatibility with rotational parts
"""
import pytest
from app.services.prismatic_svg_renderer import render_prismatic_multiview
from app.services.profile_svg_renderer import render_profile_svg


@pytest.fixture
def sample_prismatic_geometry():
    """Sample prismatic part geometry."""
    return {
        'type': 'prismatic',
        'bounding_box': {'length': 100, 'width': 60, 'height': 30},
        'outer_contour': [
            {'x': 0, 'y': 0}, {'x': 100, 'y': 0},
            {'x': 100, 'y': 60}, {'x': 0, 'y': 60}
        ],
        'pockets': [{
            'contour': [
                {'x': 20, 'y': 15}, {'x': 80, 'y': 15},
                {'x': 80, 'y': 45}, {'x': 20, 'y': 45}
            ],
            'depth': 10
        }],
        'holes': [
            {'x': 10, 'y': 30, 'diameter': 8, 'depth': 30},
            {'x': 90, 'y': 30, 'diameter': 8, 'depth': 30}
        ]
    }


@pytest.fixture
def sample_rotational_geometry():
    """Sample rotational part geometry."""
    return {
        'type': 'rotational',
        'total_length': 100,
        'max_diameter': 50,
        'outer_contour': [
            {'r': 0, 'z': 0}, {'r': 25, 'z': 0}, {'r': 25, 'z': 50},
            {'r': 15, 'z': 50}, {'r': 15, 'z': 100}, {'r': 0, 'z': 100}
        ],
        'inner_contour': []
    }


def test_multiview_renderer_basic(sample_prismatic_geometry):
    """Test basic multi-view rendering."""
    svg = render_prismatic_multiview(sample_prismatic_geometry)

    assert svg is not None
    assert isinstance(svg, str)
    assert len(svg) > 0

    # Check SVG structure
    assert '<svg width="900" height="700"' in svg
    assert 'viewBox="0 0 900 700"' in svg
    assert '</svg>' in svg


def test_multiview_has_all_views(sample_prismatic_geometry):
    """Test that all 4 views are rendered."""
    svg = render_prismatic_multiview(sample_prismatic_geometry)

    # Check view groups
    assert 'id="view-top"' in svg
    assert 'id="view-front"' in svg
    assert 'id="view-side"' in svg
    assert 'id="view-iso"' in svg

    # Check view labels
    assert 'TOP VIEW' in svg
    assert 'FRONT VIEW' in svg
    assert 'SIDE VIEW' in svg
    assert 'ISOMETRIC' in svg


def test_multiview_renders_features(sample_prismatic_geometry):
    """Test that holes and pockets are rendered."""
    svg = render_prismatic_multiview(sample_prismatic_geometry)

    # Holes should be rendered as circles
    assert '<circle' in svg

    # Should have hatch pattern
    assert 'hatch-prismatic' in svg


def test_multiview_minimal_geometry():
    """Test with minimal bounding box only."""
    geo = {
        'type': 'prismatic',
        'bounding_box': {'length': 50, 'width': 30, 'height': 20}
    }

    svg = render_prismatic_multiview(geo)
    assert svg is not None
    assert 'view-top' in svg


def test_multiview_returns_none_for_empty_geometry():
    """Test that empty geometry returns None."""
    svg = render_prismatic_multiview({})
    assert svg is None


def test_multiview_error_handling():
    """Test error handling for invalid geometry."""
    geo = {
        'type': 'prismatic',
        'bounding_box': None  # Invalid
    }

    svg = render_prismatic_multiview(geo)
    # Returns None for invalid geometry (caught by early return)
    assert svg is None


def test_profile_svg_router_prismatic(sample_prismatic_geometry):
    """Test that profile_svg_renderer routes prismatic parts to multiview."""
    svg = render_profile_svg(sample_prismatic_geometry)

    assert svg is not None
    # Should use multiview renderer (has view-top)
    assert 'view-top' in svg
    assert 'view-iso' in svg


def test_profile_svg_router_rotational(sample_rotational_geometry):
    """Test that profile_svg_renderer still handles rotational parts."""
    svg = render_profile_svg(sample_rotational_geometry)

    assert svg is not None
    # Should NOT use multiview renderer
    assert 'view-top' not in svg
    # Should have rotational cross-section elements
    assert '<path' in svg


def test_backward_compatibility_rotational_not_multiview(sample_rotational_geometry):
    """Ensure rotational parts don't accidentally use multiview renderer."""
    svg = render_profile_svg(sample_rotational_geometry)

    # Rotational should have centerline (CL)
    assert 'CL' in svg or 'centerline' in svg.lower()
    # Should NOT have multiview labels
    assert 'TOP VIEW' not in svg
    assert 'ISOMETRIC' not in svg


def test_multiview_with_feature_zones(sample_prismatic_geometry):
    """Test multiview rendering with feature zones."""
    # Mock feature zones (real zones come from feature_position_mapper)
    from dataclasses import dataclass

    @dataclass
    class MockFeatureZone:
        feature_index: int = 0
        feature_type: str = 'hole'
        category: str = 'machining'
        color: str = '#3b82f6'
        x: float = 10
        y: float = 30
        radius: float = 4

    zones = [MockFeatureZone()]

    svg = render_prismatic_multiview(sample_prismatic_geometry, feature_zones=zones)
    assert svg is not None
    # Feature zones rendering would be implemented in future
    # For now just ensure it doesn't crash
