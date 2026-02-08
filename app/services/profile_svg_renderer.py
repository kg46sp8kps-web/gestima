"""
Profile SVG Renderer — Direct mm Coordinates (No Scaling)

Generates engineering cross-section SVG using DIRECT mm coordinates from STEP.
NO SCALING - works with precise geometry data from section_profile_extractor.

Input: profile_geometry dict with outer_contour/inner_contour point arrays
Output: SVG with viewBox set to actual mm dimensions

Key principle: Data from STEP is accurate to 0.001mm - we preserve it exactly!
"""

from typing import Dict, List, Optional

# Contour colors
COLOR_OUTER = '#1e293b'      # dark slate — outer contour stroke
COLOR_INNER = '#dc2626'      # red — inner bore contour
COLOR_HATCH = '#94a3b8'      # slate — hatch lines
COLOR_DIM = '#475569'        # dimension lines and text
COLOR_CL = '#94a3b8'         # centerline


def render_profile_svg(
    profile_geometry: Optional[Dict],
    features: List[Dict] = None,
    feature_zones: List = None
) -> Optional[str]:
    """
    Render SVG cross-section from profile_geometry using direct mm coordinates.

    Args:
        profile_geometry: Dict with outer_contour, inner_contour, max_diameter, total_length
        features: List of features (currently unused)
        feature_zones: List of feature zones for interactive overlays

    Returns:
        SVG string with viewBox set to actual part dimensions in mm
    """
    if not profile_geometry:
        return None

    part_type = profile_geometry.get('part_type', 'rotational')

    # Get contours
    outer = profile_geometry.get('outer_contour', [])
    inner = profile_geometry.get('inner_contour', [])

    if len(outer) < 3:
        return None

    # Get dimensions (direct from STEP extraction)
    total_length = profile_geometry.get('total_length', 0)
    max_diameter = profile_geometry.get('max_diameter', 0)
    max_radius = max_diameter / 2

    # Recalculate from points if missing
    if not total_length:
        all_z = [p.get('z', 0) for p in outer + inner]
        total_length = max(all_z) - min(all_z) if all_z else 0

    if not max_diameter:
        all_r = [p.get('r', 0) for p in outer]
        max_radius = max(all_r) if all_r else 0
        max_diameter = max_radius * 2

    if total_length <= 0 or max_diameter <= 0:
        return None

    # SVG viewBox in mm coordinates with minimum dimensions
    margin = 10  # mm margin around part
    min_dimension = 80  # mm minimum viewbox dimension to keep visibility

    # Calculate raw dimensions
    raw_width = total_length + 2 * margin
    raw_height = max_diameter + 2 * margin

    # Apply minimum to prevent ultra-thin SVGs
    viewbox_width = max(raw_width, min_dimension)
    viewbox_height = max(raw_height, min_dimension)

    # Center part in viewBox
    ox = (viewbox_width - total_length) / 2
    cy = viewbox_height / 2  # centerline Y

    # Build SVG
    parts = []

    # Header with viewBox in mm
    parts.append(
        f'<svg width="900" height="520" '
        f'viewBox="0 0 {viewbox_width:.2f} {viewbox_height:.2f}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid meet">'
    )

    # Defs (patterns, markers)
    parts.append(_svg_defs())

    # Background
    parts.append(
        f'<rect x="0" y="0" width="{viewbox_width:.2f}" height="{viewbox_height:.2f}" '
        f'fill="white"/>'
    )

    # Title
    parts.append(
        f'<text x="{viewbox_width / 2:.2f}" y="10" text-anchor="middle" '
        f'font-size="3" font-weight="bold" fill="#1e293b" '
        f'font-family="Inter, system-ui, sans-serif">'
        f'Profil — {part_type}</text>'
    )

    # Render rotational part
    if part_type == 'rotational':
        _render_rotational(parts, outer, inner, ox, cy, total_length, max_radius)

    parts.append('</svg>')
    return '\n'.join(parts)


def _svg_defs() -> str:
    """SVG defs: hatch pattern and arrow markers."""
    return '''
    <defs>
        <pattern id="hatch" patternUnits="userSpaceOnUse" width="2" height="2" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="2" stroke="#94a3b8" stroke-width="0.3"/>
        </pattern>
        <marker id="arrow-start" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
            <path d="M 6 1 L 2 4 L 6 7" fill="none" stroke="#475569" stroke-width="0.8"/>
        </marker>
        <marker id="arrow-end" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
            <path d="M 2 1 L 6 4 L 2 7" fill="none" stroke="#475569" stroke-width="0.8"/>
        </marker>
    </defs>
    '''


