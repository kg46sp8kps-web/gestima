"""
Prismatic view rendering helpers — extracted from prismatic_svg_renderer.py.

Individual view rendering functions for multi-view prismatic drawings.
Extracted to keep main renderer <300 LOC (L-036).
"""
import math
from typing import Dict, List, Any, Tuple


# Dark theme colors
COLOR_OUTLINE = '#cbd5e1'      # light gray for part outline
COLOR_HIDDEN = '#475569'        # medium gray dashed for hidden lines
COLOR_POCKET = '#94a3b8'        # lighter gray for pocket outlines
COLOR_FACE_TOP = '#1e293b'      # isometric top face fill
COLOR_FACE_FRONT = '#0f172a'    # isometric front face fill (darker)
COLOR_FACE_SIDE = '#162034'     # isometric side face fill


def render_top_view(
    parts: List[str], geo: Dict, vp: Any, scale: float, zones: List
):
    """Render top view (XY plane, looking down from Z+)."""
    parts.append(f'<g id="view-top" class="view-group">')
    parts.append(_viewport_frame(vp))

    bbox = geo.get('bounding_box', {})
    length = bbox.get('length', 100)
    width = bbox.get('width', 60)
    contour = geo.get('outer_contour', [])
    pockets = geo.get('pockets', [])
    holes = geo.get('holes', [])

    # Center part in viewport
    cx = vp.x + vp.width / 2
    cy = vp.y + vp.height / 2
    ox = cx - (length * scale) / 2
    oy = cy - (width * scale) / 2

    # Default rectangular contour if none provided
    if not contour:
        contour = [
            {'x': 0, 'y': 0}, {'x': length, 'y': 0},
            {'x': length, 'y': width}, {'x': 0, 'y': width}
        ]

    # Draw outer contour
    path_d = build_path_from_points(contour, ox, oy, scale, close=True)
    parts.append(
        f'<path d="{path_d}" fill="url(#hatch-prismatic)" fill-opacity="0.3" '
        f'stroke="{COLOR_OUTLINE}" stroke-width="1.5"/>'
    )

    # Draw pockets
    for pocket in pockets:
        p_contour = pocket.get('contour', [])
        if p_contour:
            p_path = build_path_from_points(p_contour, ox, oy, scale, close=True)
            parts.append(
                f'<path d="{p_path}" fill="none" '
                f'stroke="{COLOR_POCKET}" stroke-width="1.2" stroke-dasharray="4,2"/>'
            )

    # Draw holes
    for hole in holes:
        hx = ox + hole.get('x', 0) * scale
        hy = oy + hole.get('y', 0) * scale
        hr = (hole.get('diameter', 5) / 2) * scale
        parts.append(
            f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hr:.1f}" '
            f'fill="none" stroke="{COLOR_OUTLINE}" stroke-width="1.2"/>'
        )
        # Center mark
        parts.append(
            f'<line x1="{hx-hr:.1f}" y1="{hy:.1f}" x2="{hx+hr:.1f}" y2="{hy:.1f}" '
            f'stroke="{COLOR_HIDDEN}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<line x1="{hx:.1f}" y1="{hy-hr:.1f}" x2="{hx:.1f}" y2="{hy+hr:.1f}" '
            f'stroke="{COLOR_HIDDEN}" stroke-width="0.5"/>'
        )

    parts.append('</g>')


def render_front_view(
    parts: List[str], geo: Dict, vp: Any, scale: float, zones: List
):
    """Render front view (XZ plane, looking from Y+)."""
    parts.append(f'<g id="view-front" class="view-group">')
    parts.append(_viewport_frame(vp))

    bbox = geo.get('bounding_box', {})
    length = bbox.get('length', 100)
    height = bbox.get('height', 30)
    holes = geo.get('holes', [])
    pockets = geo.get('pockets', [])

    # Center part in viewport
    cx = vp.x + vp.width / 2
    cy = vp.y + vp.height / 2
    ox = cx - (length * scale) / 2
    oy = cy - (height * scale) / 2

    # Draw front profile rectangle
    w = length * scale
    h = height * scale
    parts.append(
        f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="url(#hatch-prismatic)" fill-opacity="0.3" '
        f'stroke="{COLOR_OUTLINE}" stroke-width="1.5"/>'
    )

    # Draw through-holes as dashed vertical lines
    for hole in holes:
        hx = ox + hole.get('x', 0) * scale
        hole_depth = hole.get('depth', height)
        if hole_depth >= height:  # Through-hole
            parts.append(
                f'<line x1="{hx:.1f}" y1="{oy:.1f}" x2="{hx:.1f}" y2="{oy+h:.1f}" '
                f'stroke="{COLOR_HIDDEN}" stroke-width="1" stroke-dasharray="4,2" '
                f'class="hidden-line"/>'
            )

    # Draw pockets visible from front
    for pocket in pockets:
        p_depth = pocket.get('depth', 0)
        p_contour = pocket.get('contour', [])
        if p_contour and p_depth > 0:
            # Get X bounds from contour
            x_vals = [pt.get('x', 0) for pt in p_contour]
            if x_vals:
                x_min = min(x_vals)
                x_max = max(x_vals)
                px1 = ox + x_min * scale
                px2 = ox + x_max * scale
                pocket_h = p_depth * scale
                parts.append(
                    f'<rect x="{px1:.1f}" y="{oy:.1f}" '
                    f'width="{abs(px2-px1):.1f}" height="{pocket_h:.1f}" '
                    f'fill="none" stroke="{COLOR_POCKET}" stroke-width="1.2" '
                    f'stroke-dasharray="4,2"/>'
                )

    parts.append('</g>')


