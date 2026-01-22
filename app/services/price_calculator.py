"""GESTIMA - Cenová kalkulace"""

import math
from typing import Dict, Any, List
from dataclasses import dataclass

from app.services.reference_loader import get_material_properties


@dataclass
class MaterialCost:
    volume_mm3: float = 0
    weight_kg: float = 0
    price_per_kg: float = 0
    cost: float = 0


@dataclass
class BatchPrices:
    quantity: int = 1
    material_cost: float = 0
    machining_cost: float = 0
    setup_cost: float = 0
    coop_cost: float = 0
    unit_cost: float = 0
    total_cost: float = 0


def calculate_material_cost(
    stock_diameter: float,
    stock_length: float,
    material_group: str,
    stock_diameter_inner: float = 0,
) -> MaterialCost:
    result = MaterialCost()
    
    if stock_diameter <= 0 or stock_length <= 0:
        return result
    
    props = get_material_properties(material_group)
    density = props["density"]
    price_per_kg = props["price_per_kg"]
    
    r_outer = stock_diameter / 2
    r_inner = stock_diameter_inner / 2 if stock_diameter_inner > 0 else 0
    
    volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length
    volume_dm3 = volume_mm3 / 1_000_000
    weight_kg = volume_dm3 * density
    cost = weight_kg * price_per_kg
    
    result.volume_mm3 = volume_mm3
    result.weight_kg = round(weight_kg, 3)
    result.price_per_kg = price_per_kg
    result.cost = round(cost, 2)
    
    return result


def calculate_machining_cost(operation_time_min: float, hourly_rate: float) -> float:
    return round((operation_time_min / 60) * hourly_rate, 2)


def calculate_setup_cost(setup_time_min: float, hourly_rate: float, quantity: int) -> float:
    total_setup = (setup_time_min / 60) * hourly_rate
    return round(total_setup / quantity, 2) if quantity > 0 else 0


def calculate_coop_cost(coop_price: float, coop_min_price: float, quantity: int) -> float:
    if coop_price <= 0:
        return 0
    
    raw_total = coop_price * quantity
    total = max(raw_total, coop_min_price)
    return round(total / quantity, 2)


def calculate_batch_prices(
    quantity: int,
    material_cost: float,
    operations: List[Dict[str, Any]],
    machines: Dict[int, Dict[str, Any]],
) -> BatchPrices:
    result = BatchPrices(quantity=quantity)
    result.material_cost = material_cost
    
    total_machining = 0
    total_setup = 0
    total_coop = 0
    
    for op in operations:
        if op.get("is_coop"):
            coop = calculate_coop_cost(
                op.get("coop_price", 0),
                op.get("coop_min_price", 0),
                quantity,
            )
            total_coop += coop
        else:
            machine_id = op.get("machine_id")
            machine = machines.get(machine_id, {})
            hourly_rate = machine.get("hourly_rate", 1000)
            
            machining = calculate_machining_cost(
                op.get("operation_time_min", 0),
                hourly_rate,
            )
            setup = calculate_setup_cost(
                op.get("setup_time_min", 0),
                hourly_rate,
                quantity,
            )
            
            total_machining += machining
            total_setup += setup
    
    result.machining_cost = round(total_machining, 2)
    result.setup_cost = round(total_setup, 2)
    result.coop_cost = round(total_coop, 2)
    
    result.unit_cost = round(
        result.material_cost +
        result.machining_cost +
        result.setup_cost +
        result.coop_cost,
        2
    )
    
    result.total_cost = round(result.unit_cost * quantity, 2)
    
    return result
