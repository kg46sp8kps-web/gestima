"""
Multi-view prismatic SVG renderer.

Generates engineering-style multi-view drawings for prismatic (milled) parts:
- Top View (XY plane - looking down from Z+)
- Front View (XZ plane - looking from Y+)
- Side View (YZ plane - looking from X+)
- Isometric View (30-degree projection)

All views include feature zone overlays with data-feature-id attributes
for interactive highlighting.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.services.prismatic_view_helpers import (
    render_top_view,
    render_front_view,
    render_side_view,
    render_isometric_view,
)


@dataclass
class ViewPort:
    """Defines a viewport region in the SVG."""
    x: float       # viewport origin X in SVG coords
    y: float       # viewport origin Y in SVG coords
    width: float   # viewport width
    height: float  # viewport height
    label: str     # view label


def render_prismatic_multiview(
    profile_geometry: Dict[str, Any],
    feature_zones: List = None,
    active_view: str = 'all'
) -> Optional[str]:
    """
    Render prismatic part in multiple views.

    Args:
        profile_geometry: Dict with bounding_box, outer_contour, pockets, holes
        feature_zones: List of FeatureZone objects for interactive overlays
        active_view: 'all', 'top', 'front', 'side', 'iso'

    Returns:
        SVG string with all views embedded as <g> groups
    """
    try:
        bbox = profile_geometry.get('bounding_box', {})
        if not bbox:
            return None

        length = bbox.get('length', 100)
        width = bbox.get('width', 60)
        height = bbox.get('height', 30)

        # SVG canvas size
        svg_width = 900
        svg_height = 700

        # Define viewports (each 430x330 with 10px margin)
        viewports = {
            'top': ViewPort(10, 10, 430, 330, 'TOP VIEW'),
            'iso': ViewPort(460, 10, 430, 330, 'ISOMETRIC'),
            'front': ViewPort(10, 360, 430, 330, 'FRONT VIEW'),
            'side': ViewPort(460, 360, 430, 330, 'SIDE VIEW'),
        }

        parts = []
        parts.append(_svg_header(svg_width, svg_height))
        parts.append(_svg_defs())
        parts.append(_svg_background(svg_width, svg_height))

        # Calculate scale (fit largest dimension to viewport with 20% margin)
        max_dim = max(length, width, height)
        vp_inner_size = 300  # viewport inner drawing area
        scale = (vp_inner_size / max_dim) * 0.8 if max_dim > 0 else 1.0

        # Render each view
        if active_view in ['all', 'top']:
            render_top_view(parts, profile_geometry, viewports['top'], scale, feature_zones)

        if active_view in ['all', 'iso']:
            render_isometric_view(parts, profile_geometry, viewports['iso'], scale, feature_zones)

        if active_view in ['all', 'front']:
            render_front_view(parts, profile_geometry, viewports['front'], scale, feature_zones)

        if active_view in ['all', 'side']:
            render_side_view(parts, profile_geometry, viewports['side'], scale, feature_zones)

        parts.append('</svg>')
        return '\n'.join(parts)

    except Exception as e:
        # Fallback: return simple error SVG
        return (
            f'<svg width="900" height="700" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="900" height="700" fill="#0a0a0a"/>'
            f'<text x="450" y="350" text-anchor="middle" fill="#dc2626" '
            f'font-family="monospace" font-size="14">'
            f'Error rendering prismatic view: {str(e)}</text></svg>'
        )




def _svg_header(width: int, height: int) -> str:
    """Generate SVG header."""
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
    )


def _svg_defs() -> str:
    """Generate SVG <defs> with styles and patterns."""
    return '''<defs>
  <style>
    .feature-zone { transition: fill-opacity 0.15s ease; cursor: pointer; }
    .feature-zone:hover { fill-opacity: 0.35; }
    .feature-zone--highlighted { fill-opacity: 0.4; stroke-width: 2; }
    .feature-zone--selected { fill-opacity: 0.5; stroke-width: 2; }
    .view-label { font-family: Inter, sans-serif; font-size: 14px; fill: #94a3b8; font-weight: 600; }
    .dim-text { font-family: Inter, sans-serif; font-size: 11px; fill: #64748b; }
    .hidden-line { stroke-dasharray: 4,2; }
  </style>
  <pattern id="hatch-prismatic" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="5" stroke="#475569" stroke-width="0.4"/>
  </pattern>
  <marker id="arr-s" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto">
    <polygon points="8,0 0,3 8,6" fill="#64748b"/>
  </marker>
  <marker id="arr-e" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0,0 8,3 0,6" fill="#64748b"/>
  </marker>
</defs>'''


def _svg_background(width: int, height: int) -> str:
    """Generate dark theme background."""
    return (
        f'<rect width="{width}" height="{height}" fill="#0a0a0a" rx="8"/>'
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" '
        f'fill="none" stroke="#2a2a2a" rx="8"/>'
    )