def render_side_view(
    parts: List[str], geo: Dict, vp: Any, scale: float, zones: List
):
    """Render side view (YZ plane, looking from X+)."""
    parts.append(f'<g id="view-side" class="view-group">')
    parts.append(_viewport_frame(vp))

    bbox = geo.get('bounding_box', {})
    width = bbox.get('width', 60)
    height = bbox.get('height', 30)

    # Center part in viewport
    cx = vp.x + vp.width / 2
    cy = vp.y + vp.height / 2
    ox = cx - (width * scale) / 2
    oy = cy - (height * scale) / 2

    # Draw side profile rectangle
    w = width * scale
    h = height * scale
    parts.append(
        f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="url(#hatch-prismatic)" fill-opacity="0.3" '
        f'stroke="{COLOR_OUTLINE}" stroke-width="1.5"/>'
    )

    parts.append('</g>')


def render_isometric_view(
    parts: List[str], geo: Dict, vp: Any, scale: float, zones: List
):
    """Render isometric view (30-degree projection)."""
    parts.append(f'<g id="view-iso" class="view-group">')
    parts.append(_viewport_frame(vp))

    bbox = geo.get('bounding_box', {})
    length = bbox.get('length', 100)
    width = bbox.get('width', 60)
    height = bbox.get('height', 30)

    # Center isometric in viewport
    cx = vp.x + vp.width / 2
    cy = vp.y + vp.height / 2 + 30  # Shift down slightly

    # Isometric projection helper
    def iso_proj(x: float, y: float, z: float) -> Tuple[float, float]:
        """Project 3D point to 2D isometric coordinates."""
        cos30 = math.cos(math.radians(30))
        sin30 = math.sin(math.radians(30))
        ix = (x - y) * cos30 * scale
        iy = -z * scale + (x + y) * sin30 * scale
        return cx + ix, cy + iy

    # Draw 3 visible faces: top, front, right side
    # Top face (Z+ looking down)
    top_pts = [
        iso_proj(0, 0, height),
        iso_proj(length, 0, height),
        iso_proj(length, width, height),
        iso_proj(0, width, height),
    ]
    parts.append(
        f'<path d="M {top_pts[0][0]:.1f},{top_pts[0][1]:.1f} '
        f'L {top_pts[1][0]:.1f},{top_pts[1][1]:.1f} '
        f'L {top_pts[2][0]:.1f},{top_pts[2][1]:.1f} '
        f'L {top_pts[3][0]:.1f},{top_pts[3][1]:.1f} Z" '
        f'fill="{COLOR_FACE_TOP}" stroke="{COLOR_OUTLINE}" stroke-width="1.2"/>'
    )

    # Front face (Y=0 plane)
    front_pts = [
        iso_proj(0, 0, 0),
        iso_proj(length, 0, 0),
        iso_proj(length, 0, height),
        iso_proj(0, 0, height),
    ]
    parts.append(
        f'<path d="M {front_pts[0][0]:.1f},{front_pts[0][1]:.1f} '
        f'L {front_pts[1][0]:.1f},{front_pts[1][1]:.1f} '
        f'L {front_pts[2][0]:.1f},{front_pts[2][1]:.1f} '
        f'L {front_pts[3][0]:.1f},{front_pts[3][1]:.1f} Z" '
        f'fill="{COLOR_FACE_FRONT}" stroke="{COLOR_OUTLINE}" stroke-width="1.2"/>'
    )

    # Right side face (X=length plane)
    side_pts = [
        iso_proj(length, 0, 0),
        iso_proj(length, width, 0),
        iso_proj(length, width, height),
        iso_proj(length, 0, height),
    ]
    parts.append(
        f'<path d="M {side_pts[0][0]:.1f},{side_pts[0][1]:.1f} '
        f'L {side_pts[1][0]:.1f},{side_pts[1][1]:.1f} '
        f'L {side_pts[2][0]:.1f},{side_pts[2][1]:.1f} '
        f'L {side_pts[3][0]:.1f},{side_pts[3][1]:.1f} Z" '
        f'fill="{COLOR_FACE_SIDE}" stroke="{COLOR_OUTLINE}" stroke-width="1.2"/>'
    )

    parts.append('</g>')


def _viewport_frame(vp: Any) -> str:
    """Generate viewport frame with label."""
    return (
        f'<rect x="{vp.x}" y="{vp.y}" width="{vp.width}" height="{vp.height}" '
        f'fill="none" stroke="#1a1a1a" rx="4"/>'
        f'<text class="view-label" x="{vp.x+10}" y="{vp.y+25}">{vp.label}</text>'
    )


def build_path_from_points(
    points: List[Dict], ox: float, oy: float, scale: float, close: bool = False
) -> str:
    """Build SVG path string from point array."""
    if not points:
        return ""
    d = f"M {ox + points[0].get('x', 0) * scale:.1f},{oy + points[0].get('y', 0) * scale:.1f}"
    for pt in points[1:]:
        d += f" L {ox + pt.get('x', 0) * scale:.1f},{oy + pt.get('y', 0) * scale:.1f}"
    if close:
        d += " Z"
    return d
