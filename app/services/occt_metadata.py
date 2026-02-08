"""
OCCT Metadata Extractors - Volume, bounding box, rotation axis

Extracts manufacturing metadata from OCCT shapes.
Split from step_parser_occt.py to maintain L-036 compliance.

ADR-039: OCCT Integration (Primary Parser)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# OCCT imports (conditional - matches parent module)
try:
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False


def extract_metadata(shape: Any) -> Dict:
    """
    Extract volume, bounding box, center of mass.

    This is OCCT's killer feature - accurate properties!

    Args:
        shape: OCCT TopoDS_Shape object (typed as Any for optional import)

    Returns:
        Dict with keys: volume_cm3, center_of_mass, bounding_box
        Empty dict on failure (with warning log)
    """
    metadata = {}

    try:
        # Volume and center of mass
        props = GProp_GProps()
        brepgprop.VolumeProperties(shape, props)

        volume_mm3 = props.Mass()
        volume_cm3 = volume_mm3 / 1000.0

        com = props.CentreOfMass()

        metadata['volume_cm3'] = round(volume_cm3, 2)
        metadata['center_of_mass'] = (
            round(com.X(), 2),
            round(com.Y(), 2),
            round(com.Z(), 2)
        )

        # Bounding box
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)

        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

        metadata['bounding_box'] = {
            'x_min': round(xmin, 2),
            'x_max': round(xmax, 2),
            'y_min': round(ymin, 2),
            'y_max': round(ymax, 2),
            'z_min': round(zmin, 2),
            'z_max': round(zmax, 2),
            'height': round(zmax - zmin, 2),
            'width': round(xmax - xmin, 2),
            'depth': round(ymax - ymin, 2)
        }

    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")

    return metadata


def detect_rotation_axis(features: List[Dict]) -> Optional[str]:
    """
    Detect rotation axis from feature orientations.

    Same logic as regex parser: majority vote + largest diameter fallback.

    Args:
        features: List of feature dicts with 'axis_direction' and 'radius'

    Returns:
        'x', 'y', 'z', or None if no axis detected
    """
    if not features:
        return None

    axis_entries = []  # (axis_direction, radius)

    for f in features:
        axis_dir = f.get('axis_direction')
        radius = f.get('radius', 0)

        if not axis_dir or radius == 0:
            continue

        axis_entries.append((axis_dir, radius))

    if not axis_entries:
        return None

    # Classify axes
    def classify(ax):
        """Classify axis direction vector to x/y/z."""
        if abs(ax[2]) > 0.9:
            return 'z'
        if abs(ax[0]) > 0.9:
            return 'x'
        if abs(ax[1]) > 0.9:
            return 'y'
        return None

    # Majority vote (60% threshold)
    counts = {'x': 0, 'y': 0, 'z': 0}
    for ax_dir, _r in axis_entries:
        label = classify(ax_dir)
        if label:
            counts[label] += 1

    total = len(axis_entries)
    best = max(counts.items(), key=lambda x: x[1])

    if best[1] / total >= 0.60:
        return best[0]

    # Fallback: largest diameter
    max_r_per_axis = {'x': 0.0, 'y': 0.0, 'z': 0.0}
    for ax_dir, radius in axis_entries:
        label = classify(ax_dir)
        if label:
            max_r_per_axis[label] = max(max_r_per_axis[label], radius)

    best_by_size = max(max_r_per_axis.items(), key=lambda x: x[1])
    if best_by_size[1] > 0:
        return best_by_size[0]

    return None
