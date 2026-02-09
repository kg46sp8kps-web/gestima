"""Hybrid Time Estimator - Combines OCCT volumetry + AI Vision features

This service merges:
- OCCT: part_volume, stock_volume, surface_area (geometry metrics)
- Vision: material, features, tolerances, surface finishes (semantic data)

Time calculation:
1. Base time = removal_volume / MRR (material-dependent)
2. Feature time = threading + grooves + chamfers (Vision-detected)
3. Penalties = tight_tolerance + surface_finish (Vision × OCCT)
4. Total = base + features + setup + inspection
"""

import logging
import math
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Import material machinability (MRR catalog)
from app.services.cutting_conditions_catalog import MATERIAL_GROUP_MAP, WERKSTOFF_PREFIX_MAP


class HybridTimeEstimator:
    """Hybrid time estimation combining OCCT geometry + Vision features"""

    # Material Removal Rates (mm³/min) by ISO material group
    MRR_CATALOG = {
        "P": {"ROT": 40000, "PRI": 35000},  # Carbon steel (ISO P)
        "M": {"ROT": 25000, "PRI": 22000},  # Stainless (ISO M)
        "H": {"ROT": 15000, "PRI": 12000},  # Tool steel (ISO H)
        "K": {"ROT": 30000, "PRI": 28000},  # Cast iron (ISO K)
        "N": {"ROT": 80000, "PRI": 70000},  # Aluminum (ISO N)
    }

    # Feature time coefficients
    THREAD_TIME_PER_MM = {
        "M6": 0.04, "M8": 0.05, "M10": 0.06, "M12": 0.08, "M16": 0.10
    }

    TOLERANCE_MULTIPLIERS = {
        "h6": 0.25, "h7": 0.15, "h8": 0.10,
        "H6": 0.25, "H7": 0.15, "H8": 0.10,
        "±0.01": 0.30, "±0.02": 0.20, "±0.05": 0.10, "±0.1": 0.05
    }

    RA_PENALTIES = {
        "Ra 0.8": 0.50, "Ra 1.6": 0.30, "Ra 3.2": 0.15, "Ra 6.3": 0.05
    }

    def estimate(
        self,
        occt_data: Dict[str, Any],
        vision_data: Dict[str, Any],
        material_code: str,
        speed_mode: str = "mid"
    ) -> Dict[str, Any]:
        """
        Calculate machining time using hybrid approach

        Args:
            occt_data: OCCT geometry metrics (volume, surface_area, etc.)
            vision_data: Vision-extracted features (operations, tolerances, finishes)
            material_code: Material W.Nr code (e.g., "1.4305")
            speed_mode: "low", "mid", "high" (affects MRR multiplier)

        Returns:
            dict with base_time, feature_time, penalties, total_time
        """
        logger.info(f"Hybrid estimation: material={material_code}, mode={speed_mode}")

        # ═══════════════════════════════════════════════════
        # 1. BASE TIME (Volume-based MRR)
        # ═══════════════════════════════════════════════════
        removal_volume = occt_data.get("removal_volume_mm3", 0)
        part_type = vision_data.get("part_type", "ROT")

        mrr = self._get_mrr(material_code, part_type, speed_mode)

        if mrr == 0 or removal_volume == 0:
            logger.warning("MRR or removal volume is 0, using fallback time")
            base_time = 5.0  # Fallback
        else:
            base_time = removal_volume / mrr

        logger.info(f"Base time: {base_time:.2f} min (volume={removal_volume}, MRR={mrr})")

        # ═══════════════════════════════════════════════════
        # 2. FEATURE TIME ADDITIONS (Vision features)
        # ═══════════════════════════════════════════════════
        feature_breakdown = {}
        feature_time = 0

        # Threading
        for op in vision_data.get("operations", []):
            if op.get("type") == "threading":
                thread_time = self._calc_threading_time(op)
                feature_time += thread_time
                feature_breakdown.setdefault("threading", 0)
                feature_breakdown["threading"] += thread_time

        # Grooves
        for op in vision_data.get("operations", []):
            if "groove" in op.get("type", "").lower():
                groove_time = self._calc_groove_time(op)
                feature_time += groove_time
                feature_breakdown.setdefault("grooves", 0)
                feature_breakdown["grooves"] += groove_time

        # Chamfers (quick operation)
        for op in vision_data.get("operations", []):
            if op.get("type") == "chamfering":
                chamfer_time = 0.1 * op.get("count", 1)
                feature_time += chamfer_time
                feature_breakdown.setdefault("chamfers", 0)
                feature_breakdown["chamfers"] += chamfer_time

        logger.info(f"Feature time: {feature_time:.2f} min, breakdown={feature_breakdown}")

        # ═══════════════════════════════════════════════════
        # 3. PENALTIES (Vision × OCCT)
        # ═══════════════════════════════════════════════════
        penalty_breakdown = {}
        penalty_time = 0

        # Tight tolerance penalty
        tolerance_penalty = self._calc_tolerance_penalty(vision_data, base_time)
        penalty_time += tolerance_penalty
        if tolerance_penalty > 0:
            penalty_breakdown["tight_tolerance"] = tolerance_penalty

        # Surface finish penalty
        finish_penalty = self._calc_finish_penalty(vision_data, occt_data)
        penalty_time += finish_penalty
        if finish_penalty > 0:
            penalty_breakdown["surface_finish"] = finish_penalty

        logger.info(f"Penalty time: {penalty_time:.2f} min, breakdown={penalty_breakdown}")

        # ═══════════════════════════════════════════════════
        # 4. SETUP & INSPECTION
        # ═══════════════════════════════════════════════════
        num_operations = len(vision_data.get("operations", []))
        setup_time = self._estimate_setup_time(num_operations)
        inspection_time = self._estimate_inspection_time(vision_data)

        # ═══════════════════════════════════════════════════
        # 5. TOTAL TIME
        # ═══════════════════════════════════════════════════
        machining_time = base_time + feature_time + penalty_time
        total_time = machining_time + setup_time + inspection_time

        return {
            "base_time_min": round(base_time, 2),
            "feature_time_min": round(feature_time, 2),
            "penalty_time_min": round(penalty_time, 2),
            "machining_time_min": round(machining_time, 2),
            "setup_time_min": round(setup_time, 2),
            "inspection_time_min": round(inspection_time, 2),
            "total_time_min": round(total_time, 2),
            "breakdown": {
                **feature_breakdown,
                **penalty_breakdown,
                "volume_removal": round(base_time, 2),
                "setup": round(setup_time, 2),
                "inspection": round(inspection_time, 2)
            },
            "method": "hybrid_occt_vision",
            "mrr_mm3_per_min": mrr
        }

    def _get_mrr(self, material_code: str, part_type: str, speed_mode: str) -> float:
        """Get Material Removal Rate (mm³/min)"""
        # Map material code to ISO group
        material_group = self._get_material_group(material_code)
        iso_group = MATERIAL_GROUP_MAP.get(material_group, {}).get("iso", "P")

        # Get base MRR
        base_mrr = self.MRR_CATALOG.get(iso_group, {}).get(part_type, 30000)

        # Apply speed mode multiplier
        multipliers = {"low": 0.8, "mid": 1.0, "high": 1.2}
        mrr = base_mrr * multipliers.get(speed_mode, 1.0)

        return mrr

    def _get_material_group(self, material_code: str) -> str:
        """Map material code to internal material group"""
        for prefix, group_code in WERKSTOFF_PREFIX_MAP.items():
            if material_code.startswith(prefix):
                return group_code
        return "20910004"  # Default = carbon steel

    def _calc_threading_time(self, operation: Dict) -> float:
        """Calculate threading time from operation"""
        thread_spec = operation.get("thread_spec", "")
        length = operation.get("length", 15)

        # Parse "M8×1.25" → "M8"
        match = re.match(r"(M\d+)", thread_spec)
        if not match:
            return 1.0  # Fallback

        thread_type = match.group(1)
        time_per_mm = self.THREAD_TIME_PER_MM.get(thread_type, 0.05)

        return time_per_mm * length

    def _calc_groove_time(self, operation: Dict) -> float:
        """Calculate groove machining time"""
        width = operation.get("width", 2.0)
        depth = operation.get("depth", 1.0)

        # Groove time depends on width × depth (area to remove)
        volume_factor = (width * depth) / 10  # Normalize
        base_groove_time = 0.3  # min

        return base_groove_time + (volume_factor * 0.05)

    def _calc_tolerance_penalty(self, vision_data: Dict, base_time: float) -> float:
        """Calculate tight tolerance penalty"""
        penalty = 0

        for op in vision_data.get("operations", []):
            tolerance = op.get("tolerance")
            if tolerance:
                multiplier = self.TOLERANCE_MULTIPLIERS.get(tolerance, 0)
                penalty += base_time * multiplier

        return penalty

    def _calc_finish_penalty(self, vision_data: Dict, occt_data: Dict) -> float:
        """Calculate surface finish penalty"""
        surface_area = occt_data.get("surface_area_mm2", 10000)
        penalty = 0

        for op in vision_data.get("operations", []):
            finish = op.get("surface_finish")
            if finish:
                penalty_factor = self.RA_PENALTIES.get(finish, 0.10)
                # Surface area factor (larger area = more time)
                surface_factor = surface_area / 10000  # Normalize
                penalty += surface_factor * penalty_factor

        return penalty

    def _estimate_setup_time(self, num_operations: int) -> float:
        """Estimate setup time based on complexity"""
        if num_operations <= 3:
            return 1.5
        elif num_operations <= 6:
            return 2.5
        else:
            return 3.5

    def _estimate_inspection_time(self, vision_data: Dict) -> float:
        """Estimate inspection time based on tolerances"""
        # Check if there are tight tolerances
        has_tight_tolerance = any(
            op.get("tolerance") in ["h6", "H6", "±0.01", "±0.02"]
            for op in vision_data.get("operations", [])
        )

        return 1.5 if has_tight_tolerance else 1.0
