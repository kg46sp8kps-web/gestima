"""
Feature Position Mapper — Maps operations to SVG coordinate zones

Maps manufacturing operations (features) to SVG coordinate zones for interactive
visualization. Supports rotational (turning) and prismatic (milling) parts.

Architecture:
- Input: profile_geometry (contour points) + operations (feature list)
- Output: List of FeatureZone dataclasses with SVG coordinates and colors
- Matching: Diameter/position matching for rotational, dimension matching for prismatic
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging

from app.services.feature_definitions import FEATURE_FIELDS

logger = logging.getLogger(__name__)

CATEGORY_COLORS = {
    "turning": "#2563eb",       # blue
    "drilling": "#dc2626",      # red
    "threading": "#059669",     # green
    "milling": "#d97706",       # orange
    "grinding": "#7c3aed",      # purple
    "finishing": "#6b7280",     # gray
    "live_tooling": "#ec4899",  # pink
    "logistics": "#6b7280",     # gray
    "grooving": "#0891b2",      # cyan
    "parting": "#dc2626",       # red
}


@dataclass
class FeatureZone:
    """Feature zone overlay for SVG interactivity."""
    feature_index: int
    feature_type: str
    category: str
    z_start: Optional[float] = None
    z_end: Optional[float] = None
    r_inner: Optional[float] = None
    r_outer: Optional[float] = None
    # For prismatic
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None  # for holes
    color: str = ""
    label: str = ""


def map_features_to_zones(
    profile_geometry: Dict[str, Any],
    operations: List[Dict[str, Any]]
) -> List[FeatureZone]:
    """
    Map operations to SVG coordinate zones using geometry matching.

    Args:
        profile_geometry: Structured geometry (outer_contour, inner_contour, etc.)
        operations: List of operation dicts with feature_type, dimensions, etc.

    Returns:
        List of FeatureZone objects with SVG coordinates and colors
    """
    if not profile_geometry or not operations:
        return []

    part_type = profile_geometry.get('type', 'rotational')

    if part_type == 'rotational':
        return _map_rotational_features(profile_geometry, operations)
    else:
        return _map_prismatic_features(profile_geometry, operations)


def _map_rotational_features(
    geo: Dict[str, Any],
    operations: List[Dict[str, Any]]
) -> List[FeatureZone]:
    """Map rotational part features (turning, drilling on lathe)."""
    zones = []
    outer_contour = geo.get('outer_contour', [])
    inner_contour = geo.get('inner_contour', [])

    if not outer_contour:
        return zones

    # Parse outer contour into segments (consecutive points with stable r)
    outer_segments = _parse_contour_segments(outer_contour)
    inner_segments = _parse_contour_segments(inner_contour)

    total_length = geo.get('total_length', 0)
    max_diameter = geo.get('max_diameter', 0)

    for idx, op in enumerate(operations):
        try:
            zone = _match_rotational_operation(
                op, idx, outer_segments, inner_segments, total_length, max_diameter
            )
            if zone:
                zones.append(zone)
        except Exception as e:
            logger.warning(f"Failed to map operation {idx}: {e}")
            continue

    return zones


def _parse_contour_segments(contour: List[Dict]) -> List[Dict]:
    """
    Parse contour into segments with stable diameter.

    Returns list of {r, z_start, z_end} segments.
    """
    segments = []
    if not contour:
        return segments

    i = 0
    while i < len(contour):
        r = contour[i].get('r', 0)
        z_start = contour[i].get('z', 0)
        z_end = z_start

        # Collect consecutive points with same r (±0.2mm tolerance)
        j = i + 1
        while j < len(contour) and abs(contour[j].get('r', 0) - r) < 0.2:
            z_end = contour[j].get('z', z_end)
            j += 1

        if z_end - z_start > 0.1:  # Segment length > 0.1mm
            segments.append({'r': r, 'z_start': z_start, 'z_end': z_end})

        i = j if j > i else i + 1

    return segments


def _match_rotational_operation(
    op: Dict[str, Any],
    idx: int,
    outer_segments: List[Dict],
    inner_segments: List[Dict],
    total_length: float,
    max_diameter: float
) -> Optional[FeatureZone]:
    """Match single rotational operation to geometry zone."""
    feature_type = op.get('feature_type') or op.get('operation_type', '')
    params = op.get('params', {})

    # Get category and color
    category = _get_category(feature_type)
    color = CATEGORY_COLORS.get(category, "#6b7280")

    # Get dimensions from params or top-level fields
    from_diameter = params.get('from_diameter') or op.get('from_diameter')
    to_diameter = params.get('to_diameter') or op.get('to_diameter')
    length = params.get('length') or op.get('length')
    depth = params.get('depth') or op.get('depth')
    diameter = params.get('diameter') or op.get('diameter')

    # Feature type specific matching
    if feature_type in ['od_rough', 'od_finish', 'od_profile']:
        # Match to outer contour
        if from_diameter and to_diameter:
            target_r = to_diameter / 2
            match = _find_diameter_match(outer_segments, target_r)
            if match:
                return FeatureZone(
                    feature_index=idx,
                    feature_type=feature_type,
                    category=category,
                    z_start=match['z_start'],
                    z_end=match['z_end'],
                    r_inner=to_diameter / 2,
                    r_outer=from_diameter / 2,
                    color=color,
                    label=f"{feature_type} Ø{to_diameter:.0f}"
                )

    elif feature_type in ['id_rough', 'id_finish', 'id_profile', 'bore']:
        # Match to inner contour
        if from_diameter and to_diameter:
            target_r = to_diameter / 2
            match = _find_diameter_match(inner_segments, target_r)
            if match:
                return FeatureZone(
                    feature_index=idx,
                    feature_type=feature_type,
                    category=category,
                    z_start=match['z_start'],
                    z_end=match['z_end'],
                    r_inner=from_diameter / 2,
                    r_outer=to_diameter / 2,
                    color=color,
                    label=f"{feature_type} Ø{to_diameter:.0f}"
                )

    elif feature_type in ['drill', 'ream', 'tap', 'center_drill', 'drill_deep']:
        # Drilling operations — from face (z=0)
        if to_diameter or diameter:
            d = to_diameter or diameter
            d_depth = float(depth) if depth and depth != 'through' else total_length
            return FeatureZone(
                feature_index=idx,
                feature_type=feature_type,
                category=category,
                z_start=0,
                z_end=min(d_depth, total_length),
                r_inner=0,
                r_outer=d / 2,
                color=color,
                label=f"{feature_type} Ø{d:.0f}"
            )

    elif feature_type == 'face':
        # Face operation — full diameter at z=0
        if from_diameter or max_diameter:
            d = from_diameter or max_diameter
            return FeatureZone(
                feature_index=idx,
                feature_type=feature_type,
                category=category,
                z_start=0,
                z_end=0,  # Face is thin
                r_inner=0,
                r_outer=d / 2,
                color=color,
                label="face"
            )

    elif feature_type in ['thread_od', 'thread_id']:
        # Threading
        if from_diameter or diameter:
            d = from_diameter or diameter
            thread_len = length or 10
            if 'od' in feature_type:
                # Match to outer contour
                target_r = d / 2
                match = _find_diameter_match(outer_segments, target_r)
                if match:
                    return FeatureZone(
                        feature_index=idx,
                        feature_type=feature_type,
                        category=category,
                        z_start=match['z_start'],
                        z_end=min(match['z_start'] + thread_len, match['z_end']),
                        r_inner=d / 2 - 2,
                        r_outer=d / 2,
                        color=color,
                        label=f"thread Ø{d:.0f}"
                    )

    elif feature_type in ['groove_od', 'groove_id', 'groove_face']:
        # Grooves
        if from_diameter:
            width = params.get('width', 3)
            target_r = from_diameter / 2
            segments = outer_segments if 'od' in feature_type else inner_segments
            match = _find_diameter_match(segments, target_r)
            if match:
                return FeatureZone(
                    feature_index=idx,
                    feature_type=feature_type,
                    category=category,
                    z_start=match['z_start'],
                    z_end=match['z_start'] + width,
                    r_inner=target_r - 3,
                    r_outer=target_r,
                    color=color,
                    label="groove"
                )

    elif feature_type in ['chamfer', 'radius']:
        # Edge features — find sharp transitions in contour
        if from_diameter:
            target_r = from_diameter / 2
            match = _find_diameter_match(outer_segments, target_r)
            if match:
                return FeatureZone(
                    feature_index=idx,
                    feature_type=feature_type,
                    category=category,
                    z_start=match['z_start'],
                    z_end=match['z_start'] + 2,  # Small zone
                    r_inner=target_r - 1,
                    r_outer=target_r,
                    color=color,
                    label=feature_type
                )

    # Fallback: create full-length zone if no match
    if from_diameter or diameter:
        d = from_diameter or diameter
        return FeatureZone(
            feature_index=idx,
            feature_type=feature_type,
            category=category,
            z_start=0,
            z_end=total_length,
            r_inner=0,
            r_outer=d / 2,
            color=color,
            label=f"{feature_type} (unmapped)"
        )

    return None


def _find_diameter_match(
    segments: List[Dict],
    target_r: float,
    tolerance: float = 0.5
) -> Optional[Dict]:
    """Find segment matching target radius (±tolerance)."""
    for seg in segments:
        if abs(seg['r'] - target_r) <= tolerance:
            return seg
    return None


def _map_prismatic_features(
    geo: Dict[str, Any],
    operations: List[Dict[str, Any]]
) -> List[FeatureZone]:
    """Map prismatic part features (milling)."""
    zones = []
    pockets = geo.get('pockets', [])
    holes = geo.get('holes', [])

    for idx, op in enumerate(operations):
        try:
            feature_type = op.get('feature_type') or op.get('operation_type', '')
            params = op.get('params', {})
            category = _get_category(feature_type)
            color = CATEGORY_COLORS.get(category, "#6b7280")

            # Match pockets
            if feature_type == 'mill_pocket':
                pocket_length = params.get('pocket_length') or op.get('pocket_length')
                pocket_width = params.get('pocket_width') or op.get('pocket_width')
                if pocket_length and pocket_width:
                    # Match to pockets in geometry
                    for pocket in pockets:
                        if (abs(pocket.get('length', 0) - pocket_length) < 2 and
                            abs(pocket.get('width', 0) - pocket_width) < 2):
                            zones.append(FeatureZone(
                                feature_index=idx,
                                feature_type=feature_type,
                                category=category,
                                x=pocket.get('x', 0),
                                y=pocket.get('y', 0),
                                width=pocket_length,
                                height=pocket_width,
                                color=color,
                                label=f"pocket {pocket_length}×{pocket_width}"
                            ))
                            break

            # Match holes (mill_drill, mill_tap)
            elif feature_type in ['mill_drill', 'mill_tap']:
                diameter = params.get('to_diameter') or op.get('to_diameter')
                if diameter:
                    for hole in holes:
                        if abs(hole.get('diameter', 0) - diameter) < 1:
                            zones.append(FeatureZone(
                                feature_index=idx,
                                feature_type=feature_type,
                                category=category,
                                x=hole.get('x', 0),
                                y=hole.get('y', 0),
                                radius=diameter / 2,
                                color=color,
                                label=f"hole Ø{diameter:.0f}"
                            ))
                            break

        except Exception as e:
            logger.warning(f"Failed to map prismatic operation {idx}: {e}")
            continue

    return zones


def _get_category(feature_type: str) -> str:
    """Get category for feature type from FEATURE_FIELDS or infer."""
    if feature_type in FEATURE_FIELDS:
        return FEATURE_FIELDS[feature_type].get('category', 'turning')

    # Infer category from feature_type prefix
    if feature_type.startswith('od_') or feature_type.startswith('id_'):
        return 'turning'
    elif feature_type.startswith('mill_'):
        return 'milling'
    elif feature_type.startswith('drill') or feature_type.startswith('tap'):
        return 'drilling'
    elif feature_type.startswith('thread'):
        return 'threading'
    elif feature_type.startswith('grind'):
        return 'grinding'
    elif feature_type.startswith('groove') or feature_type == 'parting':
        return 'grooving'
    else:
        return 'turning'  # default
