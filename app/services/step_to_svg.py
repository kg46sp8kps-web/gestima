"""
STEP to SVG Converter

Converts STEP geometry features to SVG visualization for UI display.
Shows 2D cross-section/profile view of the part.
"""

import math
from typing import Dict, List, Tuple, Optional


def step_features_to_svg(features: List[Dict], metadata: Dict = None) -> str:
    """
    Convert STEP features to SVG visualization.

    Creates a 2D profile/cross-section view showing:
    - Cylindrical surfaces (holes, shafts)
    - Conical surfaces (tapers)
    - Radii/fillets

    Args:
        features: List of STEP features from StepParser
        metadata: Optional metadata (bounding box, etc.)

    Returns:
        SVG markup string
    """
    if not features:
        return _empty_svg()

    # Calculate bounding box from features
    bbox = _calculate_bounding_box(features)

    # SVG dimensions
    svg_width = 800
    svg_height = 600
    margin = 50

    # Scale to fit
    scale, offset_x, offset_y = _calculate_scale(
        bbox, svg_width - 2*margin, svg_height - 2*margin
    )

    # Build SVG
    svg_parts = []

    # SVG header
    svg_parts.append(f'''<svg width="{svg_width}" height="{svg_height}"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">

        <!-- Background -->
        <rect width="{svg_width}" height="{svg_height}" fill="#f8f9fa"/>

        <!-- Grid -->
        {_draw_grid(svg_width, svg_height, margin)}

        <!-- Coordinate system indicator -->
        <g transform="translate({margin}, {svg_height - margin})">
            <!-- X axis -->
            <line x1="0" y1="0" x2="100" y2="0" stroke="#666" stroke-width="2" marker-end="url(#arrowX)"/>
            <text x="110" y="5" fill="#666" font-size="14">X</text>

            <!-- Y axis -->
            <line x1="0" y1="0" x2="0" y2="-100" stroke="#666" stroke-width="2" marker-end="url(#arrowY)"/>
            <text x="-5" y="-110" fill="#666" font-size="14">Y</text>
        </g>

        <!-- Arrow markers -->
        <defs>
            <marker id="arrowX" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0 0, 10 3, 0 6" fill="#666"/>
            </marker>
            <marker id="arrowY" markerWidth="10" markerHeight="10" refX="3" refY="1" orient="auto">
                <polygon points="0 0, 6 10, 3 0" fill="#666"/>
            </marker>
        </defs>

        <!-- Part outline (profile view) -->
        <g transform="translate({margin + offset_x}, {margin + offset_y})">
    ''')

    # Draw features
    for i, feature in enumerate(features):
        feature_svg = _render_feature(feature, scale, i)
        if feature_svg:
            svg_parts.append(feature_svg)

    # Add dimension annotations
    svg_parts.append(_draw_dimensions(features, scale))

    # Close SVG
    svg_parts.append('''
        </g>

        <!-- Legend -->
        {legend}

    </svg>
    '''.format(legend=_draw_legend(features, svg_width, svg_height)))

    return '\n'.join(svg_parts)


def _calculate_bounding_box(features: List[Dict]) -> Dict:
    """Calculate bounding box from features"""
    max_diameter = 0
    total_length = 0

    for f in features:
        # Diameter-based features
        if 'diameter' in f:
            max_diameter = max(max_diameter, f['diameter'])
        elif 'radius' in f:
            max_diameter = max(max_diameter, f['radius'] * 2)

    # Assume rotational part (lathe)
    # Max diameter = width, estimate length
    estimated_length = max_diameter * 2  # Rough estimate

    return {
        'width': max_diameter,
        'height': estimated_length,
        'max_diameter': max_diameter
    }


def _calculate_scale(bbox: Dict, target_width: float, target_height: float) -> Tuple[float, float, float]:
    """Calculate scale and offsets to fit bbox in target size"""

    width = bbox['width'] or 100
    height = bbox['height'] or 100

    scale_x = target_width / width if width > 0 else 1
    scale_y = target_height / height if height > 0 else 1

    # Use smaller scale to fit both dimensions
    scale = min(scale_x, scale_y) * 0.8  # 80% to leave some margin

    # Center offsets
    offset_x = (target_width - width * scale) / 2
    offset_y = (target_height - height * scale) / 2

    return scale, offset_x, offset_y


