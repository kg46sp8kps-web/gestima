"""GESTIMA - Cenová kalkulace"""

import math
from typing import Dict, Any, List
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import StockShape


@dataclass
class MaterialCost:
    volume_mm3: float = 0
    weight_kg: float = 0
    price_per_kg: float = 0
    cost: float = 0
    density: float = 0  # kg/dm³ (pro snapshot)


@dataclass
class BatchPrices:
    quantity: int = 1
    material_cost: float = 0
    machining_cost: float = 0
    setup_cost: float = 0
    coop_cost: float = 0
    unit_cost: float = 0
    total_cost: float = 0


async def calculate_material_cost_from_part(part, db: AsyncSession) -> MaterialCost:
    """
    Výpočet ceny polotovaru z Part modelu (ADR-011: Material Hierarchy).

    Používá MaterialItem (geometrie + cena) a MaterialGroup (hustota).
    Toto je PREFEROVANÁ metoda - používat místo calculate_material_cost().

    Args:
        part: Part instance (s eager-loaded material_item.group)
        db: AsyncSession (pro lazy loading pokud potřeba)

    Returns:
        MaterialCost: volume, weight, price_per_kg, cost
    """
    result = MaterialCost()

    # Načíst material_item pokud není eager loaded
    if not hasattr(part, 'material_item') or not part.material_item:
        from sqlalchemy import select
        from app.models.part import Part
        stmt = select(Part).where(Part.id == part.id).options(
            selectinload(Part.material_item).selectinload('group')
        )
        loaded_part = await db.execute(stmt)
        part = loaded_part.scalar_one()

    item = part.material_item
    group = item.group

    if not item or not group:
        return result

    # Výpočet objemu podle tvaru polotovaru
    volume_mm3 = 0

    if item.shape == StockShape.ROUND_BAR:
        # Tyč kruhová: π × r² × délka
        if item.diameter and part.length > 0:
            r = item.diameter / 2
            volume_mm3 = math.pi * r**2 * part.length

    elif item.shape == StockShape.SQUARE_BAR:
        # Tyč čtvercová: a² × délka
        if item.width and part.length > 0:
            volume_mm3 = item.width**2 * part.length

    elif item.shape == StockShape.FLAT_BAR:
        # Tyč plochá: šířka × tloušťka × délka
        if item.width and item.thickness and part.length > 0:
            volume_mm3 = item.width * item.thickness * part.length

    elif item.shape == StockShape.HEXAGONAL_BAR:
        # Tyč šestihranná: (3√3/2) × a² × délka
        if item.diameter and part.length > 0:  # diameter = rozměr přes plochy
            a = item.diameter / 2
            area = (3 * math.sqrt(3) / 2) * a**2
            volume_mm3 = area * part.length

    elif item.shape == StockShape.PLATE:
        # Plech: šířka × tloušťka × délka
        if item.width and item.thickness and part.length > 0:
            volume_mm3 = item.width * item.thickness * part.length

    elif item.shape == StockShape.TUBE:
        # Trubka: π × (r_outer² - r_inner²) × délka
        if item.diameter and item.wall_thickness and part.length > 0:
            r_outer = item.diameter / 2
            r_inner = r_outer - item.wall_thickness
            volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * part.length

    elif item.shape in [StockShape.CASTING, StockShape.FORGING]:
        # Odlitek/výkovek: aproximace jako kruhová tyč
        if item.diameter and part.length > 0:
            r = item.diameter / 2
            volume_mm3 = math.pi * r**2 * part.length

    else:
        return result

    # Převod na hmotnost a cenu
    volume_dm3 = volume_mm3 / 1_000_000  # mm³ → dm³
    weight_kg = volume_dm3 * group.density
    cost = weight_kg * item.price_per_kg  # LIVE cena z MaterialItem

    result.volume_mm3 = round(volume_mm3, 0)
    result.weight_kg = round(weight_kg, 3)
    result.price_per_kg = item.price_per_kg
    result.density = group.density
    result.cost = round(cost, 2)

    return result


async def calculate_material_cost(
    stock_diameter: float,
    stock_length: float,
    material_group: str,
    stock_diameter_inner: float = 0,
    stock_type: str = "tyc",
    stock_width: float = 0,
    stock_height: float = 0,
) -> MaterialCost:
    """
    DEPRECATED: Použij calculate_material_cost_from_part() místo této funkce.

    Výpočet ceny polotovaru podle typu (STARÝ přístup s hardcoded daty).
    - tyc: π × r² × délka
    - trubka: π × (r_outer² - r_inner²) × délka
    - prizez: délka × šířka × výška
    - plech: délka × šířka × tloušťka
    - odlitek: π × r² × délka (jako tyč)
    """
    from app.services.reference_loader import get_material_properties
    result = MaterialCost()
    
    props = await get_material_properties(material_group)
    density = props["density"]
    price_per_kg = props["price_per_kg"]
    
    volume_mm3 = 0
    
    if stock_type in ["tyc", "odlitek"]:
        # Plná tyč nebo odlitek
        if stock_diameter <= 0 or stock_length <= 0:
            return result
        r = stock_diameter / 2
        volume_mm3 = math.pi * r**2 * stock_length
        
    elif stock_type == "trubka":
        # Trubka (dutá)
        if stock_diameter <= 0 or stock_length <= 0:
            return result
        r_outer = stock_diameter / 2
        r_inner = stock_diameter_inner / 2 if stock_diameter_inner > 0 else 0
        volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length
        
    elif stock_type in ["prizez", "plech"]:
        # Přířez nebo plech (kvádr)
        if stock_length <= 0 or stock_width <= 0 or stock_height <= 0:
            return result
        volume_mm3 = stock_length * stock_width * stock_height
    
    else:
        return result
    
    # Převod na hmotnost a cenu
    volume_dm3 = volume_mm3 / 1_000_000
    weight_kg = volume_dm3 * density
    cost = weight_kg * price_per_kg
    
    result.volume_mm3 = round(volume_mm3, 0)
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