def _render_rotational(
    parts: list,
    outer: list,
    inner: list,
    ox: float,
    cy: float,
    total_length: float,
    max_radius: float
):
    """
    Render rotational part using DIRECT mm coordinates.

    Args:
        parts: SVG parts list to append to
        outer: Outer contour points [{z, r}, ...]
        inner: Inner contour points [{z, r}, ...]
        ox: Origin X offset (mm)
        cy: Centerline Y (mm)
        total_length: Total part length (mm)
        max_radius: Max radius (mm)
    """
    # Centerline
    cl_x1 = ox - 5
    cl_x2 = ox + total_length + 5
    parts.append(
        f'<line x1="{cl_x1:.2f}" y1="{cy:.2f}" '
        f'x2="{cl_x2:.2f}" y2="{cy:.2f}" '
        f'stroke="{COLOR_CL}" stroke-width="0.15" '
        f'stroke-dasharray="2,1"/>'
    )
    parts.append(
        f'<text x="{cl_x1 - 1:.2f}" y="{cy + 0.8:.2f}" '
        f'text-anchor="end" font-size="2" fill="{COLOR_CL}" '
        f'font-family="monospace">CL</text>'
    )

    # Filter outer points (skip r=0 axis points)
    outer_pts = [p for p in outer if p.get('r', 0) > 0.01]

    if not outer_pts:
        return

    # Build closed cross-section path (top half + bottom half mirrored)
    top_path = []
    bot_path = []
    for pt in outer_pts:
        px = ox + pt['z']  # DIRECT mm coordinate
        pr = pt['r']       # DIRECT mm coordinate
        top_path.append((px, cy - pr))
        bot_path.append((px, cy + pr))

    # Build right-half path: outer top → outer bottom (reversed) → close
    right_d = f"M {top_path[0][0]:.2f},{top_path[0][1]:.2f}"
    for px, py in top_path[1:]:
        right_d += f" L {px:.2f},{py:.2f}"
    # Bottom (reversed)
    for px, py in reversed(bot_path):
        right_d += f" L {px:.2f},{py:.2f}"
    right_d += " Z"

    # Outer contour with hatch fill
    parts.append(
        f'<path d="{right_d}" '
        f'fill="url(#hatch)" fill-opacity="0.4" '
        f'stroke="{COLOR_OUTER}" stroke-width="0.3" '
        f'stroke-linejoin="round"/>'
    )

    # Inner bore cutout
    inner_pts = [p for p in inner if p.get('r', 0) > 0.01]

    if inner_pts:
        inner_top = []
        inner_bot = []
        for pt in inner_pts:
            px = ox + pt['z']  # DIRECT mm
            pr = pt['r']       # DIRECT mm
            inner_top.append((px, cy - pr))
            inner_bot.append((px, cy + pr))

        # Inner path (top → bottom reversed → close)
        inner_d = f"M {inner_top[0][0]:.2f},{inner_top[0][1]:.2f}"
        for px, py in inner_top[1:]:
            inner_d += f" L {px:.2f},{py:.2f}"
        for px, py in reversed(inner_bot):
            inner_d += f" L {px:.2f},{py:.2f}"
        inner_d += " Z"

        # White fill to cut out bore
        parts.append(
            f'<path d="{inner_d}" '
            f'fill="white" '
            f'stroke="{COLOR_INNER}" stroke-width="0.25"/>'
        )

    # Diameter dimensions
    _draw_diameter_dimensions(parts, outer_pts, inner_pts, ox, cy, total_length)

    # Total length dimension
    _draw_length_dimension(parts, ox, ox + total_length, cy + max_radius + 10, total_length)


