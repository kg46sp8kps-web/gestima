"""
STEP Analysis Helper - Volume-based time calculation from batch results.

Uses cached batch_combined_results.json for fast analysis without OCCT parsing.
Falls back to OCCT if batch results not available.

ADR-041: Time Calculation Calibration System
"""

import logging
import math
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_batch_results() -> Optional[Dict]:
    """Load cached batch_combined_results.json if exists."""
    import json

    batch_path = Path("uploads/drawings/contour_SVG/batch_combined_results.json")
    if not batch_path.exists():
        return None

    try:
        with open(batch_path, 'r', encoding='utf-8') as f:
            return {item['filename']: item for item in json.load(f)}
    except Exception as e:
        logger.warning(f"Failed to load batch results: {e}")
        return None


def detect_part_type_from_features(mfg_features: dict, rotation_axis: str = None, filename: str = None) -> str:
    """
    Detect part type (ROT/PRI) from mfg_feature distribution.

    ROT indicators: shaft_segment, bore, groove_wall, fillet_outer
    PRI indicators: pocket_*, step_face, end_face (many planar faces)

    Threshold: >40% ROT features = ROT part (lower threshold = more sensitive to rotation features)
    """
    rot_features = ['shaft_segment', 'bore', 'groove_wall', 'groove_bottom', 'fillet_outer', 'fillet_inner']
    pri_features = ['pocket_wall', 'pocket_bottom', 'step_face', 'end_face', 'taper']

    rot_count = sum(mfg_features.get(f, 0) for f in rot_features)
    pri_count = sum(mfg_features.get(f, 0) for f in pri_features)
    total = rot_count + pri_count

    if total == 0:
        # Fallback to rotation_axis
        return 'ROT' if rotation_axis else 'PRI'

    rot_ratio = rot_count / total

    # Threshold: >40% ROT features = ROT part
    # Lower threshold makes it more sensitive - even if there are some pockets/steps,
    # if there are shaft_segments or bores, it's likely a turned part
    return 'ROT' if rot_ratio > 0.40 else 'PRI'


def calculate_machining_time(
    part_type: str,
    volume_mm3: float,
    bbox_dims: dict,
    max_diameter: float = 0,
    total_length: float = 0
) -> dict:
    """
    Calculate stock volume, material removal, and PURE machining time.

    CRITICAL: Returns ONLY cutting time (material removal).
    NO setup, NO tool changes, NO inspection → those are added separately!

    Time breakdown:
    - cutting_time: Pure material removal (rough + semi + finish)
    - rapid_time: Tool positioning, retract, approach moves
    - auxiliary_time: Spindle start/stop, coolant on/off per operation

    Returns dict with:
    - stock_volume_mm3
    - material_removal_volume_mm3
    - material_removal_percent
    - machining_strategy (rough, semi_finish, finish with MRR & PURE cutting times)
    - pure_machining_time_min (NO overheads)
    """
    # Stock volume calculation
    if part_type == 'ROT' and max_diameter > 0 and total_length > 0:
        # Cylindrical stock
        stock_diameter = max_diameter + 2.0  # +1mm per side allowance
        stock_length = total_length + 5.0
        stock_volume_mm3 = math.pi * (stock_diameter / 2) ** 2 * stock_length
    else:
        # Rectangular stock (PRI or fallback)
        stock_x = bbox_dims.get('x', 0) + 10.0
        stock_y = bbox_dims.get('y', 0) + 10.0
        stock_z = bbox_dims.get('z', 0) + 10.0
        stock_volume_mm3 = stock_x * stock_y * stock_z

    # Material removal
    material_removal_volume = max(stock_volume_mm3 - volume_mm3, 0)
    material_removal_percent = (material_removal_volume / stock_volume_mm3 * 100) if stock_volume_mm3 > 0 else 0

    # Multi-level machining strategy
    # Rough: 80% of material with aggressive MRR
    # Semi-finish: 15% with moderate MRR
    # Finish: 5% with fine MRR
    rough_volume = material_removal_volume * 0.80
    semi_volume = material_removal_volume * 0.15
    finish_volume = material_removal_volume * 0.05

    # MRR values (Material Removal Rate) in mm³/min
    # These are calibration targets - adjust based on real machine data
    rough_mrr = 3000.0
    semi_mrr = 1000.0
    finish_mrr = 200.0

    # PURE CUTTING TIME (no rapids, no auxiliary)
    rough_cutting_time_min = rough_volume / rough_mrr if rough_volume > 0 else 0
    semi_cutting_time_min = semi_volume / semi_mrr if semi_volume > 0 else 0
    finish_cutting_time_min = finish_volume / finish_mrr if finish_volume > 0 else 0

    # Rapid moves time (approach, retract, tool positioning)
    # Estimate: 10% of cutting time for rough, 15% for semi/finish (more precise = more positioning)
    rough_rapid_time_min = rough_cutting_time_min * 0.10
    semi_rapid_time_min = semi_cutting_time_min * 0.15
    finish_rapid_time_min = finish_cutting_time_min * 0.15

    # Auxiliary time per operation (spindle start/stop, coolant)
    # Estimate: 0.1 min (6 sec) per operation
    auxiliary_time_per_op = 0.1
    num_operations = 3  # rough, semi, finish
    total_auxiliary_time = auxiliary_time_per_op * num_operations

    # Total per level (cutting + rapids)
    rough_total_time = rough_cutting_time_min + rough_rapid_time_min
    semi_total_time = semi_cutting_time_min + semi_rapid_time_min
    finish_total_time = finish_cutting_time_min + finish_rapid_time_min

    # PURE machining time (NO setup, NO tool changes, NO inspection)
    pure_machining_time = rough_total_time + semi_total_time + finish_total_time + total_auxiliary_time

    return {
        'stock_volume_mm3': round(stock_volume_mm3, 1),
        'material_removal_volume_mm3': round(material_removal_volume, 1),
        'material_removal_percent': round(material_removal_percent, 1),
        'machining_strategy': {
            'rough': {
                'tool': 'Ø40 hrubovací fréza',
                'volume_mm3': round(rough_volume, 1),
                'mrr_mm3_per_min': round(rough_mrr, 0),
                'cutting_time_min': round(rough_cutting_time_min, 2),
                'rapid_time_min': round(rough_rapid_time_min, 2),
                'total_time_min': round(rough_total_time, 2),
            },
            'semi_finish': {
                'tool': 'Ø12 polodokončovací fréza',
                'volume_mm3': round(semi_volume, 1),
                'mrr_mm3_per_min': round(semi_mrr, 0),
                'cutting_time_min': round(semi_cutting_time_min, 2),
                'rapid_time_min': round(semi_rapid_time_min, 2),
                'total_time_min': round(semi_total_time, 2),
            },
            'finish': {
                'tool': 'Ø4 dokončovací fréza',
                'volume_mm3': round(finish_volume, 1),
                'mrr_mm3_per_min': round(finish_mrr, 0),
                'cutting_time_min': round(finish_cutting_time_min, 2),
                'rapid_time_min': round(finish_rapid_time_min, 2),
                'total_time_min': round(finish_total_time, 2),
            },
        },
        'time_breakdown': {
            'pure_cutting_time_min': round(rough_cutting_time_min + semi_cutting_time_min + finish_cutting_time_min, 2),
            'rapid_moves_time_min': round(rough_rapid_time_min + semi_rapid_time_min + finish_rapid_time_min, 2),
            'auxiliary_time_min': round(total_auxiliary_time, 2),
            'pure_machining_time_min': round(pure_machining_time, 2),
        },
        'pure_machining_time_min': round(pure_machining_time, 2),
    }


