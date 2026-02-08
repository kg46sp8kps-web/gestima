"""
OCCT Raw Geometry Extractor

Extracts BASIC measurements from STEP files for future Vision API integration.
NO feature classification, NO interpretation, NO mfg_feature labels.
Just FACTS: cylindrical faces, bbox, volume.

ADR-042: OCCT Simplification - Raw Extraction Only
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# OCCT imports (optional - graceful degradation)
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
    from OCC.Core.TopoDS import topods
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False
    logger.warning("OCCT not available - install pythonocc-core for raw extraction")


def extract_raw_geometry(step_file: Path) -> Dict:
    """
    Extract raw measurements from STEP file.

    NO classification! Just facts for future Vision API:
    - Bounding box (L x W x H)
    - Volume
    - Cylindrical faces: diameter, z-range, orientation

    Args:
        step_file: Path to STEP file

    Returns:
        {
            "filename": str,
            "bbox_mm": {"length": float, "width": float, "height": float},
            "volume_mm3": float,
            "cylindrical_faces": [
                {
                    "face_id": int,
                    "diameter_mm": float,
                    "z_min_mm": float,
                    "z_max_mm": float,
                    "orientation": "FORWARD" | "REVERSED"
                }
            ],
            "planar_faces": [
                {
                    "face_id": int,
                    "z_position_mm": float,
                    "area_mm2": float
                }
            ],
            "source": "occt"
        }

    Raises:
        ImportError: If OCCT not available
        ValueError: If STEP file cannot be read
    """
    if not OCCT_AVAILABLE:
        raise ImportError("OCCT not available - install pythonocc-core")

    if not step_file.exists():
        raise ValueError(f"File not found: {step_file}")

    # 1. Load STEP file
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_file))

    if status != IFSelect_RetDone:
        raise ValueError(f"Failed to read STEP file: {step_file}")

    reader.TransferRoots()
    shape = reader.OneShape()

    if shape.IsNull():
        raise ValueError(f"Null shape in STEP file: {step_file}")

    # 2. Bounding box
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    length = round(xmax - xmin, 3)
    width = round(ymax - ymin, 3)
    height = round(zmax - zmin, 3)

    # 3. Volume
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    volume = round(props.Mass(), 3)

    # 4. Extract cylindrical faces (NO classification!)
    cylindrical_faces = []
    planar_faces = []

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    face_idx = 0

    while exp.More():
        face = topods.Face(exp.Current())
        surf = BRepAdaptor_Surface(face)

        # Cylindrical faces
        if surf.GetType() == GeomAbs_Cylinder:
            cyl = surf.Cylinder()
            radius = cyl.Radius()

            # Face bbox for z-range
            face_bbox = Bnd_Box()
            brepbndlib.Add(face, face_bbox)
            _, _, z_min, _, _, z_max = face_bbox.Get()

            cylindrical_faces.append({
                "face_id": face_idx,
                "diameter_mm": round(radius * 2, 3),
                "z_min_mm": round(z_min, 3),
                "z_max_mm": round(z_max, 3),
                "orientation": face.Orientation().name  # FORWARD/REVERSED
            })

        # Planar faces
        elif surf.GetType() == GeomAbs_Plane:
            plane = surf.Plane()
            origin = plane.Location()
            z_pos = origin.Z()

            # Face area
            face_props = GProp_GProps()
            brepgprop.SurfaceProperties(face, face_props)
            area = face_props.Mass()

            planar_faces.append({
                "face_id": face_idx,
                "z_position_mm": round(z_pos, 3),
                "area_mm2": round(area, 3)
            })

        face_idx += 1
        exp.Next()

    return {
        "filename": step_file.name,
        "bbox_mm": {
            "length": length,
            "width": width,
            "height": height
        },
        "volume_mm3": volume,
        "cylindrical_faces": cylindrical_faces,
        "planar_faces": planar_faces,
        "source": "occt"
    }