def _draw_diameter_dimensions(
    parts: list,
    outer_pts: list,
    inner_pts: list,
    ox: float,
    cy: float,
    total_length: float
):
    """Draw diameter dimension lines at stable segments."""
    if not outer_pts:
        return

    # Find STABLE diameter segments (same r for 2+ consecutive points)
    segments = []
    i = 0
    while i < len(outer_pts):
        r = outer_pts[i]['r']
        z_start = outer_pts[i]['z']
        z_end = z_start

        # Collect consecutive points with same r (±0.2mm tolerance)
        j = i + 1
        while j < len(outer_pts) and abs(outer_pts[j]['r'] - r) < 0.2:
            z_end = outer_pts[j]['z']
            j += 1

        seg_length = z_end - z_start
        if seg_length > 0.5:  # Only dimension segments longer than 0.5mm
            z_mid = (z_start + z_end) / 2
            segments.append({'r': r, 'z': z_mid, 'd': r * 2, 'len': seg_length})

        i = j if j > i else i + 1

    # Deduplicate by diameter value
    seen_d = set()
    unique_dims = []
    for dim in segments:
        d_rounded = round(dim['d'], 0)
        if d_rounded not in seen_d:
            seen_d.add(d_rounded)
            unique_dims.append(dim)

    # Draw dimension lines
    for idx, dim in enumerate(unique_dims):
        px = ox + dim['z']  # DIRECT mm
        pr = dim['r']       # DIRECT mm
        d_val = dim['d']

        # Position dimension to the right, staggered
        dim_x = px + 3 + idx * 6

        y_top = cy - pr
        y_bot = cy + pr

        # Leader lines
        parts.append(
            f'<line x1="{px:.2f}" y1="{y_top:.2f}" '
            f'x2="{dim_x:.2f}" y2="{y_top:.2f}" '
            f'stroke="#94a3b8" stroke-width="0.1" stroke-dasharray="0.5,0.5"/>'
        )
        parts.append(
            f'<line x1="{px:.2f}" y1="{y_bot:.2f}" '
            f'x2="{dim_x:.2f}" y2="{y_bot:.2f}" '
            f'stroke="#94a3b8" stroke-width="0.1" stroke-dasharray="0.5,0.5"/>'
        )

        # Vertical dimension line with arrows
        parts.append(
            f'<line x1="{dim_x:.2f}" y1="{y_top:.2f}" '
            f'x2="{dim_x:.2f}" y2="{y_bot:.2f}" '
            f'stroke="{COLOR_DIM}" stroke-width="0.2" '
            f'marker-start="url(#arrow-start)" '
            f'marker-end="url(#arrow-end)"/>'
        )

        # Label
        label_y = (y_top + y_bot) / 2
        parts.append(
            f'<text x="{dim_x + 1:.2f}" y="{label_y + 0.6:.2f}" '
            f'font-size="2" font-weight="600" fill="{COLOR_DIM}" '
            f'font-family="monospace">Ø{d_val:.0f}</text>'
        )

    # Inner bore dimension
    if inner_pts:
        ir = inner_pts[0]['r']
        iz = inner_pts[0]['z']
        px = ox + iz + 4  # DIRECT mm
        pr = ir           # DIRECT mm

        y_top = cy - pr
        y_bot = cy + pr

        parts.append(
            f'<line x1="{px:.2f}" y1="{y_top:.2f}" '
            f'x2="{px:.2f}" y2="{y_bot:.2f}" '
            f'stroke="#dc2626" stroke-width="0.2" '
            f'marker-start="url(#arrow-start)" '
            f'marker-end="url(#arrow-end)"/>'
        )
        parts.append(
            f'<text x="{px + 1:.2f}" y="{(y_top + y_bot) / 2 + 0.6:.2f}" '
            f'font-size="2" font-weight="600" fill="#dc2626" '
            f'font-family="monospace">Ø{ir * 2:.1f}</text>'
        )


def _draw_length_dimension(
    parts: list,
    x1: float,
    x2: float,
    y: float,
    length: float
):
    """Draw horizontal length dimension line."""
    parts.append(
        f'<line x1="{x1:.2f}" y1="{y:.2f}" '
        f'x2="{x2:.2f}" y2="{y:.2f}" '
        f'stroke="{COLOR_DIM}" stroke-width="0.2" '
        f'marker-start="url(#arrow-start)" '
        f'marker-end="url(#arrow-end)"/>'
    )

    # Label
    mid_x = (x1 + x2) / 2
    parts.append(
        f'<text x="{mid_x:.2f}" y="{y - 1:.2f}" '
        f'text-anchor="middle" font-size="2.5" font-weight="600" '
        f'fill="{COLOR_DIM}" font-family="monospace">{length:.1f} mm</text>'
    )
