"""
Constraint Detection Service — Detect machining constraints from STEP geometry.

Detects:
- Deep pockets (depth/width > 3.0)
- Thin walls (thickness < 3.0mm)
- Long overhangs (overhang > 4x diameter) — NOT YET IMPLEMENTED

Pure OCCT geometry analysis, no AI, deterministic.

ADR-TBD: Machining Constraints Detection
"""

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# OCCT imports (conditional)
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_WIRE
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir
    from OCC.Core.TopoDS import topods
    from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
    from OCC.Core.ShapeAnalysis import ShapeAnalysis_Wire
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire
    from OCC.Core.TopTools import TopTools_IndexedMapOfShape
    from OCC.Core.TopExp import topexp

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False
    logger.warning("OCCT not available - constraint_detection_service disabled")


@dataclass
class DeepPocketConstraint:
    """Deep pocket constraint (depth/width > 3.0)."""

    depth_mm: float
    width_mm: float
    depth_to_width_ratio: float
    z_level: float
    severity: str  # "moderate" (3.0-4.0) | "severe" (>4.0)


@dataclass
class ThinWallConstraint:
    """Thin wall constraint (thickness < 3.0mm)."""

    thickness_mm: float
    location: Tuple[float, float, float]
    severity: str  # "moderate" (2.0-3.0mm) | "critical" (<2.0mm)


@dataclass
class ConstraintAnalysis:
    """Complete constraint analysis result."""

    deep_pockets: List[DeepPocketConstraint] = field(default_factory=list)
    thin_walls: List[ThinWallConstraint] = field(default_factory=list)
    has_critical_constraints: bool = False
    recommended_penalty_multiplier: float = 1.0


