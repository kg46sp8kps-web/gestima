"""GESTIMA - Feature-based machining time calculation

Converts AI-extracted features (JSON) into deterministic machining time
using cutting conditions from database.

ADR: To be created for feature-based estimation architecture
Version: 1.0.0 (2026-02-15)
"""

import logging
import math
import re
from typing import Dict, Any, List, Optional, Tuple

from app.services.cutting_conditions_catalog import (
    get_catalog_conditions,
    resolve_material_group,
    MATERIAL_GROUP_MAP,
)
from app.services.feature_types import (
    get_operation_for_feature,
    CONSTANT_TIMES,
    FEATURE_TYPES,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DETAIL STRING PARSING
# ============================================================================

def parse_diameter(detail: str) -> Optional[float]:
    """Extract diameter from detail string.

    Examples:
        "ø60 h9" → 60.0
        "2× ø5.3 mm" → 5.3
        "M5" → 5.0
        "ø12.5" → 12.5
    """
    if not detail:
        return None

    # Try ø pattern first
    match = re.search(r'ø\s*(\d+\.?\d*)', detail, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Try M thread pattern (M5 → diameter 5)
    match = re.search(r'\bM\s*(\d+\.?\d*)', detail, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Try standalone number if nothing else
    match = re.search(r'(\d+\.?\d*)\s*(?:mm)?', detail)
    if match:
        return float(match.group(1))

    return None


def parse_length(detail: str) -> Optional[float]:
    """Extract length from detail string.

    Examples:
        "80×22×3.4mm" → 80.0 (first dimension)
        "L=50" → 50.0
    """
    if not detail:
        return None

    # Try L= pattern
    match = re.search(r'L\s*=?\s*(\d+\.?\d*)', detail, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Try dimension pattern (first number in ×× format)
    match = re.search(r'(\d+\.?\d*)\s*×', detail)
    if match:
        return float(match.group(1))

    return None


def parse_width(detail: str) -> Optional[float]:
    """Extract width from detail string.

    Examples:
        "80×22×3.4mm" → 22.0 (second dimension)
    """
    if not detail:
        return None

    # Try dimension pattern (second number in ×× format)
    match = re.search(r'×\s*(\d+\.?\d*)\s*×', detail)
    if match:
        return float(match.group(1))

    return None


def parse_depth(detail: str) -> Optional[float]:
    """Extract depth from detail string.

    Examples:
        "80×22×3.4mm" → 3.4 (third dimension)
        "H=5" → 5.0
    """
    if not detail:
        return None

    # Try H= pattern
    match = re.search(r'H\s*=?\s*(\d+\.?\d*)', detail, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Try dimension pattern (third number after ××)
    parts = re.findall(r'(\d+\.?\d*)', detail.replace('×', ' '))
    if len(parts) >= 3:
        return float(parts[2])

    return None


def parse_thread_pitch(detail: str) -> Optional[float]:
    """Extract thread pitch from detail string.

    Examples:
        "M5" → 0.8 (standard pitch for M5)
        "M10×1.5" → 1.5
    """
    if not detail:
        return None

    # Try explicit pitch pattern
    match = re.search(r'×\s*(\d+\.?\d*)', detail)
    if match:
        return float(match.group(1))

    # Standard ISO metric thread pitches
    match = re.search(r'\bM\s*(\d+)', detail, re.IGNORECASE)
    if match:
        diameter = int(match.group(1))
        standard_pitches = {
            3: 0.5, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25,
            10: 1.5, 12: 1.75, 14: 2.0, 16: 2.0, 20: 2.5,
        }
        return standard_pitches.get(diameter, 1.5)  # Default 1.5mm

    return None


# ============================================================================
# MACHINING TIME FORMULAS
# ============================================================================

def calc_turning_time(
    diameter_mm: float,
    length_mm: float,
    Vc: float,
    f: float,
    Ap: float,
    material_removal_mm: Optional[float] = None
) -> float:
    """Calculate turning time (OD roughing/finishing).

    Args:
        diameter_mm: Workpiece diameter
        length_mm: Length to turn
        Vc: Cutting speed (m/min)
        f: Feed rate (mm/rev)
        Ap: Depth of cut (mm)
        material_removal_mm: Total material to remove (for calculating passes)

    Returns:
        Time in minutes
    """
    if diameter_mm <= 0 or length_mm <= 0 or Vc <= 0 or f <= 0:
        return 0.01

    rpm = (Vc * 1000) / (math.pi * diameter_mm)
    feed_rate = rpm * f  # mm/min

    if material_removal_mm and Ap > 0:
        passes = math.ceil(material_removal_mm / Ap)
    else:
        passes = 1

    time_min = passes * (length_mm / feed_rate)
    return max(time_min, 0.01)


def calc_drilling_time(
    diameter_mm: float,
    depth_mm: float,
    Vc: float,
    f: float
) -> float:
    """Calculate drilling time.

    Args:
        diameter_mm: Drill diameter
        depth_mm: Hole depth
        Vc: Cutting speed (m/min)
        f: Feed rate (mm/rev)

    Returns:
        Time in minutes
    """
    if diameter_mm <= 0 or depth_mm <= 0 or Vc <= 0 or f <= 0:
        return 0.01

    rpm = (Vc * 1000) / (math.pi * diameter_mm)
    feed_rate = rpm * f  # mm/min
    time_min = depth_mm / feed_rate
    return max(time_min, 0.01)


def calc_milling_time(
    length_mm: float,
    width_mm: float,
    depth_mm: float,
    Vc: float,
    fz: float,
    Ap: float,
    tool_diameter: float = 10.0,
    num_teeth: int = 3
) -> float:
    """Calculate milling time for pockets/slots.

    Args:
        length_mm: Pocket/slot length
        width_mm: Pocket/slot width
        depth_mm: Pocket/slot depth
        Vc: Cutting speed (m/min)
        fz: Feed per tooth (mm/tooth)
        Ap: Axial depth of cut (mm)
        tool_diameter: Tool diameter (mm)
        num_teeth: Number of flutes

    Returns:
        Time in minutes
    """
    if length_mm <= 0 or depth_mm <= 0 or Vc <= 0 or fz <= 0 or Ap <= 0:
        return 0.01

    rpm = (Vc * 1000) / (math.pi * tool_diameter)
    feed_rate = rpm * fz * num_teeth  # mm/min

    # Number of depth passes
    depth_passes = math.ceil(depth_mm / Ap) if Ap > 0 else 1

    # Simplified path: length of pocket (actual path would be more complex)
    path_length = length_mm

    time_min = depth_passes * (path_length / feed_rate)
    return max(time_min, 0.01)


def calc_threading_time(
    diameter_mm: float,
    length_mm: float,
    pitch_mm: float,
    Vc: float
) -> float:
    """Calculate threading time.

    Args:
        diameter_mm: Thread diameter
        length_mm: Thread length
        pitch_mm: Thread pitch
        Vc: Cutting speed (m/min)

    Returns:
        Time in minutes
    """
    if diameter_mm <= 0 or length_mm <= 0 or pitch_mm <= 0 or Vc <= 0:
        return 0.01

    rpm = (Vc * 1000) / (math.pi * diameter_mm)
    # Threading typically 4-6 passes
    passes = 5
    feed_rate = rpm * pitch_mm  # mm/min (feed = pitch for threading)
    time_min = passes * (length_mm / feed_rate)
    return max(time_min, 0.01)


# ============================================================================
# MAIN CALCULATION FUNCTION
# ============================================================================

def calculate_features_time(
    features_json: List[Dict[str, Any]],
    material_group: str,
    cutting_mode: str = "mid",
    part_type: str = "PRI",
) -> Dict[str, Any]:
    """Calculate machining time from AI-extracted features.

    Args:
        features_json: List of feature dicts from AI extraction
            Each feature: {"type": str, "count": int, "detail": str, "location": str}
        material_group: 8-digit material group code (e.g. "20910004")
        cutting_mode: Cutting speed mode ("low", "mid", "high")
        part_type: Part type ("ROT", "PRI", "COMBINED")

    Returns:
        {
            "calculated_time_min": float,
            "feature_times": List[dict],
            "warnings": List[str],
            "cutting_mode": str,
            "material_group": str
        }
    """
    warnings = []
    feature_times = []
    total_time_sec = 0.0

    # Validate material group
    if material_group not in MATERIAL_GROUP_MAP:
        material_group = "20910004"  # Default to konstrukční ocel
        warnings.append(
            f"Unknown material group, defaulting to {material_group} "
            f"({MATERIAL_GROUP_MAP[material_group]['name']})"
        )

    for feature in features_json:
        try:
            feature_type = feature.get("type", "unknown")
            detail = feature.get("detail", "")
            count = feature.get("count", 1)
            location = feature.get("location", "")

            # Get DB operation mapping from feature_types catalog
            db_operation = get_operation_for_feature(feature_type)

            # Skip informational features
            if db_operation is None and feature_type not in CONSTANT_TIMES:
                # Check if it's a known info-only feature
                if feature_type in FEATURE_TYPES:
                    feature_times.append({
                        "type": feature_type,
                        "detail": detail,
                        "count": count,
                        "time_sec": 0.0,
                        "method": "informational (no machining time)"
                    })
                else:
                    warnings.append(f"Unknown feature type: {feature_type}")
                continue

            # Calculate time for this feature
            time_sec = 0.0
            method = ""

            # Constant time features
            if feature_type in CONSTANT_TIMES:
                time_sec = CONSTANT_TIMES[feature_type] * 60 * count  # Convert min to sec
                method = f"constant {CONSTANT_TIMES[feature_type]} min"

            # Features requiring cutting conditions lookup
            elif db_operation:
                operation_type, operation = db_operation

                # Get cutting conditions
                conditions = get_catalog_conditions(
                    material_group,
                    operation_type,
                    operation,
                    cutting_mode
                )

                if not conditions:
                    # Try fallback
                    if operation == "hrubovani":
                        conditions = get_catalog_conditions(
                            material_group, operation_type, "dokoncovani", cutting_mode
                        )
                        if conditions:
                            warnings.append(
                                f"Using 'dokoncovani' as fallback for {feature_type}"
                            )

                    if not conditions:
                        warnings.append(
                            f"No cutting conditions for {feature_type} "
                            f"(material={material_group}, op={operation_type}/{operation})"
                        )
                        continue

                # Extract dimensions from detail
                diameter = parse_diameter(detail)
                length = parse_length(detail)
                width = parse_width(detail)
                depth = parse_depth(detail)
                pitch = parse_thread_pitch(detail)

                # Calculate based on feature type
                if operation_type == "turning":
                    # For turning, if no length specified, assume default based on diameter
                    if diameter:
                        turn_length = length if length else diameter  # Default to diameter if no length
                        time_min = calc_turning_time(
                            diameter, turn_length,
                            conditions.get("Vc", 220),
                            conditions.get("f", 0.25),
                            conditions.get("Ap", 2.5)
                        )
                        time_sec = time_min * 60 * count
                        method = f"turning Vc={conditions.get('Vc')} f={conditions.get('f')}"
                    else:
                        warnings.append(f"Missing diameter for turning: {detail}")

                elif operation_type == "drilling":
                    # For drilling, if no depth specified, assume 2× diameter
                    if diameter:
                        drill_depth = depth if depth else (diameter * 2)
                        time_min = calc_drilling_time(
                            diameter, drill_depth,
                            conditions.get("Vc", 90),
                            conditions.get("f", 0.2)
                        )
                        time_sec = time_min * 60 * count
                        method = f"drilling Vc={conditions.get('Vc')} f={conditions.get('f')}"
                    else:
                        warnings.append(f"Missing diameter for drilling: {detail}")

                elif operation_type == "threading":
                    if diameter:
                        thread_length = length if length else (diameter * 1.5)  # Default to 1.5× diameter
                        thread_pitch = pitch if pitch else 1.5  # Default pitch
                        time_min = calc_threading_time(
                            diameter, thread_length, thread_pitch,
                            conditions.get("Vc", 80)
                        )
                        time_sec = time_min * 60 * count
                        method = f"threading Vc={conditions.get('Vc')} pitch={thread_pitch}"
                    else:
                        warnings.append(f"Missing diameter for threading: {detail}")

                elif operation_type == "milling":
                    if length and depth:
                        # Use width if available, else assume tool width
                        w = width or 10.0
                        time_min = calc_milling_time(
                            length, w, depth,
                            conditions.get("Vc", 160),
                            conditions.get("fz", 0.1),
                            conditions.get("Ap", 2.0)
                        )
                        time_sec = time_min * 60 * count
                        method = f"milling Vc={conditions.get('Vc')} fz={conditions.get('fz')}"
                    else:
                        warnings.append(f"Missing dimensions for milling: {detail}")

                elif operation_type == "grooving":
                    if diameter and width:
                        # Simplified: groove width as "length"
                        time_min = calc_turning_time(
                            diameter, width,
                            conditions.get("Vc", 130),
                            conditions.get("f", 0.08),
                            1.0  # Single pass for grooving
                        )
                        time_sec = time_min * 60 * count
                        method = f"grooving Vc={conditions.get('Vc')} f={conditions.get('f')}"
                    else:
                        warnings.append(f"Missing dimensions for grooving: {detail}")

            # Add to results
            if time_sec > 0:
                total_time_sec += time_sec
                feature_times.append({
                    "type": feature_type,
                    "detail": detail,
                    "count": count,
                    "location": location,
                    "time_sec": round(time_sec, 2),
                    "method": method
                })

        except Exception as e:
            warnings.append(f"Error calculating {feature.get('type', 'unknown')}: {str(e)}")
            logger.exception(f"Feature calculation error for {feature}")

    return {
        "calculated_time_min": round(total_time_sec / 60, 2),
        "feature_times": feature_times,
        "warnings": warnings,
        "cutting_mode": cutting_mode,
        "material_group": material_group,
    }
