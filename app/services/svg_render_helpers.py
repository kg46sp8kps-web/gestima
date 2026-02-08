"""
SVG Render Helpers — Extracted from profile_svg_renderer.py

Helper functions for generating SVG cross-sections (dimensions, contours, SVG defs).
Extracted to keep main renderer <300 LOC (L-036).
"""

from typing import List, Dict


# Color scheme
COLOR_DIM = '#475569'        # dimension lines and text
COLOR_CL = '#94a3b8'         # centerline
COLOR_OUTER = '#1e293b'      # dark slate — outer contour stroke
COLOR_INNER = '#dc2626'      # red — inner bore contour


def sections_to_contours(sections: list) -> tuple:
    """
    Convert old section-based format to point-based contours.

    Backward compatibility: sections[] → outer_contour[] + inner_contour[]
    """
    outer = [{'r': 0, 'z': 0}]
    inner = []
    has_inner = False
    min_inner_r = float('inf')
    max_z = 0

    for sec in sections:
        x = sec.get('x', 0)
        length = sec.get('length', 0)
        od = sec.get('outer_diameter', 0)
        id_ = sec.get('inner_diameter', 0)
        end_d = sec.get('end_diameter')

        r_start = od / 2
        r_end = (end_d / 2) if end_d is not None else r_start

        # Outer contour points
        outer.append({'r': r_start, 'z': x})
        if abs(r_start - r_end) > 0.1:
            outer.append({'r': r_end, 'z': x + length})
        else:
            outer.append({'r': r_start, 'z': x + length})

        # Track inner bore
        if id_ > 0:
            has_inner = True
            min_inner_r = min(min_inner_r, id_ / 2)

        max_z = max(max_z, x + length)

    # Close outer contour
    outer.append({'r': 0, 'z': max_z})

    # Simple inner contour (constant bore if any)
    if has_inner and min_inner_r < float('inf'):
        inner = [
            {'r': min_inner_r, 'z': 0},
            {'r': min_inner_r, 'z': max_z}
        ]

    return outer, inner


def draw_contour_dimensions(
    parts: list, outer_pts: list, inner_pts: list,
    ox: float, cy: float, scale_x: float, scale_y: float
):
    """Draw diameter dimension lines at significant (stable) diameters only."""
    if not outer_pts:
        return

    # Find STABLE diameter segments (same r for at least 2 consecutive points
    # or first/last non-zero point). Skip transitional points on cones.
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

    # Draw dimension lines for each unique diameter
    for idx, dim in enumerate(unique_dims):
        px = ox + dim['z'] * scale_x
        pr = dim['r'] * scale_x
        d_val = dim['d']

        # Position dimension to the right of part, staggered
        dim_x = px + 15 + idx * 30

        y_top = cy - pr
        y_bot = cy + pr

        # Leader lines
        parts.append(
            f'<line x1="{px:.1f}" y1="{y_top:.1f}" '
            f'x2="{dim_x:.1f}" y2="{y_top:.1f}" '
            f'stroke="#94a3b8" stroke-width="0.5" stroke-dasharray="2,2"/>'
        )
        parts.append(
            f'<line x1="{px:.1f}" y1="{y_bot:.1f}" '
            f'x2="{dim_x:.1f}" y2="{y_bot:.1f}" '
            f'stroke="#94a3b8" stroke-width="0.5" stroke-dasharray="2,2"/>'
        )

        # Vertical dimension line with arrows
        parts.append(
            f'<line x1="{dim_x:.1f}" y1="{y_top:.1f}" '
            f'x2="{dim_x:.1f}" y2="{y_bot:.1f}" '
            f'stroke="{COLOR_DIM}" stroke-width="1" '
            f'marker-start="url(#arrow-start)" '
            f'marker-end="url(#arrow-end)"/>'
        )

        # Label
        label_y = (y_top + y_bot) / 2
        parts.append(
            f'<text x="{dim_x + 6:.1f}" y="{label_y + 4:.1f}" '
            f'font-size="11" font-weight="600" fill="{COLOR_DIM}" '
            f'font-family="monospace">Ø{d_val:.0f}</text>'
        )

    # Inner bore dimension
    if inner_pts:
        # Use the first inner point's radius
        ir = inner_pts[0]['r']
        iz = inner_pts[0]['z']
        px = ox + iz * scale_x + 20
        pr = ir * scale_x

        y_top = cy - pr
        y_bot = cy + pr

        parts.append(
            f'<line x1="{px:.1f}" y1="{y_top:.1f}" '
            f'x2="{px:.1f}" y2="{y_bot:.1f}" '
            f'stroke="#dc2626" stroke-width="1" '
            f'marker-start="url(#arrow-start)" '
            f'marker-end="url(#arrow-end)"/>'
        )
        parts.append(
            f'<text x="{px + 6:.1f}" y="{(y_top + y_bot) / 2 + 4:.1f}" '
            f'font-size="11" font-weight="600" fill="#dc2626" '
            f'font-family="monospace">Ø{ir * 2:.0f}</text>'
        )


