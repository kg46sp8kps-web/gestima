"""GESTIMA - Cenová kalkulace"""

import logging
import math
from typing import Dict, Any, List
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import StockShape

logger = logging.getLogger(__name__)


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

    # Percentages removed (CRITICAL-003 fix)
    # Use Pydantic computed fields in BatchResponse instead
    # (Single Source of Truth - L-002)


async def get_price_per_kg_for_weight(
    price_category,
    total_weight_kg: float,
    db: AsyncSession
) -> float:
    """
    Najde správný price tier podle celkové váhy (ADR-014).

    Pravidlo: Největší min_weight <= total_weight (nejbližší nižší tier).

    Args:
        price_category: MaterialPriceCategory instance
        total_weight_kg: Celková váha batch (weight_kg × quantity)
        db: AsyncSession (pro lazy loading tiers)

    Returns:
        float: price_per_kg pro vybraný tier

    Example:
        Tiers: [0-15: 49.4], [15-100: 34.5], [100+: 26.3]
        weight=5 → 49.4, weight=25 → 34.5, weight=150 → 26.3
    """
    # Načíst tiers pokud nejsou eager loaded (safe check to avoid lazy-load in async)
    from sqlalchemy.exc import MissingGreenlet

    try:
        # Try to access tiers - if not loaded, will raise MissingGreenlet in async context
        tiers = price_category.tiers if price_category else None
    except (MissingGreenlet, AttributeError):
        # Tiers not loaded, fetch them explicitly
        from app.models.material import MaterialPriceCategory
        from sqlalchemy import select

        stmt = select(MaterialPriceCategory).where(
            MaterialPriceCategory.id == price_category.id
        ).options(selectinload(MaterialPriceCategory.tiers))

        result = await db.execute(stmt)
        price_category = result.scalar_one_or_none()
        tiers = price_category.tiers if price_category else None

    if not price_category or not tiers:
        logger.error(
            f"No tiers found for price category {price_category.id if price_category else 'unknown'}"
        )
        return 0

    # Filtrovat tiers: min_weight <= total_weight
    valid_tiers = [
        tier for tier in tiers
        if tier.min_weight <= total_weight_kg
    ]

    if not valid_tiers:
        logger.error(
            f"No valid tier for weight {total_weight_kg}kg in category {price_category.code}. "
            f"Check tier configuration (should have tier with min_weight=0)."
        )
        return 0

    # Vybrat tier s největším min_weight (nejbližší nižší)
    selected_tier = max(valid_tiers, key=lambda t: t.min_weight)

    logger.debug(
        f"Selected tier for {total_weight_kg}kg: "
        f"[{selected_tier.min_weight}-{selected_tier.max_weight or '∞'}] → {selected_tier.price_per_kg} Kč/kg"
    )

    return selected_tier.price_per_kg


