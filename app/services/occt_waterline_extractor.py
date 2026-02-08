"""
OCCT Waterline Extractor — Extract r(z) profile from STEP files.

Extracts waterline (polar coordinates) from rotational parts using OCCT.
Segments waterline into manufacturing features (shaft/groove/bore).

ADR-TBD: Vision Hybrid Pipeline
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# OCCT imports (conditional)
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Cone
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.TopoDS import topods

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False
    logger.warning("OCCT not available - occt_waterline_extractor disabled")


class WaterlineExtractor:
    """Extract r(z) waterline profile from STEP files using OCCT."""

    def extract_waterline(self, step_path: Path) -> Optional[Dict]:
        """
        Extract waterline polar coordinates from STEP file.

        Args:
            step_path: Path to STEP file

        Returns:
            Dict with:
            - r_values: List[float] - radius values
            - z_values: List[float] - z coordinates
            - max_diameter: float - maximum diameter (mm)
            - total_length: float - total length (mm)
            - rotation_axis: str - detected axis ('x', 'y', 'z')
            - segments: List[Dict] - feature segments
            None if extraction fails
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

            # Extract metadata for bbox and volume
            metadata = self._extract_metadata(shape)

            # Detect rotation axis
            rotation_axis = self._detect_rotation_axis(shape)
            if not rotation_axis:
                logger.warning(f"No rotation axis detected for {step_path.name}")
                rotation_axis = 'z'  # Default fallback

            # Extract cylindrical surfaces
            cylindrical_surfaces = self._extract_cylindrical_surfaces(shape)

            if not cylindrical_surfaces:
                logger.warning(f"No cylindrical surfaces found in {step_path.name}")
                return None

            # Build waterline from cylindrical surfaces
            r_values, z_values = self._build_waterline(
                cylindrical_surfaces, rotation_axis
            )

            if len(r_values) < 2:
                logger.warning(f"Insufficient waterline points in {step_path.name}")
                return None

            max_diameter = max(r_values) * 2.0
            total_length = max(z_values) - min(z_values)

            # Segment waterline into features
            segments = self._segment_waterline(r_values, z_values)

            return {
                'r_values': [round(r, 3) for r in r_values],
                'z_values': [round(z, 3) for z in z_values],
                'max_diameter': round(max_diameter, 2),
                'total_length': round(total_length, 2),
                'rotation_axis': rotation_axis,
                'segments': segments,
                'volume_cm3': metadata.get('volume_cm3', 0),
                'bounding_box': metadata.get('bounding_box', {}),
            }

        except Exception as e:
            logger.error(f"Waterline extraction failed for {step_path.name}: {e}")
            return None

    def _extract_metadata(self, shape) -> Dict:
        """Extract volume and bounding box from shape."""
        metadata = {}

        try:
            # Volume
            props = GProp_GProps()
            brepgprop.VolumeProperties(shape, props)
            volume_mm3 = props.Mass()
            metadata['volume_cm3'] = round(volume_mm3 / 1000.0, 2)

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
            }

        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")

        return metadata

    def _detect_rotation_axis(self, shape) -> Optional[str]:
        """Detect primary rotation axis from cylindrical surfaces."""
        axis_votes = {'x': 0, 'y': 0, 'z': 0}

        explorer = TopExp_Explorer(shape, TopAbs_FACE)

        while explorer.More():
            face = topods.Face(explorer.Current())
            surf = BRepAdaptor_Surface(face)

            if surf.GetType() == GeomAbs_Cylinder:
                axis = surf.Cylinder().Axis().Direction()
                ax_tuple = (axis.X(), axis.Y(), axis.Z())

                # Classify axis
                if abs(ax_tuple[2]) > 0.9:
                    axis_votes['z'] += 1
                elif abs(ax_tuple[0]) > 0.9:
                    axis_votes['x'] += 1
                elif abs(ax_tuple[1]) > 0.9:
                    axis_votes['y'] += 1

            explorer.Next()

        if sum(axis_votes.values()) == 0:
            return None

        return max(axis_votes.items(), key=lambda x: x[1])[0]

    def _extract_cylindrical_surfaces(self, shape) -> List[Dict]:
        """Extract cylindrical surface data (radius, z_min, z_max, orientation)."""
        surfaces = []

        explorer = TopExp_Explorer(shape, TopAbs_FACE)

        while explorer.More():
            face = topods.Face(explorer.Current())
            surf = BRepAdaptor_Surface(face)

            if surf.GetType() == GeomAbs_Cylinder:
                cylinder = surf.Cylinder()
                radius = cylinder.Radius()
                axis = cylinder.Axis().Direction()
                location = cylinder.Location()

                # Get face orientation (FORWARD=outer, REVERSED=inner)
                orientation = face.Orientation()
                is_inner = (orientation == 1)  # TopAbs_REVERSED

                # Compute z extent from bounding box
                bbox = Bnd_Box()
                brepbndlib.Add(face, bbox)
                xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

                surfaces.append({
                    'type': 'cylindrical',
                    'radius': round(radius, 3),
                    'z_min': round(zmin, 3),
                    'z_max': round(zmax, 3),
                    'axis': (axis.X(), axis.Y(), axis.Z()),
                    'location': (location.X(), location.Y(), location.Z()),
                    'is_inner': is_inner,
                })

            explorer.Next()

        return surfaces

    def _build_waterline(
        self, surfaces: List[Dict], rotation_axis: str
    ) -> Tuple[List[float], List[float]]:
        """
        Build r(z) waterline from cylindrical surfaces.

        For each surface, create points at z_min and z_max.
        Sort by z coordinate.
        """
        points = []

        for surf in surfaces:
            z_min = surf['z_min']
            z_max = surf['z_max']
            radius = surf['radius']

            points.append((z_min, radius))
            points.append((z_max, radius))

        # Sort by z coordinate
        points.sort(key=lambda p: p[0])

        # Remove duplicates (keep first occurrence)
        unique_points = []
        seen_z = set()
        for z, r in points:
            if z not in seen_z:
                unique_points.append((z, r))
                seen_z.add(z)

        z_values = [p[0] for p in unique_points]
        r_values = [p[1] for p in unique_points]

        return r_values, z_values

    def _segment_waterline(
        self, r_values: List[float], z_values: List[float]
    ) -> List[Dict]:
        """
        Segment waterline into manufacturing features.

        Creates segments between consecutive waterline points.
        Classifies each segment by radius change:
        - shaft: constant radius (±0.5mm)
        - groove: radius decreases (external groove)
        - bore: radius increases (internal bore)
        - taper: gradual radius change

        Returns list of segments with type, z_start, z_end, r_avg, length.
        """
        if len(r_values) < 2:
            return []

        segments = []

        # Create segment between each pair of consecutive points
        for i in range(len(r_values) - 1):
            z_start = z_values[i]
            z_end = z_values[i + 1]
            r_start = r_values[i]
            r_end = r_values[i + 1]
            r_avg = (r_start + r_end) / 2.0
            length = abs(z_end - z_start)

            # Skip zero-length segments
            if length < 0.1:
                continue

            # Classify by radius change
            r_change = r_end - r_start

            if abs(r_change) <= 0.5:
                seg_type = 'shaft'
            elif r_change < -0.5:
                seg_type = 'groove'
            elif r_change > 0.5:
                seg_type = 'bore'
            else:
                seg_type = 'taper'

            segments.append({
                'type': seg_type,
                'z_start': round(z_start, 2),
                'z_end': round(z_end, 2),
                'length': round(length, 2),
                'r_avg': round(r_avg, 2),
                'diameter': round(r_avg * 2, 2),
            })

        return segments
