"""GESTIMA - Setup Planning Service

Determines optimal number of setups (upnutí) based on geometry analysis.

Key decisions:
- 1 setup: All features accessible from one side
- 2 setups: Front/back features, or parting operation
- 3+ setups: Complex prismatic (multiple faces) OR mixed rotational/milling

Design: Data-driven analysis, no hardcoded rules.
Pattern: Analyze geometry → determine accessibility → return setup list
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SetupPlanner:
    """
    Analyze geometry and determine optimal setup strategy.

    Factors considered:
    - Part type (rotational/prismatic/mixed)
    - Feature accessibility (axial vs radial vs multi-face)
    - Tolerance requirements (tight tolerances → fewer setups)
    - Tool access constraints (deep holes, threading)
    """

    # Setup time estimates [min] based on fixture type
    SETUP_TIMES = {
        "3jaw_chuck": 25.0,      # 3-čelisťové sklíčidlo (first setup)
        "collet": 15.0,          # Klešt (second setup, known diameter)
        "faceplate": 35.0,       # Lícní deska (complex clamping)
        "tailstock": 20.0,       # Hrot (long parts)
        "vise": 20.0,            # Svěrák (first milling setup)
        "fixture": 10.0,         # Upínka (additional setups)
        "tombstone": 30.0,       # Tombstone (5-axis multi-part)
        "vacuum": 25.0,          # Vakuové upnutí (thin parts)
    }

    def plan_setups(self, geometry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Determine setups needed for part manufacturing.

        Args:
            geometry: Full geometry dict from Claude (part_type, profile_geometry, features)

        Returns:
            List of setup dicts:
            [
                {
                    "setup_id": 1,
                    "description": "OP10 - Front face, OD turning, drilling",
                    "features": [...],  # features accessible in this setup
                    "fixture": "3-jaw chuck",
                    "estimated_setup_time": 25.0,  # minutes
                    "machine_type": "lathe_3ax"
                },
                ...
            ]
        """
        part_type = geometry.get("part_type", "rotational")
        features = geometry.get("profile_geometry", {}).get("features", [])

        if not features:
            logger.warning("No features in geometry, returning single setup")
            return self._default_single_setup(part_type)

        # Dispatch based on part type
        if part_type == "rotational":
            return self._plan_turning_setups(geometry, features)
        elif part_type == "prismatic":
            return self._plan_milling_setups(geometry, features)
        elif part_type == "mixed":
            return self._plan_hybrid_setups(geometry, features)
        else:
            logger.warning(f"Unknown part_type: {part_type}, defaulting to rotational")
            return self._plan_turning_setups(geometry, features)

    def _default_single_setup(self, part_type: str) -> List[Dict[str, Any]]:
        """Fallback: single setup when no features detected."""
        if part_type == "prismatic":
            fixture = "vise"
            machine = "mill_3ax"
        else:
            fixture = "3jaw_chuck"
            machine = "lathe_3ax"

        return [{
            "setup_id": 1,
            "description": "OP10 Základní obrábění",
            "features": [],
            "fixture": fixture,
            "estimated_setup_time": self.SETUP_TIMES.get(fixture, 20.0),
            "machine_type": machine,
        }]

    def _plan_turning_setups(
        self,
        geometry: Dict[str, Any],
        features: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Plan setups for turning (rotational) parts.

        Rules:
        - 1 setup: All features on front face (z < 50% length)
        - 2 setups: Features on both faces OR parting operation
        - Live tooling: Radial holes/slots → adds operations to setup 1 (needs 4-axis lathe)
        """
        setups = []

        # Analyze feature distribution
        stock_length = geometry.get("stock", {}).get("dimensions", {}).get("length", 100.0)
        mid_z = stock_length / 2

        front_features = []
        back_features = []
        radial_features = []
        has_parting = False

        for feat in features:
            ftype = feat.get("type", "")
            z_pos = feat.get("position", {}).get("z", 0.0)

            # Check for parting
            if ftype == "parting":
                has_parting = True
                front_features.append(feat)
                continue

            # Check for radial features (live tooling)
            if ftype in ["lt_drill", "lt_mill", "lt_flat", "lt_slot"]:
                radial_features.append(feat)
                front_features.append(feat)  # Usually accessible from front setup
                continue

            # Distribute by Z position
            if z_pos < mid_z:
                front_features.append(feat)
            else:
                back_features.append(feat)

        # Determine number of setups
        needs_two_setups = (
            len(back_features) > 0 or
            has_parting or
            stock_length > 150  # Long parts often need tailstock + flip
        )

        # Setup 1: Front side
        machine_type = "lathe_4ax" if radial_features else "lathe_3ax"
        fixture = "3jaw_chuck" if not has_parting else "faceplate"

        setup1_desc = "OP10 Soustružení - přední strana"
        if radial_features:
            setup1_desc += " + live tooling"

        setups.append({
            "setup_id": 1,
            "description": setup1_desc,
            "features": front_features,
            "fixture": fixture,
            "estimated_setup_time": self.SETUP_TIMES.get(fixture, 25.0),
            "machine_type": machine_type,
            "notes": f"{len(front_features)} operations, {len(radial_features)} radial"
        })

        # Setup 2: Back side (if needed)
        if needs_two_setups and back_features:
            setups.append({
                "setup_id": 2,
                "description": "OP20 Soustružení - zadní strana",
                "features": back_features,
                "fixture": "collet",
                "estimated_setup_time": self.SETUP_TIMES["collet"],
                "machine_type": "lathe_3ax",
                "notes": f"{len(back_features)} operations"
            })

        return setups

    def _plan_milling_setups(
        self,
        geometry: Dict[str, Any],
        features: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Plan setups for prismatic (milling) parts.

        Rules:
        - Count faces with features
        - 1-2 faces → 3-axis mill (multiple setups)
        - 3+ faces → evaluate 5-axis (1 setup) vs 3-axis (multiple setups)
        """
        # Analyze which faces have features
        faces_with_features = {}
        for feat in features:
            face = feat.get("face", "top")  # top, bottom, left, right, front, back
            if face not in faces_with_features:
                faces_with_features[face] = []
            faces_with_features[face].append(feat)

        num_faces = len(faces_with_features)

        if num_faces <= 2:
            # 3-axis milling: 1 setup per face
            return self._plan_3ax_milling(geometry, faces_with_features)
        else:
            # 5-axis vs 3-axis decision
            # For now, return 3-axis plan (5-axis is premium, needs cost analysis)
            logger.info(f"{num_faces} faces detected → 3-axis milling (5-axis evaluation TODO)")
            return self._plan_3ax_milling(geometry, faces_with_features)

    def _plan_3ax_milling(
        self,
        geometry: Dict[str, Any],
        faces_with_features: Dict[str, List[Dict]],
    ) -> List[Dict[str, Any]]:
        """Plan 3-axis milling: 1 setup per face."""
        setups = []

        for i, (face, features) in enumerate(sorted(faces_with_features.items()), start=1):
            fixture = "vise" if i == 1 else "fixture"
            setup_time = self.SETUP_TIMES[fixture]

            setups.append({
                "setup_id": i,
                "description": f"OP{i}0 Frézování - {face} strana",
                "features": features,
                "fixture": fixture,
                "estimated_setup_time": setup_time,
                "machine_type": "mill_3ax",
                "notes": f"{len(features)} operations na {face} straně"
            })

        return setups

    def _plan_hybrid_setups(
        self,
        geometry: Dict[str, Any],
        features: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Plan setups for mixed parts (rotational + prismatic features).

        Strategy:
        - If dominant type is turning (>70% features) → turn first, mill second
        - If dominant type is milling → mill first, turn second (less common)
        - If balanced → turn first (easier fixturing)
        """
        turning_features = []
        milling_features = []

        for feat in features:
            ftype = feat.get("type", "")
            # Classify feature
            if ftype in ["od_rough", "od_finish", "id_rough", "id_finish", "thread_od", "thread_id",
                         "groove_od", "groove_id", "chamfer", "radius", "parting"]:
                turning_features.append(feat)
            elif ftype in ["pocket_rough", "pocket_finish", "slot", "face_mill", "mill_drill",
                           "mill_tap", "contour_2d", "surface_3d"]:
                milling_features.append(feat)
            else:
                # Unknown → assume turning (conservative)
                turning_features.append(feat)

        turning_pct = len(turning_features) / len(features) if features else 0.0

        setups = []

        if turning_pct > 0.7:
            # Turning-dominant: turn first, mill second
            logger.info(f"Hybrid part: {turning_pct:.0%} turning → turn first")

            # Setup 1: Turning
            setups.append({
                "setup_id": 1,
                "description": "OP10 Soustružení",
                "features": turning_features,
                "fixture": "3jaw_chuck",
                "estimated_setup_time": self.SETUP_TIMES["3jaw_chuck"],
                "machine_type": "lathe_3ax",
                "notes": f"{len(turning_features)} turning operations"
            })

            # Setup 2: Milling
            if milling_features:
                setups.append({
                    "setup_id": 2,
                    "description": "OP20 Frézování",
                    "features": milling_features,
                    "fixture": "vise",
                    "estimated_setup_time": self.SETUP_TIMES["vise"],
                    "machine_type": "mill_3ax",
                    "notes": f"{len(milling_features)} milling operations"
                })
        else:
            # Milling-dominant or balanced: turn first (easier fixturing)
            logger.info(f"Hybrid part: {turning_pct:.0%} turning → turn first, mill second")

            # Setup 1: Turning (create basic shape)
            if turning_features:
                setups.append({
                    "setup_id": 1,
                    "description": "OP10 Soustružení - základní tvar",
                    "features": turning_features,
                    "fixture": "3jaw_chuck",
                    "estimated_setup_time": self.SETUP_TIMES["3jaw_chuck"],
                    "machine_type": "lathe_3ax",
                    "notes": f"{len(turning_features)} turning operations"
                })

            # Setup 2: Milling (add details)
            setups.append({
                "setup_id": 2 if turning_features else 1,
                "description": f"OP{20 if turning_features else 10} Frézování - detaily",
                "features": milling_features,
                "fixture": "vise",
                "estimated_setup_time": self.SETUP_TIMES["vise"],
                "machine_type": "mill_3ax",
                "notes": f"{len(milling_features)} milling operations"
            })

        return setups

    def get_total_setup_time(self, setups: List[Dict[str, Any]]) -> float:
        """
        Calculate total setup time for all setups.

        Args:
            setups: List of setup dicts from plan_setups()

        Returns:
            Total setup time in minutes
        """
        return sum(s.get("estimated_setup_time", 0.0) for s in setups)


# Singleton
setup_planner = SetupPlanner()


def plan_setups_for_geometry(geometry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convenience function for planning setups.

    Args:
        geometry: Full geometry dict from Claude extraction

    Returns:
        List of setup dicts with setup_id, description, features, fixture, time, machine_type
    """
    return setup_planner.plan_setups(geometry)


def get_setup_count(geometry: Dict[str, Any]) -> int:
    """
    Get number of setups required for part.

    Args:
        geometry: Full geometry dict

    Returns:
        Number of setups (1-3 typical)
    """
    setups = setup_planner.plan_setups(geometry)
    return len(setups)


def get_total_setup_time(geometry: Dict[str, Any]) -> float:
    """
    Get total setup time for all setups.

    Args:
        geometry: Full geometry dict

    Returns:
        Total setup time in minutes
    """
    setups = setup_planner.plan_setups(geometry)
    return setup_planner.get_total_setup_time(setups)