async def calculate_stock_cost_from_part(
    part,
    quantity: int = 1,
    db: AsyncSession = None
) -> MaterialCost:
    """
    Výpočet ceny polotovaru z Part.stock_* polí (ADR-014: Dynamic Price Tiers).
    Migration 2026-01-26: Podporuje Part.price_category + Part.stock_shape.

    Používá:
    - Part.stock_* pro geometrii (editovatelné uživatelem)
    - Part.stock_shape pro typ polotovaru (NOVÉ)
    - Part.price_category → price tier podle quantity (NOVÉ)
    - Part.price_category.material_group.density pro hustotu (NOVÉ)
    - Fallback: Part.material_item.* (staré)

    Args:
        part: Part instance (s eager-loaded price_category.material_group nebo material_item.group)
        quantity: Množství kusů (pro výběr správného price tier)
        db: AsyncSession (pro lazy loading pokud potřeba)

    Returns:
        MaterialCost: volume, weight, price_per_kg (pro snapshot), cost, density
    """
    result = MaterialCost()

    # Migration 2026-01-26: Priorita Part.price_category, fallback Part.material_item
    price_category = None
    material_group = None
    stock_shape = part.stock_shape

    if part.price_category:
        # Nové: Part → PriceCategory → MaterialGroup
        price_category = part.price_category
        material_group = price_category.material_group if price_category else None
    elif part.material_item:
        # Fallback: Part → MaterialItem → PriceCategory → MaterialGroup
        item = part.material_item
        price_category = item.price_category
        material_group = item.group
        if not stock_shape:
            stock_shape = item.shape  # Použij item.shape pokud Part nemá stock_shape

    if not price_category:
        logger.error(f"Part {part.id} has no price_category (neither direct nor via material_item)")
        return result

    if not material_group:
        logger.error(f"PriceCategory {price_category.id} has no material_group")
        return result

    if not stock_shape:
        logger.error(f"Part {part.id} has no stock_shape")
        return result

    if db is None:
        logger.error("DB session required for dynamic price tier selection")
        return result

    # Použij Part.stock_* pro geometrii
    stock_diameter = part.stock_diameter or 0
    stock_length = part.stock_length or 0
    stock_width = part.stock_width or 0
    stock_height = part.stock_height or 0
    stock_wall_thickness = part.stock_wall_thickness or 0

    # Výpočet objemu podle tvaru polotovaru (Migration 2026-01-26: stock_shape místo item.shape)
    volume_mm3 = 0

    if stock_shape == StockShape.ROUND_BAR:
        # Tyč kruhová: π × r² × délka
        if stock_diameter > 0 and stock_length > 0:
            r = stock_diameter / 2
            volume_mm3 = math.pi * r**2 * stock_length

    elif stock_shape == StockShape.SQUARE_BAR:
        # Tyč čtvercová: a² × délka
        if stock_width > 0 and stock_length > 0:
            volume_mm3 = stock_width**2 * stock_length

    elif stock_shape == StockShape.FLAT_BAR:
        # Tyč plochá: šířka × výška × délka
        if stock_width > 0 and stock_height > 0 and stock_length > 0:
            volume_mm3 = stock_width * stock_height * stock_length

    elif stock_shape == StockShape.HEXAGONAL_BAR:
        # Tyč šestihranná: (3√3/2) × a² × délka
        if stock_diameter > 0 and stock_length > 0:
            a = stock_diameter / 2
            area = (3 * math.sqrt(3) / 2) * a**2
            volume_mm3 = area * stock_length

    elif stock_shape == StockShape.PLATE:
        # Plech: šířka × výška × délka
        if stock_width > 0 and stock_height > 0 and stock_length > 0:
            volume_mm3 = stock_width * stock_height * stock_length

    elif stock_shape == StockShape.TUBE:
        # Trubka: π × (r_outer² - r_inner²) × délka
        if stock_diameter > 0 and stock_wall_thickness > 0 and stock_length > 0:
            r_outer = stock_diameter / 2
            r_inner = r_outer - stock_wall_thickness
            if r_inner <= 0:
                logger.warning(
                    f"Invalid tube geometry: wall_thickness ({stock_wall_thickness}) >= radius ({r_outer})"
                )
                raise ValueError("Tloušťka stěny nemůže být větší nebo rovna poloměru")
            volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length

    elif stock_shape in [StockShape.CASTING, StockShape.FORGING]:
        # Odlitek/výkovek: aproximace jako kruhová tyč
        if stock_diameter > 0 and stock_length > 0:
            r = stock_diameter / 2
            volume_mm3 = math.pi * r**2 * stock_length

    # Převod na hmotnost (Migration 2026-01-26: material_group.density místo group.density)
    volume_dm3 = volume_mm3 / 1_000_000  # mm³ → dm³
    weight_kg = volume_dm3 * material_group.density

    # ADR-014: Dynamický výběr ceny podle quantity
    total_weight = weight_kg * quantity
    price_per_kg = await get_price_per_kg_for_weight(price_category, total_weight, db)

    # Cena za 1 kus
    cost = weight_kg * price_per_kg

    result.volume_mm3 = round(volume_mm3, 0)
    result.weight_kg = round(weight_kg, 3)
    result.price_per_kg = price_per_kg  # Pro snapshot (ADR-012)
    result.density = material_group.density
    result.cost = round(cost, 2)

    return result


# AUDIT-2026-01-27: Removed deprecated functions:
# - calculate_material_cost_from_part() - replaced by calculate_stock_cost_from_part()
# - calculate_material_cost() - legacy with hardcoded data
# See git history for original implementation if needed.


def calculate_machining_cost(operation_time_min: float, hourly_rate: float) -> float:
    return round((operation_time_min / 60) * hourly_rate, 2)


def calculate_setup_cost(setup_time_min: float, hourly_rate: float, quantity: int) -> float:
    total_setup = (setup_time_min / 60) * hourly_rate
    return round(total_setup / quantity, 2) if quantity > 0 else 0


