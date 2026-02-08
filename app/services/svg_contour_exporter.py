"""
SVG Contour Exporter — Export r(z) contour as SVG for CAM/further processing.

Exports part contour as clean SVG with:
- Red contour line
- Gray rotation axis
- Bounding box (polotovar)
- Scale and dimensions
"""

import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


def export_contour_to_svg(
    contour: List[Dict],
    step_geometry: Dict,
    output_path: Path
) -> None:
    """
    Export contour as SVG file.

    Args:
        contour: List of {"z": float, "r": float} points
        step_geometry: STEP data for reference
        output_path: Where to save SVG

    Output SVG structure:
        - Contour (red polyline)
        - Rotation axis (gray dashed line at r=0)
        - Bounding box (blue rectangle - polotovar)
        - Grid and dimensions
    """
    if len(contour) < 2:
        logger.error(f"Cannot export contour with only {len(contour)} points")
        return

    # Extract z, r coordinates
    z_values = [p["z"] for p in contour]
    r_values = [p["r"] for p in contour]

    z_min, z_max = min(z_values), max(z_values)
    r_min, r_max = 0, max(r_values)  # Always start from axis (r=0)

    # SVG canvas settings
    scale = 5  # 1mm = 5 pixels
    margin = 40

    z_span = z_max - z_min
    r_span = r_max - r_min

    canvas_width = z_span * scale + margin * 2
    canvas_height = r_span * scale + margin * 2

    # Helper: Convert (z, r) → (svg_x, svg_y)
    def to_svg(z, r):
        x = (z - z_min) * scale + margin
        y = canvas_height - ((r - r_min) * scale + margin)
        return x, y

    # Build SVG
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{canvas_width}" height="{canvas_height}"
     viewBox="0 0 {canvas_width} {canvas_height}">

  <!-- Grid -->
  <defs>
    <pattern id="grid" width="{10*scale}" height="{10*scale}" patternUnits="userSpaceOnUse">
      <path d="M {10*scale} 0 L 0 0 0 {10*scale}" fill="none" stroke="#eee" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="{canvas_width}" height="{canvas_height}" fill="url(#grid)"/>

  <!-- Rotation Axis (z-axis at r=0) -->
'''

    axis_y = to_svg(0, 0)[1]
    svg += f'''  <line x1="{margin}" y1="{axis_y}" x2="{canvas_width - margin}" y2="{axis_y}"
        stroke="gray" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
  <text x="{margin - 5}" y="{axis_y - 5}" font-size="10" fill="gray" text-anchor="end">r=0</text>

  <!-- Bounding Box (Polotovar) -->
'''

    bb_x1, bb_y1 = to_svg(z_min, r_max)
    bb_x2, bb_y2 = to_svg(z_max, 0)
    bb_width = bb_x2 - bb_x1
    bb_height = bb_y2 - bb_y1

    svg += f'''  <rect x="{bb_x1}" y="{bb_y1}" width="{bb_width}" height="{bb_height}"
        fill="none" stroke="blue" stroke-width="1" stroke-dasharray="10,5" opacity="0.3"/>
  <text x="{bb_x1 + bb_width/2}" y="{bb_y1 - 5}" font-size="10" fill="blue" text-anchor="middle">
    Polotovar Ø{r_max*2:.1f} × L{z_span:.1f}
  </text>

  <!-- Contour (Red Line) -->
  <polyline points="'''

    for point in contour:
        x, y = to_svg(point["z"], point["r"])
        svg += f"{x},{y} "

    svg += f'''" fill="none" stroke="red" stroke-width="2"/>

  <!-- Contour Points (markers) -->
'''

    for i, point in enumerate(contour):
        x, y = to_svg(point["z"], point["r"])
        svg += f'''  <circle cx="{x}" cy="{y}" r="3" fill="red"/>
  <text x="{x + 5}" y="{y - 5}" font-size="8" fill="black">
    P{i} (z={point["z"]:.1f}, r={point["r"]:.1f})
  </text>
'''

    svg += f'''
  <!-- Dimensions -->
  <text x="{margin}" y="20" font-size="12" fill="black" font-weight="bold">
    Contour: {len(contour)} points | Range: z=[{z_min:.1f}, {z_max:.1f}], r=[{r_min:.1f}, {r_max:.1f}]
  </text>

</svg>'''

    # Write SVG file
    output_path.write_text(svg, encoding='utf-8')
    logger.info(f"SVG exported: {output_path} ({len(contour)} points)")