class ConstraintDetectionService:
    """
    Detects machining constraints from STEP geometry.
    Pure OCCT analysis, no AI.

    Algorithm:
    1. Deep pockets: Z-slicing method
       - Slice part in 20 Z-levels
       - For each level, find internal contours
       - Measure depth from contour to top
       - Measure width (min bbox dimension)
       - Flag if depth/width > 3.0

    2. Thin walls: Face-to-face distance
       - Get all planar faces
       - Find parallel face pairs
       - Measure minimum distance
       - Flag if distance < 3.0mm

    3. Calculate penalty multiplier:
       - Deep pocket (ratio 3-4): 1.5x
       - Deep pocket (ratio >4): 1.8x
       - Thin wall (<3mm): 2.5x
       - Multiple constraints: multiply factors
    """

    @staticmethod
    def analyze_constraints(step_path: Path) -> Optional[ConstraintAnalysis]:
        """
        Analyze STEP file for machining constraints.

        Args:
            step_path: Path to STEP file

        Returns:
            ConstraintAnalysis object or None on failure
        """
        if not OCCT_AVAILABLE:
            logger.error("OCCT not available")
            return None

        if not step_path.exists():
            logger.error(f"STEP file not found: {step_path}")
            return None

        try:
            # Load STEP file
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_path))

            if status != 1:  # IFSelect_RetDone
                logger.error(f"Failed to read STEP file: {step_path}")
                return None

            reader.TransferRoots()
            shape = reader.OneShape()

            # Detect constraints
            deep_pockets = ConstraintDetectionService.detect_deep_pockets(shape)
            thin_walls = ConstraintDetectionService.detect_thin_walls(shape)

            # Calculate penalty multiplier
            penalty = 1.0
            has_critical = False

            for pocket in deep_pockets:
                if pocket.severity == "severe":
                    penalty *= 1.8
                    has_critical = True
                else:
                    penalty *= 1.5

            for wall in thin_walls:
                penalty *= 2.5
                if wall.severity == "critical":
                    has_critical = True

            return ConstraintAnalysis(
                deep_pockets=deep_pockets,
                thin_walls=thin_walls,
                has_critical_constraints=has_critical,
                recommended_penalty_multiplier=round(penalty, 2),
            )

        except Exception as e:
            logger.error(f"Constraint analysis failed for {step_path.name}: {e}")
            return None

    @staticmethod
    def detect_deep_pockets(
        brep: Any, threshold_ratio: float = 3.0
    ) -> List[DeepPocketConstraint]:
        """
        Detect deep pockets by analyzing cylindrical faces (holes/bores).

        Algorithm:
        1. Extract all cylindrical faces with REVERSED orientation (internal)
        2. For each cylinder, measure depth (Z extent) and diameter
        3. Flag if depth/diameter > threshold_ratio

        This is more robust than Z-slicing for simple hole geometries.

        Args:
            brep: OCCT TopoDS_Shape object
            threshold_ratio: Minimum depth/width ratio to flag (default 3.0)

        Returns:
            List of DeepPocketConstraint objects
        """
        constraints = []

        try:
            from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
            from OCC.Core.GeomAbs import GeomAbs_Cylinder

            # Get overall bounding box for depth calculation
            bbox = Bnd_Box()
            brepbndlib.Add(brep, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

            # Extract all faces
            explorer = TopExp_Explorer(brep, TopAbs_FACE)

            while explorer.More():
                face = topods.Face(explorer.Current())
                surf = BRepAdaptor_Surface(face)

                # Check if cylindrical
                if surf.GetType() == GeomAbs_Cylinder:
                    cylinder = surf.Cylinder()
                    radius = cylinder.Radius()
                    diameter = radius * 2.0

                    # Check if internal (REVERSED orientation)
                    is_internal = face.Orientation() == 1  # TopAbs_REVERSED

                    if is_internal:
                        # Get face bounding box for depth
                        face_bbox = Bnd_Box()
                        brepbndlib.Add(face, face_bbox)
                        fx_min, fy_min, fz_min, fx_max, fy_max, fz_max = (
                            face_bbox.Get()
                        )

                        depth = fz_max - fz_min
                        width = diameter

                        # Check if deep pocket
                        if depth > 1.0 and width > 0.1:
                            ratio = depth / width

                            if ratio >= threshold_ratio:
                                severity = "severe" if ratio > 4.0 else "moderate"
                                z_level = fz_min

                                constraints.append(
                                    DeepPocketConstraint(
                                        depth_mm=round(depth, 2),
                                        width_mm=round(width, 2),
                                        depth_to_width_ratio=round(ratio, 2),
                                        z_level=round(z_level, 2),
                                        severity=severity,
                                    )
                                )

                explorer.Next()

        except Exception as e:
            logger.error(f"Deep pocket detection failed: {e}")

        # Deduplicate constraints (keep only highest ratio per z_level range)
        if constraints:
            constraints = ConstraintDetectionService._deduplicate_pockets(constraints)

        return constraints

    @staticmethod
    def _deduplicate_pockets(
        pockets: List[DeepPocketConstraint],
    ) -> List[DeepPocketConstraint]:
        """
        Deduplicate pocket constraints by grouping nearby z_levels.

        Keep only the constraint with highest ratio per 10mm z-range.
        """
        if not pockets:
            return []

        # Sort by z_level
        pockets.sort(key=lambda p: p.z_level)

        deduplicated = []
        current_group = [pockets[0]]

        for pocket in pockets[1:]:
            # If within 10mm of current group, add to group
            if pocket.z_level - current_group[0].z_level < 10.0:
                current_group.append(pocket)
            else:
                # Select best from current group
                best = max(current_group, key=lambda p: p.depth_to_width_ratio)
                deduplicated.append(best)
                current_group = [pocket]

        # Add last group
        if current_group:
            best = max(current_group, key=lambda p: p.depth_to_width_ratio)
            deduplicated.append(best)

        return deduplicated

    @staticmethod
    def detect_thin_walls(
        brep: Any, threshold_mm: float = 3.0
    ) -> List[ThinWallConstraint]:
        """
        Face-to-face distance measurement for thin wall detection.

        Steps:
        1. Get all planar faces
        2. For each pair, check if parallel
        3. Measure minimum distance (BRepExtrema_DistShapeShape)
        4. Return constraints where distance < threshold_mm

        Args:
            brep: OCCT TopoDS_Shape object
            threshold_mm: Maximum thickness to flag as thin wall (default 3.0)

        Returns:
            List of ThinWallConstraint objects
        """
        constraints = []

        try:
            # Extract all planar faces
            planar_faces = []
            explorer = TopExp_Explorer(brep, TopAbs_FACE)

            while explorer.More():
                face = topods.Face(explorer.Current())
                surf = BRepAdaptor_Surface(face)

                if surf.GetType() == GeomAbs_Plane:
                    plane = surf.Plane()
                    normal = plane.Axis().Direction()
                    planar_faces.append(
                        {
                            "face": face,
                            "normal": (normal.X(), normal.Y(), normal.Z()),
                            "location": plane.Location(),
                        }
                    )

                explorer.Next()

            # Check pairs for parallel faces
            for i, face1 in enumerate(planar_faces):
                for face2 in planar_faces[i + 1 :]:
                    # Check if normals are parallel (dot product close to ±1)
                    n1 = face1["normal"]
                    n2 = face2["normal"]
                    dot = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]

                    if abs(abs(dot) - 1.0) > 0.1:
                        continue  # Not parallel

                    # Measure distance
                    dist_calc = BRepExtrema_DistShapeShape(
                        face1["face"], face2["face"]
                    )
                    dist_calc.Perform()

                    if dist_calc.IsDone() and dist_calc.NbSolution() > 0:
                        distance = dist_calc.Value()

                        if 0.1 < distance < threshold_mm:
                            # Get midpoint location
                            p1 = dist_calc.PointOnShape1(1)
                            p2 = dist_calc.PointOnShape2(1)
                            mid_x = (p1.X() + p2.X()) / 2
                            mid_y = (p1.Y() + p2.Y()) / 2
                            mid_z = (p1.Z() + p2.Z()) / 2

                            severity = "critical" if distance < 2.0 else "moderate"

                            constraints.append(
                                ThinWallConstraint(
                                    thickness_mm=round(distance, 2),
                                    location=(
                                        round(mid_x, 2),
                                        round(mid_y, 2),
                                        round(mid_z, 2),
                                    ),
                                    severity=severity,
                                )
                            )

        except Exception as e:
            logger.error(f"Thin wall detection failed: {e}")

        # Deduplicate (remove constraints with very close locations)
        if constraints:
            constraints = ConstraintDetectionService._deduplicate_walls(constraints)

        return constraints

    @staticmethod
    def _deduplicate_walls(
        walls: List[ThinWallConstraint],
    ) -> List[ThinWallConstraint]:
        """
        Deduplicate thin wall constraints by location.

        Remove constraints within 5mm of each other, keeping the thinnest.
        """
        if not walls:
            return []

        deduplicated = []

        for wall in walls:
            # Check if close to existing constraint
            is_duplicate = False
            for existing in deduplicated:
                dx = wall.location[0] - existing.location[0]
                dy = wall.location[1] - existing.location[1]
                dz = wall.location[2] - existing.location[2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                if dist < 5.0:
                    # Duplicate found - keep thinner one
                    if wall.thickness_mm < existing.thickness_mm:
                        deduplicated.remove(existing)
                        deduplicated.append(wall)
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(wall)

        return deduplicated
