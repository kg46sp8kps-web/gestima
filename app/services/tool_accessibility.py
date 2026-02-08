"""
Tool Accessibility & Reachability Analysis

Determines which tools can reach which features based on:
- Tool diameter vs. feature minimum radius
- Tool length vs. feature depth
- Collision with surrounding geometry

ADR-041: Manufacturing Feasibility Constraints
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Standard tool library (simplified)
TOOL_LIBRARY = {
    # Turning tools
    'TNMG_160408': {
        'type': 'turning_insert',
        'nose_radius': 0.8,  # mm
        'min_bore_diameter': 25.0,  # Cannot turn ID < 25mm
        'max_depth_of_cut': 4.0,
    },
    'TNMG_160404': {
        'type': 'turning_insert',
        'nose_radius': 0.4,
        'min_bore_diameter': 20.0,
        'max_depth_of_cut': 2.0,
    },
    # Drills
    'DRILL_3': {'type': 'drill', 'diameter': 3.0, 'max_depth': 30.0},
    'DRILL_5': {'type': 'drill', 'diameter': 5.0, 'max_depth': 50.0},
    'DRILL_8': {'type': 'drill', 'diameter': 8.0, 'max_depth': 80.0},
    'DRILL_10': {'type': 'drill', 'diameter': 10.0, 'max_depth': 100.0},
    'DRILL_12': {'type': 'drill', 'diameter': 12.0, 'max_depth': 120.0},
    # Milling cutters
    'MILL_4': {'type': 'endmill', 'diameter': 4.0, 'flute_length': 12.0, 'min_corner_radius': 2.0},
    'MILL_6': {'type': 'endmill', 'diameter': 6.0, 'flute_length': 18.0, 'min_corner_radius': 3.0},
    'MILL_8': {'type': 'endmill', 'diameter': 8.0, 'flute_length': 24.0, 'min_corner_radius': 4.0},
    'MILL_12': {'type': 'endmill', 'diameter': 12.0, 'flute_length': 36.0, 'min_corner_radius': 6.0},
    'MILL_16': {'type': 'endmill', 'diameter': 16.0, 'flute_length': 48.0, 'min_corner_radius': 8.0},
}


def check_tool_accessibility_pocket(
    pocket_faces: List[Dict],
    all_faces: List[Dict]
) -> Dict:
    """
    Check which tools can access a pocket feature.

    Returns:
        {
            'accessible': bool,
            'min_tool_diameter': float,
            'max_tool_diameter': float,
            'recommended_tools': [str],
            'limiting_factor': str,
        }
    """
    if not pocket_faces:
        return {'accessible': False, 'limiting_factor': 'no_faces'}

    # Find minimum internal radius (tightest corner)
    min_internal_radius = float('inf')
    max_depth = 0

    for face in pocket_faces:
        # Check for internal radii (fillets, corners)
        if face.get('type') == 'toroidal' and face.get('is_inner'):
            radius = face.get('radius', 0)
            if radius > 0 and radius < min_internal_radius:
                min_internal_radius = radius

        # Check depth
        z_min = face.get('z_min', 0)
        z_max = face.get('z_max', 0)
        depth = abs(z_max - z_min)
        if depth > max_depth:
            max_depth = depth

    # Tool selection constraints
    if min_internal_radius == float('inf'):
        # No internal corners detected - can use larger tools
        min_tool_diameter = 4.0
        max_tool_diameter = 16.0
    else:
        # Tool must fit in tightest corner
        min_tool_diameter = 2.0
        max_tool_diameter = min_internal_radius * 2 * 0.9  # 90% of corner radius

    # Depth constraint
    suitable_tools = []
    for tool_name, tool_spec in TOOL_LIBRARY.items():
        if tool_spec['type'] != 'endmill':
            continue

        tool_dia = tool_spec['diameter']
        tool_length = tool_spec['flute_length']

        # Check diameter fits
        if tool_dia < min_tool_diameter or tool_dia > max_tool_diameter:
            continue

        # Check length reaches
        if tool_length < max_depth:
            continue

        # Check corner radius
        min_corner = tool_spec.get('min_corner_radius', tool_dia / 2)
        if min_internal_radius != float('inf') and tool_dia / 2 > min_internal_radius:
            continue

        suitable_tools.append(tool_name)

    limiting_factor = 'none'
    if not suitable_tools:
        if min_internal_radius < 2.0:
            limiting_factor = 'corner_too_tight'
        elif max_depth > 100:
            limiting_factor = 'too_deep'
        else:
            limiting_factor = 'no_suitable_tool'

    return {
        'accessible': len(suitable_tools) > 0,
        'min_tool_diameter': round(min_tool_diameter, 1),
        'max_tool_diameter': round(max_tool_diameter, 1),
        'max_depth': round(max_depth, 1),
        'min_internal_radius': round(min_internal_radius, 1) if min_internal_radius != float('inf') else None,
        'recommended_tools': suitable_tools,
        'limiting_factor': limiting_factor,
    }


def check_tool_accessibility_bore(bore_diameter: float, bore_depth: float) -> Dict:
    """
    Check which drilling/boring tools can access a bore feature.

    Returns:
        {
            'accessible': bool,
            'recommended_operation': str,
            'recommended_tools': [str],
            'pilot_required': bool,
        }
    """
    suitable_drills = []
    for tool_name, tool_spec in TOOL_LIBRARY.items():
        if tool_spec['type'] != 'drill':
            continue

        tool_dia = tool_spec['diameter']
        tool_depth = tool_spec['max_depth']

        # Check diameter match (±0.5mm tolerance)
        if abs(tool_dia - bore_diameter) < 0.5 and tool_depth >= bore_depth:
            suitable_drills.append(tool_name)

    # Large bores need pilot + boring
    pilot_required = bore_diameter > 12.0
    operation = 'BORING' if pilot_required else 'DRILLING'

    return {
        'accessible': len(suitable_drills) > 0 or pilot_required,
        'recommended_operation': operation,
        'recommended_tools': suitable_drills if suitable_drills else ['DRILL_12', 'BORING_BAR'],
        'pilot_required': pilot_required,
        'limiting_factor': 'none' if (suitable_drills or pilot_required) else 'no_matching_drill',
    }


def analyze_feature_accessibility(
    feature_type: str,
    faces: List[Dict],
    all_faces: List[Dict]
) -> Dict:
    """
    Main entry point for tool accessibility analysis.

    Args:
        feature_type: 'pocket', 'bore', 'shaft_segment', etc.
        faces: Faces belonging to this feature
        all_faces: All faces in part (for collision detection)

    Returns:
        Accessibility analysis dict with tool recommendations
    """
    if feature_type in ('pocket_bottom', 'pocket_wall'):
        return check_tool_accessibility_pocket(faces, all_faces)
    elif feature_type == 'bore':
        # Get bore parameters from first face
        if faces:
            diameter = faces[0].get('diameter', 0)
            z_min = faces[0].get('z_min', 0)
            z_max = faces[0].get('z_max', 0)
            depth = abs(z_max - z_min)
            return check_tool_accessibility_bore(diameter, depth)

    # Default: accessible
    return {
        'accessible': True,
        'recommended_tools': [],
        'limiting_factor': 'none',
    }