def _render_feature(feature: Dict, scale: float, index: int) -> str:
    """Render a single feature as SVG"""

    feature_type = feature.get('type')

    if feature_type in ['cylindrical', 'hole']:
        # Draw as circle (end view) or rectangle (side view)
        diameter = feature.get('diameter', 0)
        radius = diameter / 2

        # Side view: rectangle
        y_pos = index * 15 * scale  # Stack features vertically

        return f'''
        <!-- {feature_type}: Ø{diameter} -->
        <rect
            x="0"
            y="{y_pos}"
            width="{diameter * scale}"
            height="10"
            fill="none"
            stroke="#2563eb"
            stroke-width="2"
            opacity="0.7"
        />
        <circle
            cx="{radius * scale}"
            cy="{y_pos + 5}"
            r="3"
            fill="#2563eb"
        />
        <text
            x="{diameter * scale + 10}"
            y="{y_pos + 8}"
            font-size="12"
            fill="#1e40af"
        >Ø{diameter}</text>
        '''

    elif feature_type == 'cone':
        # Draw as trapezoid
        angle = feature.get('angle', 45)
        radius = feature.get('radius', 10)

        y_pos = index * 20 * scale
        width = radius * 2 * scale
        height = 15

        # Calculate trapezoid points
        angle_rad = math.radians(angle)
        offset = height * math.tan(angle_rad)

        points = f"0,{y_pos} {width},{y_pos} {width-offset},{y_pos+height} {offset},{y_pos+height}"

        return f'''
        <!-- cone: {angle}° -->
        <polygon
            points="{points}"
            fill="none"
            stroke="#dc2626"
            stroke-width="2"
            opacity="0.7"
        />
        <text
            x="{width + 10}"
            y="{y_pos + 10}"
            font-size="12"
            fill="#991b1b"
        >{angle}°</text>
        '''

    elif feature_type == 'radius':
        # Draw as arc
        radius_val = feature.get('radius', 1)

        y_pos = index * 10 * scale
        r = radius_val * scale

        return f'''
        <!-- radius: R{radius_val} -->
        <path
            d="M 0,{y_pos} Q {r},{y_pos} {r},{y_pos + r}"
            fill="none"
            stroke="#16a34a"
            stroke-width="2"
            opacity="0.7"
        />
        <text
            x="{r + 10}"
            y="{y_pos + 8}"
            font-size="12"
            fill="#15803d"
        >R{radius_val}</text>
        '''

    return ''


def _draw_dimensions(features: List[Dict], scale: float) -> str:
    """Draw dimension lines and annotations"""
    # TODO: Add dimension lines between features
    return ''


def _draw_legend(features: List[Dict], svg_width: int, svg_height: int) -> str:
    """Draw legend showing feature types"""

    legend_items = []
    legend_y = 20

    # Count feature types
    feature_counts = {}
    for f in features:
        ftype = f.get('type', 'unknown')
        feature_counts[ftype] = feature_counts.get(ftype, 0) + 1

    legend_items.append(f'''
    <g transform="translate({svg_width - 200}, {legend_y})">
        <rect x="0" y="0" width="180" height="{len(feature_counts) * 25 + 40}"
              fill="white" stroke="#ddd" stroke-width="1" rx="5"/>
        <text x="10" y="20" font-weight="bold" font-size="14">Features Detected</text>
    ''')

    colors = {
        'cylindrical': '#2563eb',
        'hole': '#2563eb',
        'cone': '#dc2626',
        'radius': '#16a34a'
    }

    y_offset = 40
    for ftype, count in feature_counts.items():
        color = colors.get(ftype, '#666')
        legend_items.append(f'''
        <circle cx="15" cy="{y_offset}" r="5" fill="{color}"/>
        <text x="30" y="{y_offset + 5}" font-size="12">{ftype}: {count}</text>
        ''')
        y_offset += 25

    legend_items.append('</g>')

    return '\n'.join(legend_items)


def _draw_grid(width: int, height: int, margin: int) -> str:
    """Draw background grid"""
    lines = []

    # Vertical lines
    for x in range(margin, width - margin, 50):
        lines.append(f'<line x1="{x}" y1="{margin}" x2="{x}" y2="{height-margin}" stroke="#e5e7eb" stroke-width="1"/>')

    # Horizontal lines
    for y in range(margin, height - margin, 50):
        lines.append(f'<line x1="{margin}" y1="{y}" x2="{width-margin}" y2="{y}" stroke="#e5e7eb" stroke-width="1"/>')

    return '\n'.join(lines)


def _empty_svg() -> str:
    """Return empty SVG placeholder"""
    return '''
    <svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
        <rect width="800" height="600" fill="#f8f9fa"/>
        <text x="400" y="300" text-anchor="middle" font-size="16" fill="#666">
            No geometry features detected
        </text>
    </svg>
    '''