def build_analysis_from_batch(batch_item: dict, filename: str) -> dict:
    """
    Build complete analysis response from batch_combined_results.json item.

    Extracts geometry, computes time, returns frontend-ready dict.
    """
    # Extract geometry
    bbox = batch_item.get('bbox', {})
    bbox_dims = {
        'x': bbox.get('dx', 0),
        'y': bbox.get('dy', 0),
        'z': bbox.get('dz', 0),
    }

    volume_cm3 = batch_item.get('volume_cm3', 0)
    volume_mm3 = volume_cm3 * 1000.0  # cm³ → mm³

    mfg_features = batch_item.get('mfg_features', {})
    n_faces = batch_item.get('n_faces', 0)
    n_edges = batch_item.get('n_manifold_edges', 0)

    # Waterline data (if ROT part)
    waterline = batch_item.get('waterline_polar', {})
    max_diameter = waterline.get('max_diameter_mm', 0)
    total_length = waterline.get('total_length_mm', 0)
    rotation_axis = waterline.get('rotation_axis')

    # Detect part type from mfg_features
    part_type = batch_item.get('part_type', 'PRI')
    if not part_type or part_type == 'UNKNOWN':
        part_type = detect_part_type_from_features(mfg_features, rotation_axis)

    # Calculate machining time
    time_data = calculate_machining_time(
        part_type, volume_mm3, bbox_dims, max_diameter, total_length
    )

    # Build feature list (first 20 for display)
    face_list = []
    for face_data in batch_item.get('face_classifications', [])[:20]:
        face_list.append({
            'type': face_data.get('type', 'unknown'),
            'mfg_feature': face_data.get('mfg_feature', 'unknown'),
            'radius': face_data.get('radius'),
            'diameter': face_data.get('diameter'),
        })

    return {
        'filename': filename,
        'success': True,
        'part_type': part_type,
        'rotation_axis': rotation_axis,
        'n_faces': n_faces,
        'n_manifold_edges': n_edges,
        'volume_mm3': round(volume_mm3, 1),
        'bbox': {
            'x': round(bbox_dims['x'], 1),
            'y': round(bbox_dims['y'], 1),
            'z': round(bbox_dims['z'], 1),
        },
        **time_data,
        'contour_points': len(waterline.get('r_values', [])),
        'features': face_list,
        'mfg_feature_summary': mfg_features,
    }