def calculate_coop_cost(coop_price: float, coop_min_price: float, quantity: int) -> float:
    if coop_price <= 0 or quantity <= 0:
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

            # Pokud není stroj vybraný, cena = 0 (BEZ fallback!)
            if not machine_id:
                continue

            machine = machines.get(machine_id, {})
            hourly_rate = machine.get("hourly_rate", 0)  # Default 0 pokud machine nenalezen

            if hourly_rate == 0:
                # Machine existuje ale nemá hourly_rate? Skip.
                continue

            machining = calculate_machining_cost(
                op.get("operation_time_min") or 0,  # None-safe
                hourly_rate,
            )
            setup = calculate_setup_cost(
                op.get("setup_time_min") or 0,  # None-safe
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

    # Percentages calculation removed (CRITICAL-003 fix)
    # Computed by Pydantic BatchResponse.material_percent etc. computed fields
    # This ensures Single Source of Truth (L-002)

    return result


# ============================================================================
# NOVÁ KALKULACE S KOEFICIENTY (ADR-016)
# ============================================================================

@dataclass
class PriceBreakdown:
    """
    Detailní rozpad ceny dílu s koeficienty (ADR-016).

    Struktura:
    1. Stroje (rozpad do komponent + setup vs operace)
    2. Režie (overhead_coefficient)
    3. Marže (margin_coefficient)
    4. Kooperace (coop_coefficient)
    5. Materiál (stock_coefficient)
    6. Celkem
    """
    # === STROJE ===
    # Rozpad komponent
    machine_amortization: float = 0.0
    machine_labor: float = 0.0
    machine_tools: float = 0.0
    machine_overhead: float = 0.0
    machine_total: float = 0.0

    # Setup vs Operace
    machine_setup_time_min: float = 0.0
    machine_setup_cost: float = 0.0
    machine_operation_time_min: float = 0.0
    machine_operation_cost: float = 0.0

    # === REŽIE + MARŽE (pouze na stroje) ===
    overhead_coefficient: float = 1.0
    work_with_overhead: float = 0.0

    margin_coefficient: float = 1.0
    work_with_margin: float = 0.0

    # === KOOPERACE (s koeficientem) ===
    coop_cost_raw: float = 0.0
    coop_coefficient: float = 1.0
    coop_cost: float = 0.0

    # === MATERIÁL (s koeficientem) ===
    material_cost_raw: float = 0.0
    stock_coefficient: float = 1.0
    material_cost: float = 0.0

    # === CELKEM ===
    total_cost: float = 0.0

    # === METADATA ===
    quantity: int = 1
    cost_per_piece: float = 0.0

    # === COMPUTED PROPERTIES ===
    @property
    def overhead_markup(self) -> float:
        """Přirážka režie v Kč"""
        return self.work_with_overhead - self.machine_total

    @property
    def margin_markup(self) -> float:
        """Přirážka marže v Kč"""
        return self.work_with_margin - self.work_with_overhead

    @property
    def overhead_percent(self) -> float:
        """Režie v %"""
        return (self.overhead_coefficient - 1) * 100

    @property
    def margin_percent(self) -> float:
        """Marže v %"""
        return (self.margin_coefficient - 1) * 100


async def get_config_coefficient(db: AsyncSession, key: str, default: float = 1.0) -> float:
    """Helper: načte koeficient ze SystemConfig"""
    from sqlalchemy import select
    from app.models.config import SystemConfig

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key)
    )
    config = result.scalar_one_or_none()
    return config.value_float if config else default


