"""GESTIMA - Machine Selector Service

Selects optimal machine type based on geometry analysis and cost calculation.

Machine types:
- lathe_3ax: Basic turning (2 axes + spindle)
- lathe_4ax: Turning + live tooling (Y-axis milling for radial features)
- mill_3ax: 3-axis milling (standard)
- mill_4ax: 4-axis milling (rotary table)
- mill_5ax: 5-axis milling (complex geometries, multi-angle access)

Decision logic:
1. Rotational parts → Lathe preferred
   - Radial features (holes, flats) → 4ax lathe (live tooling saves setup)
   - Basic turning only → 3ax lathe (cheaper)

2. Prismatic parts → Mill
   - Complex 3D surfaces → 5ax mill (required)
   - Simple 2.5D → Compare 3ax vs 5ax on cost (5ax may save setups)

Cost calculation:
- Setup time (from setup_planner)
- Machining time (from features)
- Hourly rate (machine-specific)
- Total = (setup_time + machining_time) * hourly_rate

Design: Data-driven, deterministic (same input → same output)
Pattern: Calculate all feasible options → recommend lowest cost option
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MachineSelector:
    """
    Select optimal machine type based on geometry and cost.

    Deterministic: Same geometry + setups → always same machine recommendation
    Cost-driven: Considers setup time, machining time, and hourly rates
    """

    # Hourly rates [€/hour] - customize per shop
    # TODO: Eventually load from database (WorkCenter model)
    MACHINE_RATES = {
        "lathe_3ax": 50.0,   # Basic CNC lathe
        "lathe_4ax": 70.0,   # Lathe with live tooling (Y-axis)
        "mill_3ax": 60.0,    # Standard 3-axis mill
        "mill_4ax": 80.0,    # 4-axis mill (rotary table)
        "mill_5ax": 120.0,   # 5-axis mill (expensive!)
    }

    # Cost calculation constants
    SETUP_REDUCTION_5AX = 0.7  # 5-axis reduces setup count to 70% of 3-axis
    COST_PREMIUM_THRESHOLD = 1.2  # Accept 5-axis if within 20% cost premium
    EXTRA_MILLING_SETUP_MIN = 30.0  # Extra setup time if lathe can't do radial features

    def select_machine(
        self,
        geometry: Dict[str, Any],
        setups: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select best machine based on cost and capability.

        Args:
            geometry: Full geometry dict (part_type, profile_geometry, features)
            setups: List of setup dicts from setup_planner (each with features, setup_time)

        Returns:
            {
                "recommended_machine": "lathe_4ax",
                "reasoning": "Radial holes → live tooling saves setup time",
                "alternatives": [
                    {"machine": "lathe_3ax", "cost": 120.50, "time": 90, "setups": 2},
                    {"machine": "lathe_4ax", "cost": 130.20, "time": 70, "setups": 1},
                ]
            }
        """
        if not geometry:
            raise ValueError("geometry parameter is required")
        if not setups:
            raise ValueError("setups parameter is required (empty list = no operations)")

        part_type = geometry.get("part_type", "rotational")
        profile_geometry = geometry.get("profile_geometry", {})
        features = profile_geometry.get("features", [])

        # Analyze feature complexity
        has_radial_features = any(
            f.get("type") in ["lt_drill", "lt_flat", "radial_hole"]
            for f in features
        )
        has_complex_3d = any(
            f.get("type") in ["mill_3d", "sphere", "freeform_surface"]
            for f in features
        )

        # Decision tree based on part type
        if part_type == "rotational":
            return self._select_for_rotational(
                has_radial_features, setups
            )
        elif part_type == "prismatic":
            return self._select_for_prismatic(
                has_complex_3d, setups
            )
        else:
            # Mixed or unknown → default to milling
            logger.warning(f"Unknown part_type '{part_type}', defaulting to mill_3ax")
            return {
                "recommended_machine": "mill_3ax",
                "reasoning": f"Unknown part type '{part_type}', using standard mill",
                "alternatives": []
            }

    def _select_for_rotational(
        self,
        has_radial_features: bool,
        setups: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select machine for rotational parts (lathe-based)."""

        if has_radial_features:
            # Compare 3ax lathe (with extra milling setup) vs 4ax lathe (live tooling)
            cost_3ax = self._calc_cost("lathe_3ax", setups, extra_setup=True)
            cost_4ax = self._calc_cost("lathe_4ax", setups, extra_setup=False)

            if cost_4ax["total_cost"] < cost_3ax["total_cost"]:
                return {
                    "recommended_machine": "lathe_4ax",
                    "reasoning": "Radial features → live tooling eliminates separate milling setup",
                    "alternatives": [cost_3ax, cost_4ax]
                }
            else:
                return {
                    "recommended_machine": "lathe_3ax",
                    "reasoning": "3-axis lathe + milling setup cheaper than 4-axis live tooling",
                    "alternatives": [cost_3ax, cost_4ax]
                }
        else:
            # Basic turning only → standard lathe
            cost_3ax = self._calc_cost("lathe_3ax", setups, extra_setup=False)
            return {
                "recommended_machine": "lathe_3ax",
                "reasoning": "Basic turning only → standard 3-axis lathe",
                "alternatives": [cost_3ax]
            }

    def _select_for_prismatic(
        self,
        has_complex_3d: bool,
        setups: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select machine for prismatic parts (mill-based)."""

        if has_complex_3d:
            # Complex 3D surfaces require 5-axis
            cost_5ax = self._calc_cost("mill_5ax", setups, extra_setup=False)
            return {
                "recommended_machine": "mill_5ax",
                "reasoning": "Complex 3D surfaces → 5-axis required for tool access",
                "alternatives": [cost_5ax]
            }
        else:
            # Simple 2.5D → compare 3ax vs 5ax on cost
            # (5ax may save setups despite higher hourly rate)
            cost_3ax = self._calc_cost("mill_3ax", setups, extra_setup=False)

            # Estimate 5ax with fewer setups
            setups_5ax = max(1, int(len(setups) * self.SETUP_REDUCTION_5AX))
            cost_5ax = self._calc_cost(
                "mill_5ax",
                setups[:setups_5ax],  # Use subset of setups
                extra_setup=False
            )

            # Recommend 5ax if cost-effective (within premium threshold)
            if cost_5ax["total_cost"] < cost_3ax["total_cost"] * self.COST_PREMIUM_THRESHOLD:
                return {
                    "recommended_machine": "mill_5ax",
                    "reasoning": "5-axis saves setup time, cost-effective (within 20% premium)",
                    "alternatives": [cost_3ax, cost_5ax]
                }
            else:
                return {
                    "recommended_machine": "mill_3ax",
                    "reasoning": "3-axis cheaper despite multiple setups",
                    "alternatives": [cost_3ax, cost_5ax]
                }

    def _calc_cost(
        self,
        machine_type: str,
        setups: List[Dict[str, Any]],
        extra_setup: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate total cost for machine option.

        Args:
            machine_type: Machine type key (e.g., "lathe_3ax")
            setups: List of setup dicts (each with estimated_setup_time, features)
            extra_setup: Add extra milling setup time (for 3ax lathe with radial features)

        Returns:
            {
                "machine": "lathe_3ax",
                "setup_count": 2,
                "setup_time_min": 50.0,
                "machining_time_min": 35.0,
                "total_time_min": 85.0,
                "hourly_rate": 50.0,
                "total_cost": 70.83
            }
        """
        rate = self.MACHINE_RATES.get(machine_type, 60.0)

        # Calculate setup time
        setup_time = sum(s.get("estimated_setup_time", 25.0) for s in setups)

        if extra_setup:
            # Extra milling setup if lathe can't do radial features
            setup_time += self.EXTRA_MILLING_SETUP_MIN

        # Calculate machining time from features
        machining_time = 0.0
        for setup in setups:
            features = setup.get("features", [])
            for feature in features:
                machining_time += feature.get("estimated_time", 0.0)

        total_time = setup_time + machining_time

        return {
            "machine": machine_type,
            "setup_count": len(setups) + (1 if extra_setup else 0),
            "setup_time_min": round(setup_time, 1),
            "machining_time_min": round(machining_time, 1),
            "total_time_min": round(total_time, 1),
            "hourly_rate": rate,
            "total_cost": round((total_time / 60.0) * rate, 2)
        }


# Singleton instance
machine_selector = MachineSelector()
