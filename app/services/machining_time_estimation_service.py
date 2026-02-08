"""GESTIMA - Physics-Based Machining Time Estimation Service

100% deterministic time estimation based on:
- Material removal rate (MRR) from physics
- Geometry from OCCT (volume, surface area, bounding box)
- Manufacturing constraints (deep pockets, thin walls)

NO AI, NO ML, NO FEATURE CLASSIFICATION - pure physics + geometry.

ADR-040: Machining Time Estimation System
Reference: ISO 3685, DIN 6580, Sandvik Coromant Handbook
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.material import MaterialGroup

logger = logging.getLogger(__name__)

# Create synchronous engine for this service (OCCT is synchronous)
# Convert async URL (sqlite+aiosqlite:///...) to sync URL (sqlite:///...)
_sync_db_url = settings.DATABASE_URL.replace('+aiosqlite', '')
_sync_engine = create_engine(_sync_db_url, echo=False)
_SessionLocal = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)

# OCCT imports (conditional)
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False


# === CONSTANTS ===
SETUP_TIME_BASE_MIN = 15.00  # Base setup time (chuck, tools, program)
SETUP_TIME_PER_100MM_MIN = 2.00  # Additional time for larger parts
FINISHING_RATE_CM2_MIN = 50.00  # Surface finishing rate (cm²/min)


class MachiningTimeEstimationService:
    """
    Physics-based machining time estimation.

    No AI, no feature classification, just geometry + material physics.
    Deterministic: same input → identical output.
    """

    @staticmethod
    def estimate_time(
        step_path: Path,
        material: str,
        stock_type: str = "bbox"
    ) -> Dict[str, Any]:
        """
        Estimate machining time from STEP file.

        Args:
            step_path: Path to STEP file
            material: Material group code (e.g., "OCEL-AUTO", "HLINIK")
            stock_type: Stock type ("bbox" or "cylinder")

        Returns:
            Dict with time estimates and breakdown:
            {
                "total_time_min": float,
                "roughing_time_min": float,
                "finishing_time_min": float,
                "setup_time_min": float,
                "breakdown": {...},
                "deterministic": true
            }

        Raises:
            ValueError: Invalid material code or STEP file
            RuntimeError: OCCT not available or STEP parsing failed
        """
        if not OCCT_AVAILABLE:
            raise RuntimeError(
                "OCCT not available. Install pythonocc-core: "
                "mamba install -c conda-forge pythonocc-core"
            )

        if not step_path.exists():
            raise ValueError(f"STEP file not found: {step_path}")

        # Fetch material from database
        db = _SessionLocal()
        try:
            material_group = db.query(MaterialGroup).filter(
                MaterialGroup.code == material
            ).first()

            if not material_group:
                raise ValueError(f"Material code '{material}' not found in database")

            if not material_group.mrr_milling_roughing:
                raise ValueError(
                    f"Material '{material}' has no cutting parameters defined. "
                    f"Run seed_material_group_cutting_params.py to populate data."
                )

            # Convert DB model to dict for compatibility with existing code
            material_data = {
                "iso_group": material_group.iso_group,
                "hardness_hb": material_group.hardness_hb,
                "density": material_group.density,
                "mrr_aggressive_cm3_min": material_group.mrr_milling_roughing,
                "deep_pocket_penalty": material_group.deep_pocket_penalty or 1.8,
                "thin_wall_penalty": material_group.thin_wall_penalty or 2.5,
            }
        finally:
            db.close()

        # Load STEP file
        shape = MachiningTimeEstimationService._load_step(step_path)

        # Extract geometry
        geometry = MachiningTimeEstimationService._extract_geometry(shape)

        # Calculate stock volume
        stock_volume_mm3 = MachiningTimeEstimationService._calculate_stock_volume(
            geometry, stock_type
        )

        # Calculate material to remove
        part_volume_mm3 = geometry["volume_mm3"]
        material_to_remove_mm3 = stock_volume_mm3 - part_volume_mm3
        material_to_remove_cm3 = material_to_remove_mm3 / 1000.0

        # Calculate surface area (for finishing time)
        surface_area_mm2 = geometry["surface_area_mm2"]
        surface_area_cm2 = surface_area_mm2 / 100.0

        # Detect constraints
        constraints = MachiningTimeEstimationService._detect_constraints(geometry)
        constraint_multiplier = MachiningTimeEstimationService._calculate_penalty(
            constraints, material_data
        )

        # === TIME CALCULATIONS ===
        # Roughing: volume / MRR
        mrr_roughing = material_data["mrr_aggressive_cm3_min"]
        roughing_time_base = material_to_remove_cm3 / mrr_roughing
        roughing_time_main = roughing_time_base * constraint_multiplier

        # Roughing auxiliary (přejezdy - 20% hlavního času)
        roughing_time_aux = roughing_time_main * 0.20
        roughing_time_min = roughing_time_main + roughing_time_aux

        # Finishing: surface area / rate
        finishing_time_main = surface_area_cm2 / FINISHING_RATE_CM2_MIN

        # Finishing auxiliary (přejezdy - 15% hlavního času)
        finishing_time_aux = finishing_time_main * 0.15
        finishing_time_min = finishing_time_main + finishing_time_aux

        # Total time (NO SETUP - není potřeba)
        total_time_min = roughing_time_min + finishing_time_min

        # Round all values to 2 decimals for consistency
        return {
            "total_time_min": round(total_time_min, 2),
            "roughing_time_min": round(roughing_time_min, 2),
            "roughing_time_main": round(roughing_time_main, 2),
            "roughing_time_aux": round(roughing_time_aux, 2),
            "finishing_time_min": round(finishing_time_min, 2),
            "finishing_time_main": round(finishing_time_main, 2),
            "finishing_time_aux": round(finishing_time_aux, 2),
            "setup_time_min": 0.0,  # No longer used, kept for compatibility
            "breakdown": {
                "material": material,
                "iso_group": material_data.get("iso_group"),
                "stock_volume_mm3": round(stock_volume_mm3, 2),
                "part_volume_mm3": round(part_volume_mm3, 2),
                "material_to_remove_mm3": round(material_to_remove_mm3, 2),
                "surface_area_mm2": round(surface_area_mm2, 2),
                "mrr_roughing_cm3_min": round(mrr_roughing, 2),
                "finishing_rate_cm2_min": round(FINISHING_RATE_CM2_MIN, 2),
                "constraint_multiplier": round(constraint_multiplier, 2),
                "critical_constraints": constraints,
                "stock_type": stock_type,
            },
            "deterministic": True
        }

    @staticmethod
    def _load_step(step_path: Path) -> Any:
        """
        Load STEP file and return OCCT shape.

        Args:
            step_path: Path to STEP file

        Returns:
            OCCT TopoDS_Shape object

        Raises:
            RuntimeError: STEP parsing failed
        """
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(step_path))

        if status != IFSelect_RetDone:
            raise RuntimeError(f"STEP file read failed: {step_path}")

        reader.TransferRoots()
        shape = reader.OneShape()

        if shape.IsNull():
            raise RuntimeError(f"Empty STEP shape: {step_path}")

        return shape

    @staticmethod
    def _extract_geometry(shape: Any) -> Dict[str, Any]:
        """
        Extract geometry from OCCT shape.

        Args:
            shape: OCCT TopoDS_Shape

        Returns:
            Dict with keys: volume_mm3, surface_area_mm2, bbox, face_count
        """
        # Volume
        props = GProp_GProps()
        brepgprop.VolumeProperties(shape, props)
        volume_mm3 = props.Mass()

        # Surface area
        surface_props = GProp_GProps()
        brepgprop.SurfaceProperties(shape, surface_props)
        surface_area_mm2 = surface_props.Mass()

        # Bounding box
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

        # Face count (for complexity estimation)
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        face_count = 0
        while explorer.More():
            face_count += 1
            explorer.Next()

        return {
            "volume_mm3": volume_mm3,
            "surface_area_mm2": surface_area_mm2,
            "bbox": {
                "x_min": xmin,
                "x_max": xmax,
                "y_min": ymin,
                "y_max": ymax,
                "z_min": zmin,
                "z_max": zmax,
                "width": xmax - xmin,
                "depth": ymax - ymin,
                "height": zmax - zmin,
            },
            "face_count": face_count,
        }

    @staticmethod
    def _calculate_stock_volume(geometry: Dict, stock_type: str) -> float:
        """
        Calculate stock volume based on bounding box or cylinder.

        Args:
            geometry: Geometry dict from _extract_geometry
            stock_type: "bbox" or "cylinder"

        Returns:
            Stock volume in mm³
        """
        bbox = geometry["bbox"]
        width = bbox["width"]
        depth = bbox["depth"]
        height = bbox["height"]

        if stock_type == "bbox":
            # Rectangular stock (with allowances)
            allowance = 5.0  # mm per side
            stock_volume = (width + 2 * allowance) * (depth + 2 * allowance) * (height + allowance)
        elif stock_type == "cylinder":
            # Cylindrical stock (diameter = max(width, depth), length = height)
            import math
            diameter = max(width, depth) + 3.0  # diameter allowance
            radius = diameter / 2.0
            length = height + 5.0  # length allowance
            stock_volume = math.pi * radius * radius * length
        else:
            raise ValueError(f"Unknown stock type: {stock_type}")

        return stock_volume

    @staticmethod
    def _detect_constraints(geometry: Dict) -> list[str]:
        """
        Detect manufacturing constraints from geometry.

        Args:
            geometry: Geometry dict

        Returns:
            List of constraint identifiers (e.g., ["deep_pocket", "thin_wall"])
        """
        constraints = []
        bbox = geometry["bbox"]
        volume_mm3 = geometry["volume_mm3"]

        # Deep pocket detection (height/width ratio > 3)
        max_lateral = max(bbox["width"], bbox["depth"])
        if max_lateral > 0:
            aspect_ratio = bbox["height"] / max_lateral
            if aspect_ratio > 3.0:
                constraints.append("deep_pocket")

        # Thin wall detection (volume/surface_area ratio < threshold)
        surface_area_mm2 = geometry["surface_area_mm2"]
        if surface_area_mm2 > 0:
            thickness_estimate = volume_mm3 / surface_area_mm2
            if thickness_estimate < 3.0:  # < 3mm average thickness
                constraints.append("thin_wall")

        # High complexity (many faces)
        if geometry["face_count"] > 100:
            constraints.append("high_complexity")

        return constraints

    @staticmethod
    def _calculate_penalty(constraints: list[str], material_data: Dict) -> float:
        """
        Calculate total penalty multiplier from constraints.

        Args:
            constraints: List of constraint identifiers
            material_data: Material data dict

        Returns:
            Penalty multiplier (1.0 = no penalty, >1.0 = increased time)
        """
        multiplier = 1.0

        if "deep_pocket" in constraints:
            multiplier *= material_data.get("deep_pocket_penalty", 1.5)

        if "thin_wall" in constraints:
            multiplier *= material_data.get("thin_wall_penalty", 2.0)

        if "high_complexity" in constraints:
            multiplier *= 1.2  # 20% penalty for complex geometry

        return multiplier