async def calculate_part_price(
    part,
    quantity: int = 1,
    db: AsyncSession = None
) -> PriceBreakdown:
    """
    Výpočet ceny dílu s rozpadem nákladů (ADR-016).

    Vzorec:
    1. Stroje: setup (bez nástrojů) + operace (s nástroji)
    2. Režie: machine_cost × overhead_coefficient
    3. Marže: (machine + režie) × margin_coefficient
    4. Kooperace: coop_raw × coop_coefficient
    5. Materiál: material_raw × stock_coefficient
    6. Celkem: work_with_margin + coop_cost + material_cost

    Args:
        part: Part instance (s eager-loaded operations + material_item)
        quantity: Množství kusů (setup distribuce + material tier)
        db: AsyncSession (required pro config a material cost)

    Returns:
        PriceBreakdown: Detailní rozpad nákladů
    """
    if db is None:
        raise ValueError("DB session required for price calculation")

    result = PriceBreakdown(quantity=quantity)

    # Načíst koeficienty ze SystemConfig
    result.overhead_coefficient = await get_config_coefficient(db, "overhead_coefficient", 1.20)
    result.margin_coefficient = await get_config_coefficient(db, "margin_coefficient", 1.25)
    result.stock_coefficient = await get_config_coefficient(db, "stock_coefficient", 1.15)
    result.coop_coefficient = await get_config_coefficient(db, "coop_coefficient", 1.10)

    # === 1. NÁKLADY STROJŮ ===
    machine_cost = 0.0
    setup_cost = 0.0
    operation_cost = 0.0
    total_setup_time = 0.0
    total_operation_time = 0.0

    machine_breakdown = {
        'amortization': 0.0,
        'labor': 0.0,
        'tools': 0.0,
        'overhead': 0.0
    }

    # Načíst operace (pokud nejsou eager loaded)
    if not hasattr(part, 'operations') or not part.operations:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.part import Part

        stmt = select(Part).where(Part.id == part.id).options(
            selectinload(Part.operations)
        )
        loaded = await db.execute(stmt)
        part = loaded.scalar_one()

    # Pre-load all work centers in ONE query (N+1 fix)
    from sqlalchemy import select
    from app.models.work_center import WorkCenter

    work_center_ids = {op.work_center_id for op in part.operations if op.work_center_id and not op.is_coop}
    work_centers_dict = {}
    if work_center_ids:
        work_centers_result = await db.execute(
            select(WorkCenter).where(WorkCenter.id.in_(work_center_ids))
        )
        work_centers_dict = {wc.id: wc for wc in work_centers_result.scalars().all()}

    for op in part.operations:
        if op.is_coop:
            # Kooperace - zpracujeme později
            result.coop_cost_raw += op.coop_price
            continue

        if not op.work_center_id:
            logger.warning(f"Operation {op.id} has no work_center_id, skipping")
            continue

        # Použít pre-loaded pracoviště z dictionary (N+1 fix)
        work_center = work_centers_dict.get(op.work_center_id)
        if not work_center:
            logger.warning(f"WorkCenter {op.work_center_id} not found, skipping operation {op.id}")
            continue

        # Setup (BEZ nástrojů) - jednou pro celý batch
        setup_hours = op.setup_time_min / 60
        op_setup_cost = setup_hours * work_center.hourly_rate_setup
        setup_cost += op_setup_cost
        total_setup_time += op.setup_time_min

        # Operace (S nástroji) - × quantity
        op_hours = op.operation_time_min / 60
        op_operation_cost = op_hours * work_center.hourly_rate_operation * quantity
        operation_cost += op_operation_cost
        total_operation_time += op.operation_time_min

        machine_cost += op_setup_cost + op_operation_cost

        # Rozpad do komponent
        total_hours = setup_hours + (op_hours * quantity)
        machine_breakdown['amortization'] += total_hours * work_center.hourly_rate_amortization
        machine_breakdown['labor'] += total_hours * work_center.hourly_rate_labor
        machine_breakdown['tools'] += (op_hours * quantity) * work_center.hourly_rate_tools  # POUZE operace!
        machine_breakdown['overhead'] += total_hours * work_center.hourly_rate_overhead

    result.machine_total = machine_cost
    result.machine_setup_time_min = total_setup_time
    result.machine_setup_cost = setup_cost
    result.machine_operation_time_min = total_operation_time
    result.machine_operation_cost = operation_cost

    result.machine_amortization = machine_breakdown['amortization']
    result.machine_labor = machine_breakdown['labor']
    result.machine_tools = machine_breakdown['tools']
    result.machine_overhead = machine_breakdown['overhead']

    # === 2. REŽIE (administrativní - pouze na stroje) ===
    result.work_with_overhead = result.machine_total * result.overhead_coefficient

    # === 3. MARŽE (pouze na stroje + režii) ===
    result.work_with_margin = result.work_with_overhead * result.margin_coefficient

    # === 4. KOOPERACE (s koeficientem) ===
    result.coop_cost = result.coop_cost_raw * result.coop_coefficient * quantity

    # === 5. MATERIÁL (s koeficientem) ===
    material_calc = await calculate_stock_cost_from_part(part, quantity, db)
    result.material_cost_raw = material_calc.cost  # Za 1 kus
    result.material_cost = result.material_cost_raw * result.stock_coefficient * quantity

    # === 6. CELKEM ===
    result.total_cost = result.work_with_margin + result.coop_cost + result.material_cost
    result.cost_per_piece = result.total_cost / quantity if quantity > 0 else 0

    return result


async def calculate_series_pricing(
    part,
    quantities: list[int],
    db: AsyncSession
) -> list[PriceBreakdown]:
    """
    Porovnání cen pro různé série (setup distribuce).

    Args:
        part: Part instance
        quantities: Seznam množství [1, 10, 50, 100, 500]
        db: AsyncSession

    Returns:
        List[PriceBreakdown]: Kalkulace pro každé množství
    """
    results = []
    for qty in quantities:
        breakdown = await calculate_part_price(part, qty, db)
        results.append(breakdown)
    return results
