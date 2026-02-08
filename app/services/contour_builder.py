"""
Contour Builder — Deterministic profile_geometry from STEP features.

Builds exact outer_contour/inner_contour point arrays from
enriched STEP features (with z_min, z_max, radius, is_inner).

Uses face boundary data (vertex-traced z_min/z_max) for precise contours.

Key insight: STEP `sense` flag (.T./.F.) on ADVANCED_FACE reflects
surface normal orientation, NOT inner/outer in manufacturing sense.
For toroidal surfaces (fillets), sense=F often appears on outer fillets.
We use z-continuity with neighboring surfaces to decide placement.

ADR-035: Part of Feature Recognition pipeline.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Feature types that represent surfaces (vs CIRCLE-based 'hole')
_SURFACE_TYPES = {'cylindrical', 'cone', 'radius'}


class ContourBuilder:
    """Build deterministic profile_geometry from enriched STEP features."""

    def build_profile_geometry(
        self,
        features: List[Dict],
        advanced_faces: Dict,
        rotation_axis: str = 'z'
    ) -> Optional[Dict]:
        """
        Build profile_geometry from STEP-extracted features.

        Features must have z_min/z_max (from face boundary extraction).

        Returns:
            profile_geometry dict or None if not enough data
        """
        if not features:
            logger.warning("No features provided to build_profile_geometry")
            return None

        logger.info(f"ContourBuilder: building from {len(features)} features")

        outer, inner, holes = self._classify(features, rotation_axis)

        logger.info(
            f"Classified: {len(outer)} outer, {len(inner)} inner, {len(holes)} holes"
        )

        if not outer:
            logger.warning("No outer surfaces found for contour building")
            return None

        outer_contour = self._build_outer_contour(outer)
        inner_contour = self._build_inner_contour(inner)

        if not outer_contour or len(outer_contour) < 3:
            return None

        total_length = max(pt['z'] for pt in outer_contour)
        max_diameter = max(pt['r'] for pt in outer_contour) * 2

        return {
            'type': 'rotational',
            'outer_contour': outer_contour,
            'inner_contour': inner_contour,
            'total_length': round(total_length, 2),
            'max_diameter': round(max_diameter, 2),
            'holes': holes,
            'confidence': 1.0,
            'source': 'step_deterministic'
        }

    def _classify(
        self, features: List[Dict], rotation_axis: str
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Split features into outer, inner, and bolt holes.

        Classification priority:
        0. mfg_feature label from edge convexity (if available) — most reliable
        1. Bolt holes: off-axis cylinders (x/y position > 1.0 or axis misaligned)
        2. Cylindrical surfaces: use is_inner from ADVANCED_FACE sense flag
        3. Cones: use is_inner if present, default to outer
        4. Toroidal (fillets): NEVER use is_inner — classify by z-continuity
           with neighboring outer surfaces (sense flag unreliable for fillets)
        """
        outer = []
        inner = []
        holes = []

        # Labels from edge convexity that indicate INNER surfaces
        _INNER_MFG_LABELS = {
            'bore', 'groove_wall', 'groove_bottom',
            'pocket_wall', 'pocket_bottom', 'fillet_inner',
        }
        # Labels that indicate OUTER surfaces
        _OUTER_MFG_LABELS = {
            'shaft_segment', 'end_face', 'step_face',
            'step_transition', 'taper', 'fillet_outer',
        }

        # First pass: classify cylinders and cones
        for f in features:
            ftype = f.get('type', '')
            if ftype not in _SURFACE_TYPES:
                continue

            # Must have boundary data
            if 'z_min' not in f or 'z_max' not in f:
                continue

            # Off-axis surface: bolt hole, cross-hole, or angled feature
            # Applies to cylindrical AND conical surfaces
            # Check ALL surfaces, not just outer — inner off-axis are cross-holes too
            if ftype in ('cylindrical', 'cone') and self._is_off_axis(f, rotation_axis):
                if ftype == 'cylindrical':
                    holes.append({
                        'diameter': round(f.get('radius', 0) * 2, 2),
                        'depth': round(f.get('z_max', 0) - f.get('z_min', 0), 2),
                        'position': f"x={f.get('x_position', 0):.1f}, y={f.get('y_position', 0):.1f}"
                    })
                # Skip off-axis cones entirely (angled features, not part of profile)
                continue

            if ftype == 'radius':
                # Defer toroidal classification to second pass
                continue

            # Priority 1: Use mfg_feature label from edge convexity if available
            mfg = f.get('mfg_feature', '')
            if mfg in _INNER_MFG_LABELS:
                inner.append(f)
                continue
            if mfg in _OUTER_MFG_LABELS:
                outer.append(f)
                continue

            # Priority 2: Fallback to is_inner heuristic (original logic)
            is_inner = f.get('is_inner', False)
            if is_inner:
                inner.append(f)
            else:
                outer.append(f)

        # Post-process: fix inverted sense flags for on-axis cylinders
        # Some STEP files have incorrect ADVANCED_FACE sense flags.
        # Heuristic: for on-axis cylinders, largest radius → outer (main body)
        on_axis_cylinders_inner = [f for f in inner if f.get('type') == 'cylindrical']
        on_axis_cylinders_outer = [f for f in outer if f.get('type') == 'cylindrical']
        all_on_axis_cyl = on_axis_cylinders_inner + on_axis_cylinders_outer

        if all_on_axis_cyl:
            max_radius = max(f.get('radius', 0) for f in all_on_axis_cyl)
            # Find cylinders with largest radius (within 0.5mm tolerance)
            largest_cylinders = [f for f in all_on_axis_cyl if f.get('radius', 0) >= max_radius - 0.5]

            # Move largest cylinders to outer
            for f in largest_cylinders:
                if f in inner:
                    inner.remove(f)
                    outer.append(f)

        # Second pass: classify toroidal surfaces by z-continuity
        outer_intervals = [(s.get('z_min', 0), s.get('z_max', 0)) for s in outer]

        for f in features:
            if f.get('type') != 'radius':
                continue
            if 'z_min' not in f or 'z_max' not in f:
                continue

            z_min = f.get('z_min', 0)
            z_max = f.get('z_max', 0)

            # Check if this fillet connects to outer surfaces at z_min or z_max
            touches_outer = False
            for oz_min, oz_max in outer_intervals:
                # Fillet z_min touches an outer surface's z_max (or vice versa)
                if (abs(z_min - oz_max) < 0.01 or abs(z_min - oz_min) < 0.01 or
                        abs(z_max - oz_min) < 0.01 or abs(z_max - oz_max) < 0.01):
                    touches_outer = True
                    break

            if touches_outer:
                outer.append(f)
                # Update intervals for subsequent fillets
                outer_intervals.append((z_min, z_max))
            else:
                inner.append(f)

        # Third pass: reclassify surfaces that lie INSIDE a larger outer surface
        # E.g., a small cylinder at z=51-53 inside a larger cylinder at z=0-85
        # These are bore chamfers/transitions, not outer contour features.
        # IMPORTANT: For cones, 'radius' is semi_angle, not geometric radius!
        # Use boundary_zr_pairs max(r) for the actual geometric size.
        if len(outer) >= 2:
            reclassified = []

            def _effective_radius(surf: Dict) -> float:
                """Get effective geometric radius for enclosed check."""
                zr = surf.get('boundary_zr_pairs', [])
                if zr:
                    return max(r for _z, r in zr)
                return surf.get('radius', 0)

            new_outer = []
            for s in outer:
                s_r = _effective_radius(s)
                s_zmin = s.get('z_min', 0)
                s_zmax = s.get('z_max', 0)

                # Check if this surface is enclosed within a larger outer surface
                enclosed = False
                for other in outer:
                    if other is s:
                        continue
                    o_r = _effective_radius(other)
                    o_zmin = other.get('z_min', 0)
                    o_zmax = other.get('z_max', 0)
                    # 'other' must be bigger AND fully contain 's' in z-range
                    if (o_r > s_r * 1.5 and
                            o_zmin <= s_zmin + 0.1 and o_zmax >= s_zmax - 0.1):
                        enclosed = True
                        break

                if enclosed:
                    inner.append(s)
                    reclassified.append(s)
                else:
                    new_outer.append(s)

            if reclassified:
                outer = new_outer

        return outer, inner, holes

    def _is_off_axis(self, f: Dict, rotation_axis: str) -> bool:
        """
        Check if a surface is off-axis (bolt hole, cross-hole, angled feature).

        A surface is off-axis if its axis_direction doesn't align with
        the part's rotation axis. Works for X, Y, Z oriented parts.

        Note: position-based check only for Z-axis parts (where origin
        is typically on the rotation axis). For X/Y-axis parts, STEP
        placements use absolute coordinates → position check unreliable.
        """
        axis_dir = f.get('axis_direction')
        if axis_dir and isinstance(axis_dir, tuple) and len(axis_dir) >= 3:
            ax_idx = {'x': 0, 'y': 1, 'z': 2}.get(rotation_axis, 2)
            # Surface axis must be parallel to rotation axis (±1 on ax_idx, ~0 elsewhere)
            if abs(abs(axis_dir[ax_idx]) - 1.0) > 0.1:
                return True

        # Off-center position check (bolt circle holes on Z-axis parts only)
        # Z-axis parts typically have origin on rotation axis (x=0, y=0)
        if rotation_axis == 'z':
            x_pos = abs(f.get('x_position', 0.0))
            y_pos = abs(f.get('y_position', 0.0))
            if x_pos > 1.0 or y_pos > 1.0:
                return True

        return False

    def _build_outer_contour(self, surfaces: List[Dict]) -> List[Dict]:
        """
        Build outer contour by tracing surfaces in z-order.

        Instead of collecting all points and sorting (which breaks at
        step transitions like Ø36→Ø30), we trace surfaces sequentially
        and insert vertical transitions where diameters change.
        """
        sorted_surfs = sorted(surfaces, key=lambda s: s.get('z_min', 0.0))

        z_start = min(s.get('z_min', 0.0) for s in sorted_surfs)
        z_end = max(s.get('z_max', 0.0) for s in sorted_surfs)

        # Collect (z_min, z_max, points[]) for each surface
        segments = []
        for surf in sorted_surfs:
            ftype = surf.get('type', '')
            z_min = surf.get('z_min', 0.0)
            z_max = surf.get('z_max', 0.0)

            if ftype == 'cylindrical':
                radius = surf.get('radius', 0.0)
                pts = [{'r': radius, 'z': z_min}, {'r': radius, 'z': z_max}]
            elif ftype == 'cone':
                pts = self._cone_boundary_points(surf)
            elif ftype == 'radius':
                pts = self._fillet_boundary_points(surf)
            else:
                continue

            if pts:
                segments.append({'z_min': z_min, 'z_max': z_max, 'points': pts})

        if not segments:
            return []

        # Build contour by tracing segments in order
        contour = [{'r': 0.0, 'z': z_start}]

        for seg in segments:
            pts = seg['points']
            first_pt = pts[0]
            last_contour = contour[-1]

            # If there's a gap in z, we need to handle it
            # (shouldn't happen with good data, but be safe)

            # If radius changes at the same z → vertical step transition
            # The new segment starts at its first point
            if abs(first_pt['z'] - last_contour['z']) < 0.02:
                # Same z position: check if this is a vertical step or just continuation
                if abs(first_pt['r'] - last_contour['r']) > 0.01:
                    # Vertical step (diameter change at same z)
                    contour.append(first_pt)
                # else: first point is duplicate of last contour point (continuous transition)

                # Add remaining points (ALWAYS from pts[1:] to avoid duplicates)
                for pt in pts[1:]:
                    contour.append(pt)
            else:
                # Different z: check if first point is duplicate before adding
                if abs(first_pt['z'] - last_contour['z']) > 0.01 or abs(first_pt['r'] - last_contour['r']) > 0.01:
                    contour.append(first_pt)
                # Add remaining points
                for pt in pts[1:]:
                    contour.append(pt)

        # Deduplicate consecutive near-identical points (0.005mm threshold = 5µm)
        # CRITICAL: Must be < 0.01mm to catch chamfer/fillet endpoint duplicates
        result = [contour[0]]
        for pt in contour[1:]:
            rpt = {'r': round(pt['r'], 2), 'z': round(pt['z'], 2)}
            last = result[-1]
            # Use 0.005mm threshold to catch duplicates but preserve vertical steps
            if abs(rpt['z'] - last['z']) > 0.005 or abs(rpt['r'] - last['r']) > 0.005:
                result.append(rpt)

        # Ensure first point is on axis
        if result[0]['r'] != 0.0:
            result.insert(0, {'r': 0.0, 'z': round(z_start, 2)})

        # Ensure last point is on axis
        if result[-1]['r'] != 0.0:
            result.append({'r': 0.0, 'z': round(z_end, 2)})

        return result

    def _cone_boundary_points(self, surf: Dict) -> List[Dict]:
        """
        Get cone start/end points from vertex z→r mapping.

        Uses boundary_zr_pairs (exact vertex data) when available.
        Each pair is (z, r) from actual STEP vertex coordinates.
        """
        zr_pairs = surf.get('boundary_zr_pairs', [])

        if len(zr_pairs) >= 2:
            # Use exact vertex data: first and last z→r pairs
            # For cones with bolt holes, intermediate pairs exist but
            # we only need the endpoints (min z and max z)
            z_start, r_start = zr_pairs[0]
            z_end, r_end = zr_pairs[-1]
            return [
                {'r': r_start, 'z': z_start},
                {'r': r_end, 'z': z_end}
            ]

        # Fallback to boundary_r_values
        z_min = surf.get('z_min', 0.0)
        z_max = surf.get('z_max', 0.0)
        br = surf.get('boundary_r_values', [])

        if len(br) >= 2:
            r_small = br[0]
            r_large = br[-1]
            return [
                {'r': r_large, 'z': z_min},
                {'r': r_small, 'z': z_max}
            ]

        radius = surf.get('radius', 0.0)
        return [
            {'r': radius, 'z': z_min},
            {'r': radius, 'z': z_max}
        ]

    def _fillet_boundary_points(self, surf: Dict) -> List[Dict]:
        """
        Get fillet arc points from vertex z→r mapping.

        Uses boundary_zr_pairs for exact start/end points,
        adds a midpoint arc approximation.
        """
        zr_pairs = surf.get('boundary_zr_pairs', [])

        if len(zr_pairs) >= 2:
            z_start, r_start = zr_pairs[0]
            z_end, r_end = zr_pairs[-1]

            # 3-point arc approximation
            z_mid = (z_start + z_end) / 2
            r_mid = (r_start + r_end) / 2

            return [
                {'r': r_start, 'z': z_start},
                {'r': r_mid, 'z': z_mid},
                {'r': r_end, 'z': z_end}
            ]

        # Fallback to boundary_r_values
        z_min = surf.get('z_min', 0.0)
        z_max = surf.get('z_max', 0.0)
        br = surf.get('boundary_r_values', [])

        if len(br) >= 2:
            r_small = br[0]
            r_large = br[-1]
            z_mid = (z_min + z_max) / 2
            r_mid = (r_small + r_large) / 2
            return [
                {'r': r_large, 'z': z_min},
                {'r': r_mid, 'z': z_mid},
                {'r': r_small, 'z': z_max}
            ]

        # Fallback
        major_r = surf.get('major_radius', surf.get('radius', 0.0))
        minor_r = surf.get('minor_radius', surf.get('radius', 1.0))
        return [
            {'r': major_r + minor_r, 'z': z_min},
            {'r': major_r, 'z': (z_min + z_max) / 2},
            {'r': major_r - minor_r, 'z': z_max}
        ]

    def _build_inner_contour(self, surfaces: List[Dict]) -> List[Dict]:
        """
        Build inner contour as outer envelope of inner surfaces.

        Inner surfaces often overlap in z-range (e.g. three concentric bores
        all spanning z=[0,12], or a large bore z=[-2.5,0] overlapping with
        a smaller bore z=[-0.5,18.5]). Simple sequential tracing fails here.

        Strategy: group overlapping surfaces into z-clusters, then for each
        cluster take the outermost (max r) profile — this is what you see
        in a 2D cross-section as the bore wall.
        """
        valid_types = ('cylindrical', 'cone', 'radius')
        inner_surfs = [s for s in surfaces if s.get('type', '') in valid_types]
        if not inner_surfs:
            return []

        # Collect segments: (z_min, z_max, points[])
        segments = []
        for surf in inner_surfs:
            ftype = surf.get('type', '')
            z_min = surf.get('z_min', 0.0)
            z_max = surf.get('z_max', 0.0)

            if ftype == 'cylindrical':
                radius = surf.get('radius', 0.0)
                pts = [{'r': radius, 'z': z_min}, {'r': radius, 'z': z_max}]
            elif ftype == 'cone':
                pts = self._cone_boundary_points(surf)
            elif ftype == 'radius':
                pts = self._fillet_boundary_points(surf)
            else:
                continue

            if pts:
                max_r = max(p['r'] for p in pts)
                segments.append({
                    'z_min': z_min, 'z_max': z_max,
                    'points': pts, 'max_r': max_r
                })

        if not segments:
            return []

        # Check for overlapping segments: if any two segments overlap in z,
        # we need the envelope approach. Otherwise, sequential tracing works.
        segments.sort(key=lambda s: (s['z_min'], -s['max_r']))

        has_overlap = False
        for i in range(len(segments) - 1):
            if segments[i]['z_max'] > segments[i + 1]['z_min'] + 0.1:
                has_overlap = True
                break

        if not has_overlap:
            # No overlap: simple sequential tracing (as for outer contour)
            return self._trace_sequential(segments)

        # Overlap detected: build envelope by selecting the outermost surface
        # at each z-transition point.
        # Collect all z-breakpoints where the profile may change
        z_breaks = set()
        for seg in segments:
            z_breaks.add(round(seg['z_min'], 2))
            z_breaks.add(round(seg['z_max'], 2))
        z_sorted = sorted(z_breaks)

        if len(z_sorted) < 2:
            return self._trace_sequential(segments)

        # For each z-interval, find the segment with the largest r
        contour = []
        for i in range(len(z_sorted) - 1):
            z_lo = z_sorted[i]
            z_hi = z_sorted[i + 1]
            z_mid = (z_lo + z_hi) / 2

            # Find active segments at z_mid
            best_r = 0.0
            best_seg = None
            for seg in segments:
                if seg['z_min'] - 0.01 <= z_mid <= seg['z_max'] + 0.01:
                    # Interpolate r at z_mid from segment points
                    r_at_mid = self._interpolate_r(seg['points'], z_mid)
                    if r_at_mid > best_r:
                        best_r = r_at_mid
                        best_seg = seg

            if best_seg is None:
                continue

            # Add points for this interval
            r_lo = self._interpolate_r(best_seg['points'], z_lo)
            r_hi = self._interpolate_r(best_seg['points'], z_hi)

            contour.append({'r': r_lo, 'z': z_lo})
            contour.append({'r': r_hi, 'z': z_hi})

        # Deduplicate consecutive near-identical points
        if not contour:
            return []

        result = [{'r': round(contour[0]['r'], 2), 'z': round(contour[0]['z'], 2)}]
        for pt in contour[1:]:
            rpt = {'r': round(pt['r'], 2), 'z': round(pt['z'], 2)}
            last = result[-1]
            if abs(rpt['z'] - last['z']) > 0.01 or abs(rpt['r'] - last['r']) > 0.01:
                result.append(rpt)

        return result

    def _trace_sequential(self, segments: List[Dict]) -> List[Dict]:
        """Trace non-overlapping segments sequentially (for simple inner bores)."""
        contour = []
        for seg in segments:
            pts = seg['points']
            first_pt = pts[0]

            if contour:
                last_contour = contour[-1]
                if abs(first_pt['z'] - last_contour['z']) < 0.02:
                    if abs(first_pt['r'] - last_contour['r']) > 0.01:
                        contour.append(first_pt)
                    for pt in pts[1:]:
                        contour.append(pt)
                else:
                    for pt in pts:
                        contour.append(pt)
            else:
                for pt in pts:
                    contour.append(pt)

        result = [{'r': round(contour[0]['r'], 2), 'z': round(contour[0]['z'], 2)}]
        for pt in contour[1:]:
            rpt = {'r': round(pt['r'], 2), 'z': round(pt['z'], 2)}
            last = result[-1]
            if abs(rpt['z'] - last['z']) > 0.01 or abs(rpt['r'] - last['r']) > 0.01:
                result.append(rpt)
        return result

    @staticmethod
    def _interpolate_r(points: List[Dict], z: float) -> float:
        """Interpolate radius at given z from segment points."""
        if not points:
            return 0.0
        if len(points) == 1:
            return points[0]['r']

        # Clamp to segment range
        z_min_pt = min(p['z'] for p in points)
        z_max_pt = max(p['z'] for p in points)

        if z <= z_min_pt:
            return points[0]['r']
        if z >= z_max_pt:
            return points[-1]['r']

        # Linear interpolation between consecutive points
        for i in range(len(points) - 1):
            z0, r0 = points[i]['z'], points[i]['r']
            z1, r1 = points[i + 1]['z'], points[i + 1]['r']
            if z0 <= z <= z1:
                if abs(z1 - z0) < 0.001:
                    return max(r0, r1)
                t = (z - z0) / (z1 - z0)
                return r0 + t * (r1 - r0)

        return points[-1]['r']

    def _sort_and_deduplicate(self, points: List[Dict]) -> List[Dict]:
        """Sort points by z and remove near-duplicates."""
        sorted_pts = sorted(points, key=lambda p: (p['z'], p['r']))

        result = []
        for pt in sorted_pts:
            rpt = {'r': round(pt['r'], 2), 'z': round(pt['z'], 2)}
            if not result:
                result.append(rpt)
            else:
                last = result[-1]
                if abs(rpt['z'] - last['z']) > 0.01 or abs(rpt['r'] - last['r']) > 0.01:
                    result.append(rpt)

        return result
