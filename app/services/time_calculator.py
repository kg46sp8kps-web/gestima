"""GESTIMA - Výpočet strojních časů"""

import math
from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.services.cutting_conditions import get_conditions

# Default values when cutting conditions are not found
DEFAULT_MAX_RPM = 4000
DEFAULT_VC = 150  # m/min - conservative cutting speed
DEFAULT_FEED = 0.2  # mm/rev
DEFAULT_AP = 2.0  # mm - depth of cut


@dataclass
class CalculationResult:
    Vc: float = 0
    f: float = 0
    Ap: float = 0
    rpm: int = 0
    num_passes: int = 1
    cutting_time_sec: float = 0
    total_time_sec: float = 0


class FeatureCalculator:
    def __init__(self, max_rpm: int = DEFAULT_MAX_RPM):
        self.max_rpm = max_rpm
    
    def calc_rpm(self, Vc: float, diameter: float) -> float:
        if diameter <= 0:
            return 0
        rpm = (1000 * Vc) / (math.pi * diameter)
        return min(rpm, self.max_rpm)
    
    def calc_time(self, length: float, rpm: float, feed: float) -> float:
        if rpm <= 0 or feed <= 0:
            return 0
        return (length / (rpm * feed)) * 60
    
    async def calculate(
        self,
        feature_type: str,
        material_group: str,
        cutting_mode: str,
        geometry: Dict[str, Any],
        locked_values: Optional[Dict[str, float]] = None,
    ) -> CalculationResult:
        result = CalculationResult()
        locked = locked_values or {}
        
        conditions = await get_conditions(
            feature_type,
            material_group,
            cutting_mode,
            diameter=geometry.get("to_diameter"),
        )
        
        Vc = locked.get("Vc") or conditions.get("Vc") or DEFAULT_VC
        f = locked.get("f") or conditions.get("f") or DEFAULT_FEED
        Ap = locked.get("Ap") or conditions.get("Ap") or DEFAULT_AP
        
        result.Vc = Vc
        result.f = f
        result.Ap = Ap
        
        method_name = f"_calc_{feature_type}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            result = method(result, geometry)
        else:
            result = self._calc_generic(result, geometry)
        
        return result
    
    def _calc_generic(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        diameter = geo.get("from_diameter") or geo.get("to_diameter") or 50
        length = geo.get("length") or 50
        
        result.rpm = int(self.calc_rpm(result.Vc, diameter))
        result.num_passes = 1
        result.cutting_time_sec = self.calc_time(length, result.rpm, result.f)
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_od_rough(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        from_d = geo.get("from_diameter") or 50
        to_d = geo.get("to_diameter") or 45
        length = geo.get("length") or 50
        
        allowance = (from_d - to_d) / 2
        result.num_passes = max(1, math.ceil(allowance / result.Ap)) if result.Ap else 1
        
        avg_dia = (from_d + to_d) / 2
        result.rpm = int(self.calc_rpm(result.Vc, avg_dia))
        
        result.cutting_time_sec = self.calc_time(length + 2, result.rpm, result.f) * result.num_passes
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_od_finish(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        return self._calc_od_rough(result, geo)
    
    def _calc_id_rough(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        result = self._calc_od_rough(result, geo)
        result.cutting_time_sec *= 1.2
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_id_finish(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        return self._calc_id_rough(result, geo)
    
    def _calc_face(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        diameter = geo.get("from_diameter") or 50
        depth = geo.get("depth") or 1
        
        result.num_passes = max(1, math.ceil(depth / result.Ap)) if result.Ap else 1
        avg_dia = diameter / 2
        result.rpm = int(self.calc_rpm(result.Vc, avg_dia))
        
        result.cutting_time_sec = self.calc_time(diameter / 2, result.rpm, result.f) * result.num_passes
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_drill(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        diameter = geo.get("to_diameter") or 10
        depth = geo.get("depth") or geo.get("length") or 30
        
        result.rpm = int(self.calc_rpm(result.Vc, diameter))
        
        if depth > 3 * diameter:
            num_cycles = max(1, math.ceil(depth / (2 * diameter)))
            result.num_passes = num_cycles
            result.cutting_time_sec = self.calc_time(depth, result.rpm, result.f) * num_cycles * 0.7
        else:
            result.num_passes = 1
            result.cutting_time_sec = self.calc_time(depth, result.rpm, result.f)
        
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_drill_deep(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        return self._calc_drill(result, geo)
    
    def _calc_parting(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        diameter = geo.get("from_diameter") or 40
        
        avg_dia = diameter / 2
        result.rpm = int(self.calc_rpm(result.Vc, avg_dia))
        result.num_passes = 1
        
        if result.rpm > 0:
            result.cutting_time_sec = (diameter / 2) / (result.rpm * result.f) * 60
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_thread_od(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        diameter = geo.get("to_diameter") or geo.get("from_diameter") or 20
        length = geo.get("length") or 20
        pitch = geo.get("thread_pitch") or 1.5
        
        result.rpm = int(self.calc_rpm(result.Vc, diameter))
        result.f = pitch
        result.num_passes = 6
        
        result.cutting_time_sec = self.calc_time(length, result.rpm, pitch) * result.num_passes * 2
        result.total_time_sec = result.cutting_time_sec
        return result
    
    def _calc_thread_id(self, result: CalculationResult, geo: Dict) -> CalculationResult:
        return self._calc_thread_od(result, geo)


async def calculate_feature_time(
    feature_type: str,
    material_group: str,
    cutting_mode: str,
    geometry: Dict[str, Any],
    locked_values: Optional[Dict[str, float]] = None,
    max_rpm: int = DEFAULT_MAX_RPM,
) -> CalculationResult:
    calc = FeatureCalculator(max_rpm=max_rpm)
    return await calc.calculate(feature_type, material_group, cutting_mode, geometry, locked_values)