def draw_total_length(
    parts: list, x1: float, x2: float, y: float, total_length: float
):
    """Draw total length dimension line at the bottom."""
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y - 10:.1f}" '
        f'x2="{x1:.1f}" y2="{y + 5:.1f}" '
        f'stroke="#1e293b" stroke-width="0.8"/>'
    )
    parts.append(
        f'<line x1="{x2:.1f}" y1="{y - 10:.1f}" '
        f'x2="{x2:.1f}" y2="{y + 5:.1f}" '
        f'stroke="#1e293b" stroke-width="0.8"/>'
    )
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y:.1f}" '
        f'x2="{x2:.1f}" y2="{y:.1f}" '
        f'stroke="#1e293b" stroke-width="1.5" '
        f'marker-start="url(#arrow-start)" '
        f'marker-end="url(#arrow-end)"/>'
    )
    mid_x = (x1 + x2) / 2
    parts.append(
        f'<rect x="{mid_x - 30:.1f}" y="{y - 14:.1f}" '
        f'width="60" height="16" fill="#fafbfc" rx="2"/>'
    )
    parts.append(
        f'<text x="{mid_x:.1f}" y="{y:.1f}" '
        f'text-anchor="middle" font-size="12" font-weight="bold" '
        f'fill="#1e293b" font-family="monospace">{total_length}</text>'
    )


def svg_header(width: int, height: int) -> str:
    """Generate SVG header with viewBox."""
    return (
        f'<svg width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'style="font-family: Inter, system-ui, sans-serif;">'
    )


def svg_defs() -> str:
    """Generate SVG <defs> with markers, patterns, and CSS."""
    return '''<defs>
  <marker id="arrow-start" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto">
    <polygon points="8,0 0,3 8,6" fill="#475569"/>
  </marker>
  <marker id="arrow-end" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0,0 8,3 0,6" fill="#475569"/>
  </marker>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="5" stroke="#94a3b8" stroke-width="0.4"/>
  </pattern>
  <style>
    .feature-zone { transition: fill-opacity 0.15s ease; }
    .feature-zone:hover { fill-opacity: 0.35; }
    .feature-zone--highlighted { fill-opacity: 0.4; stroke-width: 2; }
    .feature-zone--selected { fill-opacity: 0.5; stroke-width: 2; stroke-dasharray: none; }
  </style>
</defs>'''


def svg_background(width: int, height: int) -> str:
    """Generate SVG background with rounded border."""
    return (
        f'<rect width="{width}" height="{height}" fill="#fafbfc" rx="8"/>'
        f'<rect x="2" y="2" width="{width - 4}" height="{height - 4}" '
        f'fill="none" stroke="#e2e8f0" stroke-width="1" rx="6"/>'
    )


def render_prismatic(
    parts: list, geo: dict,
    ox: float, cy: float, scale: float,
    svg_width: int
):
    """Render prismatic part: top view outline with features."""
    bbox = geo.get('bounding_box', {})
    contour = geo.get('outer_contour', [])
    holes = geo.get('holes', [])

    if not contour and bbox:
        # Generate rectangle from bounding box
        w = bbox.get('length', 100)
        h = bbox.get('width', 50)
        contour = [
            {'x': 0, 'y': 0}, {'x': w, 'y': 0},
            {'x': w, 'y': h}, {'x': 0, 'y': h}
        ]

    if not contour:
        return

    # Draw outline
    d = f"M {ox + contour[0].get('x', 0) * scale_x:.1f}," \
        f"{cy - contour[0].get('y', 0) * scale_x + 50:.1f}"
    for pt in contour[1:]:
        d += f" L {ox + pt.get('x', 0) * scale_x:.1f}," \
             f"{cy - pt.get('y', 0) * scale_x + 50:.1f}"
    d += " Z"

    parts.append(
        f'<path d="{d}" fill="url(#hatch)" fill-opacity="0.3" '
        f'stroke="{COLOR_OUTER}" stroke-width="1.5"/>'
    )

    # Draw holes
    for hole in holes:
        hx = ox + hole.get('x', 0) * scale_x
        hy = cy - hole.get('y', 0) * scale_x + 50
        hr = (hole.get('diameter', 5) / 2) * scale_x
        parts.append(
            f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hr:.1f}" '
            f'fill="white" stroke="{COLOR_INNER}" stroke-width="1.2"/>'
        )


