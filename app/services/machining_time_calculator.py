"""Machining Time Calculator - computes times from Vision operations + cutting conditions catalog

This service takes operations extracted by AI Vision and calculates actual machining times
using the cutting conditions catalog based on material and operation type.
"""

import logging
from typing import Dict, List, Any, Literal
import math

logger = logging.getLogger(__name__)

# Import cutting conditions catalog
from app.services.cutting_conditions_catalog import (
    MATERIAL_GROUP_MAP,
    WERKSTOFF_PREFIX_MAP
)


class MachiningTimeCalculator:
    """Calculate machining times from Vision operations using cutting conditions catalog"""

    def __init__(self):
        self.speed_mode = "mid"  # low, mid, high

    def calculate_times(
        self,
        operations: List[Dict[str, Any]],
        material_code: str,
        speed_mode: Literal["low", "mid", "high"] = "mid"
    ) -> Dict[str, Any]:
        """
        Calculate machining times for all operations

        Args:
            operations: List of operations from Vision API (with geometric params)
            material_code: Material code (W.Nr like "1.4305")
            speed_mode: Cutting speed mode (low=conservative, mid=standard, high=aggressive)

        Returns:
            dict with:
                - machining_time_min: total machining time
                - setup_time_min: setup time estimate
                - inspection_time_min: inspection time estimate
                - total_time_min: total time
                - operations: operations with calculated times
        """
        self.speed_mode = speed_mode

        # Map material code to material group
        material_group = self._get_material_group(material_code)
        material_info = MATERIAL_GROUP_MAP.get(material_group, {})

        calculated_ops = []
        total_machining_time = 0.0

        for op in operations:
            op_type = op.get("type", "")

            # Calculate time based on operation type
            if op_type == "roughing_turn":
                time_data = self._calc_roughing_turn(op, material_info)
            elif op_type == "finishing_turn":
                time_data = self._calc_finishing_turn(op, material_info)
            elif op_type == "drilling":
                time_data = self._calc_drilling(op, material_info)
            elif op_type == "boring":
                time_data = self._calc_boring(op, material_info)
            elif op_type == "threading":
                time_data = self._calc_threading(op, material_info)
            elif op_type == "chamfering":
                time_data = self._calc_chamfering(op, material_info)
            elif op_type == "face_mill":
                time_data = self._calc_face_milling(op, material_info)
            elif op_type == "slot_mill":
                time_data = self._calc_slot_milling(op, material_info)
            elif op_type == "pocket_mill":
                time_data = self._calc_pocket_milling(op, material_info)
            else:
                # Unknown operation - estimate conservatively
                time_data = {"main_time_min": 1.0, "auxiliary_time_min": 0.3}

            # Merge operation with calculated times
            calc_op = {**op, **time_data}
            calculated_ops.append(calc_op)

            # Sum total machining time
            total_machining_time += time_data["main_time_min"] + time_data["auxiliary_time_min"]

        # Estimate setup and inspection times
        setup_time = self._estimate_setup_time(len(calculated_ops))
        inspection_time = self._estimate_inspection_time(operations)

        return {
            "machining_time_min": round(total_machining_time, 2),
            "setup_time_min": round(setup_time, 2),
            "inspection_time_min": round(inspection_time, 2),
            "total_time_min": round(total_machining_time + setup_time + inspection_time, 2),
            "operations": calculated_ops
        }

    def _get_material_group(self, material_code: str) -> str:
        """Map material code to internal material group"""
        # Try W.Nr prefix match (e.g., "1.4305" → "1.43" → Nerez)
        for prefix, group_code in WERKSTOFF_PREFIX_MAP.items():
            if material_code.startswith(prefix):
                return group_code

        # Default to carbon steel
        return "20910004"

    def _get_cutting_speed(self, material_info: Dict, operation_mode: str) -> float:
        """Get cutting speed Vc (m/min) based on material and operation"""
        iso_group = material_info.get("iso", "P")

        # Base speeds by ISO group and mode
        speed_table = {
            "P": {"roughing": 200, "finishing": 250},  # Carbon steel
            "M": {"roughing": 100, "finishing": 140},  # Stainless
            "H": {"roughing": 80, "finishing": 120},   # Tool steel
            "K": {"roughing": 150, "finishing": 200},  # Cast iron
            "N": {"roughing": 400, "finishing": 500},  # Aluminum
        }

        base_speed = speed_table.get(iso_group, {}).get(operation_mode, 200)

        # Apply speed mode multiplier
        multipliers = {"low": 0.8, "mid": 1.0, "high": 1.2}
        return base_speed * multipliers.get(self.speed_mode, 1.0)

    def _calc_roughing_turn(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for roughing turning operation"""
        D_avg = (op.get("diameter_start", 20) + op.get("diameter_end", 15)) / 2
        L = op.get("length", 10)
        passes = op.get("passes", 1)

        Vc = self._get_cutting_speed(material_info, "roughing")
        f = 0.4  # mm/rev (roughing feed)

        n = (1000 * Vc) / (math.pi * D_avg)  # rpm
        Tc = (L * passes) / (f * n)  # min

        main_time = Tc
        aux_time = Tc * 0.25  # 25% auxiliary

        return {
            "main_time_min": round(main_time, 2),
            "auxiliary_time_min": round(aux_time, 2),
            "cutting_params": f"Vc={int(Vc)} m/min, f={f} mm/rev, n={int(n)} rpm"
        }

    def _calc_finishing_turn(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for finishing turning operation"""
        D = op.get("diameter_end", 15)
        L = op.get("length", 10)

        Vc = self._get_cutting_speed(material_info, "finishing")
        f = 0.15  # mm/rev (finishing feed)

        n = (1000 * Vc) / (math.pi * D)
        Tc = L / (f * n)

        main_time = Tc
        aux_time = Tc * 0.2  # 20% auxiliary

        return {
            "main_time_min": round(main_time, 2),
            "auxiliary_time_min": round(aux_time, 2),
            "cutting_params": f"Vc={int(Vc)} m/min, f={f} mm/rev, n={int(n)} rpm"
        }

    def _calc_drilling(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for drilling operation"""
        D = op.get("diameter", 6)
        depth = op.get("depth", 10)

        Vc = self._get_cutting_speed(material_info, "roughing") * 0.7  # Drilling is slower
        f = 0.15  # mm/rev

        n = (1000 * Vc) / (math.pi * D)
        Tc = depth / (f * n)

        main_time = Tc
        aux_time = 0.2  # Fixed auxiliary for drilling

        return {
            "main_time_min": round(main_time, 2),
            "auxiliary_time_min": round(aux_time, 2),
            "cutting_params": f"Vc={int(Vc)} m/min, f={f} mm/rev, n={int(n)} rpm"
        }

    def _calc_boring(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for boring operation"""
        # Similar to finishing turn
        return self._calc_finishing_turn(op, material_info)

    def _calc_threading(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for threading operation"""
        L = op.get("length", 10)
        pitch = op.get("pitch", 1.5)
        passes = op.get("passes", 3)

        # Threading is slow (feed = pitch)
        Vc = 30  # Very slow for threading
        D = op.get("diameter", 10)
        n = (1000 * Vc) / (math.pi * D)

        Tc = (L * passes) / (pitch * n)

        return {
            "main_time_min": round(Tc, 2),
            "auxiliary_time_min": 0.5,
            "cutting_params": f"Vc={int(Vc)} m/min, pitch={pitch} mm"
        }

    def _calc_chamfering(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for chamfering"""
        count = op.get("count", 1)
        size = op.get("size", 0.5)

        # Chamfering is quick
        time_per_chamfer = 0.1 + (size / 5.0)  # Bigger chamfers take longer
        main_time = time_per_chamfer * count

        return {
            "main_time_min": round(main_time, 2),
            "auxiliary_time_min": 0.1,
            "cutting_params": f"{count}× chamfer {size}mm"
        }

    def _calc_face_milling(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for face milling"""
        area = op.get("area", 1000)  # mm²
        tool_diameter = op.get("tool_diameter", 50)

        Vc = self._get_cutting_speed(material_info, "finishing")
        fz = 0.12  # mm/tooth
        z = 4  # number of teeth

        n = (1000 * Vc) / (math.pi * tool_diameter)
        vf = fz * z * n  # mm/min feed rate

        # Estimate cutting length (rectangular area coverage)
        cutting_length = area / tool_diameter * 1.2  # 20% overlap

        Tc = cutting_length / vf

        return {
            "main_time_min": round(Tc, 2),
            "auxiliary_time_min": round(Tc * 0.3, 2),
            "cutting_params": f"Vc={int(Vc)} m/min, fz={fz} mm/tooth"
        }

    def _calc_slot_milling(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for slot milling"""
        length = op.get("length", 20)
        width = op.get("width", 10)
        depth = op.get("depth", 5)
        tool_diameter = op.get("tool_diameter", width * 0.8)

        Vc = self._get_cutting_speed(material_info, "roughing") * 0.7
        fz = 0.1
        z = 2

        n = (1000 * Vc) / (math.pi * tool_diameter)
        vf = fz * z * n

        # Multiple depth passes
        depth_per_pass = 2.0
        passes = math.ceil(depth / depth_per_pass)

        Tc = (length * passes) / vf

        return {
            "main_time_min": round(Tc, 2),
            "auxiliary_time_min": round(Tc * 0.4, 2),
            "cutting_params": f"Vc={int(Vc)} m/min, {passes} depth passes"
        }

    def _calc_pocket_milling(self, op: Dict, material_info: Dict) -> Dict:
        """Calculate time for pocket milling"""
        # Similar to slot but with spiral toolpath
        result = self._calc_slot_milling(op, material_info)
        # Pockets take ~40% longer due to complex toolpath
        result["main_time_min"] *= 1.4
        result["auxiliary_time_min"] *= 1.4
        return result

    def _estimate_setup_time(self, num_operations: int) -> float:
        """Estimate setup time based on complexity"""
        if num_operations <= 3:
            return 1.5
        elif num_operations <= 6:
            return 2.5
        else:
            return 3.5

    def _estimate_inspection_time(self, operations: List[Dict]) -> float:
        """Estimate inspection time based on tolerances"""
        # Check if there are tight tolerances
        has_tight_tolerance = any(
            op.get("tolerance") and "±0.1" in str(op.get("tolerance"))
            for op in operations
        )

        if has_tight_tolerance:
            return 1.5
        else:
            return 1.0