def render_feature_zones(parts: list, zones: List, scale: float, ox: float, cy: float):
    """
    Render colored semi-transparent overlay zones for each feature.

    Args:
        parts: SVG parts list to append to
        zones: List of FeatureZone objects
        scale: Scaling factor for coordinates
        ox: X offset for part origin
        cy: Centerline Y coordinate
    """
    parts.append('<g class="feature-zones">')

    for zone in zones:
        if zone.z_start is not None and zone.z_end is not None:
            # Rotational: rect from z_start to z_end, r_inner to r_outer
            x1 = ox + zone.z_start * scale_x
            x2 = ox + zone.z_end * scale_x
            r_out = (zone.r_outer or 0) * scale_x
            r_in = (zone.r_inner or 0) * scale_x

            # Top half rect
            y_top = cy - r_out
            h = r_out - r_in
            if h > 0.5:  # Only render if height > 0.5px
                parts.append(
                    f'<rect x="{x1:.1f}" y="{y_top:.1f}" '
                    f'width="{abs(x2-x1):.1f}" height="{h:.1f}" '
                    f'fill="{zone.color}" fill-opacity="0.15" '
                    f'stroke="{zone.color}" stroke-opacity="0.3" stroke-width="0.5" '
                    f'class="feature-zone feature-zone--{zone.category}" '
                    f'data-feature-id="{zone.feature_index}" '
                    f'data-feature-type="{zone.feature_type}" '
                    f'data-category="{zone.category}" '
                    f'style="cursor: pointer;" />'
                )

            # Bottom half rect (mirrored)
            y_bot = cy + r_in
            if h > 0.5:  # Only render if height > 0.5px
                parts.append(
                    f'<rect x="{x1:.1f}" y="{y_bot:.1f}" '
                    f'width="{abs(x2-x1):.1f}" height="{h:.1f}" '
                    f'fill="{zone.color}" fill-opacity="0.15" '
                    f'stroke="{zone.color}" stroke-opacity="0.3" stroke-width="0.5" '
                    f'class="feature-zone feature-zone--{zone.category}" '
                    f'data-feature-id="{zone.feature_index}" '
                    f'data-feature-type="{zone.feature_type}" '
                    f'data-category="{zone.category}" '
                    f'style="cursor: pointer;" />'
                )

        elif zone.radius is not None:
            # Prismatic hole
            cx = ox + (zone.x or 0) * scale_x
            cy_h = cy + (zone.y or 0) * scale_x
            r = zone.radius * scale_x
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy_h:.1f}" r="{r:.1f}" '
                f'fill="{zone.color}" fill-opacity="0.15" '
                f'stroke="{zone.color}" stroke-opacity="0.4" stroke-width="1" '
                f'class="feature-zone feature-zone--{zone.category}" '
                f'data-feature-id="{zone.feature_index}" '
                f'data-feature-type="{zone.feature_type}" '
                f'data-category="{zone.category}" '
                f'style="cursor: pointer;" />'
            )

        elif zone.width is not None and zone.height is not None:
            # Prismatic pocket/slot
            x = ox + (zone.x or 0) * scale_x
            y = cy + (zone.y or 0) * scale_x
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{zone.width * scale_x:.1f}" height="{zone.height * scale_x:.1f}" '
                f'fill="{zone.color}" fill-opacity="0.15" '
                f'stroke="{zone.color}" stroke-opacity="0.4" stroke-width="1" '
                f'stroke-dasharray="4,2" '
                f'class="feature-zone feature-zone--{zone.category}" '
                f'data-feature-id="{zone.feature_index}" '
                f'data-feature-type="{zone.feature_type}" '
                f'data-category="{zone.category}" '
                f'style="cursor: pointer;" />'
            )

    parts.append('</g>')
