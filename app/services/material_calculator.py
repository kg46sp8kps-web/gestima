"""GESTIMA - Material Weight & Price Calculator

This service calculates material weight and pricing based on stock geometry,
MaterialGroup density (via MaterialPriceCategory), and MaterialPriceTier configuration.

Flow (ADR-014):
    price_category_id → MaterialPriceCategory → material_group → density

Usage:
    result = await calculate_material_weight_and_price(
        stock_shape=StockShape.ROUND_BAR,
        dimensions={'diameter': 20, 'length': 100},
        price_category_id=1,  # Density loaded via category.material_group
        quantity=10,
        db=db
    )
"""

import logging
import math
from typing import Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.enums import StockShape
from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialPriceTier

logger = logging.getLogger(__name__)


@dataclass
class MaterialCalculation:
    """Result of material weight and price calculation"""
    # Geometry
    volume_mm3: float = 0.0
    volume_dm3: float = 0.0

    # Weight
    weight_kg: float = 0.0          # Weight per piece
    total_weight_kg: float = 0.0    # Weight × quantity

    # Pricing
    price_per_kg: float = 0.0
    cost_per_piece: float = 0.0
    total_cost: float = 0.0

    # Metadata
    density: float = 0.0             # kg/dm³ (from MaterialGroup)
    quantity: int = 1
    tier_id: Optional[int] = None    # Selected MaterialPriceTier.id
    tier_range: str = ""             # e.g., "0-15 kg"


# ============================================================================
# VOLUME CALCULATION BY STOCK SHAPE
# ============================================================================

def calculate_volume_round_bar(diameter: float, length: float) -> float:
    """
    Calculate volume for ROUND_BAR.

    Formula: π × (D/2)² × L

    Args:
        diameter: Diameter in mm
        length: Length in mm

    Returns:
        float: Volume in mm³
    """
    if diameter <= 0 or length <= 0:
        return 0.0

    radius = diameter / 2
    return math.pi * radius**2 * length


def calculate_volume_square_bar(side: float, length: float) -> float:
    """
    Calculate volume for SQUARE_BAR.

    Formula: side² × L

    Args:
        side: Side length in mm (uses 'width' dimension)
        length: Length in mm

    Returns:
        float: Volume in mm³
    """
    if side <= 0 or length <= 0:
        return 0.0

    return side**2 * length


def calculate_volume_flat_bar(width: float, thickness: float, length: float) -> float:
    """
    Calculate volume for FLAT_BAR.

    Formula: width × thickness × L

    Args:
        width: Width in mm
        thickness: Thickness in mm (uses 'height' dimension)
        length: Length in mm

    Returns:
        float: Volume in mm³
    """
    if width <= 0 or thickness <= 0 or length <= 0:
        return 0.0

    return width * thickness * length


def calculate_volume_hexagonal_bar(side: float, length: float) -> float:
    """
    Calculate volume for HEXAGONAL_BAR.

    Formula: 2.598 × side² × L (where 2.598 = 3√3/2)

    Args:
        side: Side length in mm (uses 'diameter' dimension)
        length: Length in mm

    Returns:
        float: Volume in mm³
    """
    if side <= 0 or length <= 0:
        return 0.0

    # 3√3/2 = 2.598076211353316
    hexagon_constant = 2.598076211353316
    return hexagon_constant * side**2 * length


def calculate_volume_plate(width: float, height: float, thickness: float) -> float:
    """
    Calculate volume for PLATE.

    Formula: width × height × thickness

    Args:
        width: Width in mm
        height: Height in mm
        thickness: Thickness in mm

    Returns:
        float: Volume in mm³
    """
    if width <= 0 or height <= 0 or thickness <= 0:
        return 0.0

    return width * height * thickness


def calculate_volume_tube(
    outer_diameter: float,
    wall_thickness: float,
    length: float
) -> float:
    """
    Calculate volume for TUBE.

    Formula: π × ((D_outer/2)² - (D_inner/2)²) × L

    Args:
        outer_diameter: Outer diameter in mm (uses 'diameter' dimension)
        wall_thickness: Wall thickness in mm
        length: Length in mm

    Returns:
        float: Volume in mm³

    Raises:
        ValueError: If wall_thickness >= radius (invalid geometry)
    """
    if outer_diameter <= 0 or wall_thickness <= 0 or length <= 0:
        return 0.0

    r_outer = outer_diameter / 2
    r_inner = r_outer - wall_thickness

    if r_inner <= 0:
        raise ValueError(
            f"Invalid tube geometry: wall_thickness ({wall_thickness}mm) "
            f">= radius ({r_outer}mm)"
        )

    return math.pi * (r_outer**2 - r_inner**2) * length


def calculate_volume_casting_forging(diameter: float, length: float) -> float:
    """
    Calculate volume for CASTING or FORGING.

    Approximation: Uses round bar formula (π × (D/2)² × L)

    Args:
        diameter: Approximate diameter in mm
        length: Approximate length in mm

    Returns:
        float: Volume in mm³
    """
    return calculate_volume_round_bar(diameter, length)


# ============================================================================
# VOLUME DISPATCHER
# ============================================================================

def calculate_volume(stock_shape: StockShape, dimensions: Dict[str, float]) -> float:
    """
    Calculate volume for any stock shape.

    Args:
        stock_shape: StockShape enum value
        dimensions: Dictionary with dimension values in mm
            - ROUND_BAR: {'diameter': float, 'length': float}
            - SQUARE_BAR: {'width': float, 'length': float}
            - FLAT_BAR: {'width': float, 'height': float, 'length': float}
            - HEXAGONAL_BAR: {'diameter': float, 'length': float}
            - PLATE: {'width': float, 'height': float, 'thickness': float}
            - TUBE: {'diameter': float, 'wall_thickness': float, 'length': float}
            - CASTING/FORGING: {'diameter': float, 'length': float}

    Returns:
        float: Volume in mm³

    Raises:
        ValueError: If required dimensions are missing or invalid
    """
    try:
        if stock_shape == StockShape.ROUND_BAR:
            return calculate_volume_round_bar(
                diameter=dimensions.get('diameter', 0),
                length=dimensions.get('length', 0)
            )

        elif stock_shape == StockShape.SQUARE_BAR:
            return calculate_volume_square_bar(
                side=dimensions.get('width', 0),
                length=dimensions.get('length', 0)
            )

        elif stock_shape == StockShape.FLAT_BAR:
            return calculate_volume_flat_bar(
                width=dimensions.get('width', 0),
                thickness=dimensions.get('height', 0),
                length=dimensions.get('length', 0)
            )

        elif stock_shape == StockShape.HEXAGONAL_BAR:
            return calculate_volume_hexagonal_bar(
                side=dimensions.get('diameter', 0),
                length=dimensions.get('length', 0)
            )

        elif stock_shape == StockShape.PLATE:
            return calculate_volume_plate(
                width=dimensions.get('width', 0),
                height=dimensions.get('height', 0),
                thickness=dimensions.get('thickness', 0)
            )

        elif stock_shape == StockShape.TUBE:
            return calculate_volume_tube(
                outer_diameter=dimensions.get('diameter', 0),
                wall_thickness=dimensions.get('wall_thickness', 0),
                length=dimensions.get('length', 0)
            )

        elif stock_shape in [StockShape.CASTING, StockShape.FORGING]:
            return calculate_volume_casting_forging(
                diameter=dimensions.get('diameter', 0),
                length=dimensions.get('length', 0)
            )

        else:
            logger.error(f"Unsupported stock shape: {stock_shape}")
            return 0.0

    except ValueError as e:
        logger.error(f"Volume calculation failed for {stock_shape}: {e}")
        raise


# ============================================================================
# PRICE TIER SELECTION
# ============================================================================

async def find_price_tier(
    price_category_id: int,
    total_weight_kg: float,
    db: AsyncSession
) -> Optional[MaterialPriceTier]:
    """
    Find matching MaterialPriceTier based on weight.

    Selection rule: Largest min_weight <= total_weight (closest lower tier).

    Args:
        price_category_id: MaterialPriceCategory.id
        total_weight_kg: Total weight (weight_per_piece × quantity)
        db: AsyncSession

    Returns:
        MaterialPriceTier or None if no matching tier found

    Example:
        Tiers: [0-15: 49.4], [15-100: 34.5], [100+: 26.3]
        weight=5 → tier 0-15
        weight=25 → tier 15-100
        weight=150 → tier 100+
    """
    # Load price category with tiers
    stmt = select(MaterialPriceCategory).where(
        MaterialPriceCategory.id == price_category_id
    ).options(selectinload(MaterialPriceCategory.tiers))

    result = await db.execute(stmt)
    price_category = result.scalar_one_or_none()

    if not price_category:
        logger.error(f"MaterialPriceCategory {price_category_id} not found")
        return None

    if not price_category.tiers:
        logger.error(
            f"No tiers configured for MaterialPriceCategory {price_category_id} "
            f"({price_category.code})"
        )
        return None

    # Filter tiers where min_weight <= total_weight
    valid_tiers = [
        tier for tier in price_category.tiers
        if tier.min_weight <= total_weight_kg
    ]

    if not valid_tiers:
        logger.error(
            f"No valid tier for weight {total_weight_kg}kg in category "
            f"{price_category.code}. Check tier configuration (should have "
            f"tier with min_weight=0)."
        )
        return None

    # Select tier with largest min_weight (closest lower)
    selected_tier = max(valid_tiers, key=lambda t: t.min_weight)

    logger.debug(
        f"Selected tier for {total_weight_kg}kg: "
        f"[{selected_tier.min_weight}-{selected_tier.max_weight or '∞'}] → "
        f"{selected_tier.price_per_kg} Kč/kg"
    )

    return selected_tier


# ============================================================================
# MAIN CALCULATION FUNCTION
# ============================================================================

async def calculate_material_weight_and_price(
    stock_shape: StockShape,
    dimensions: Dict[str, float],
    price_category_id: int,
    quantity: int = 1,
    db: AsyncSession = None
) -> MaterialCalculation:
    """
    Calculate material weight and price based on geometry and quantity.

    This is the main entry point for material calculations. It:
    1. Loads MaterialPriceCategory (with MaterialGroup for density)
    2. Calculates volume from stock geometry
    3. Converts to weight using MaterialGroup.density (via price_category.material_group)
    4. Finds matching MaterialPriceTier based on total weight
    5. Calculates total cost

    Args:
        stock_shape: StockShape enum value
        dimensions: Dictionary with dimension values in mm (see calculate_volume)
        price_category_id: MaterialPriceCategory.id (for price tiers AND density via material_group)
        quantity: Number of pieces (default: 1)
        db: AsyncSession (required)

    Returns:
        MaterialCalculation: Complete calculation result

    Raises:
        HTTPException: If price_category not found or material_group missing
        ValueError: If invalid geometry provided

    Example:
        >>> result = await calculate_material_weight_and_price(
        ...     stock_shape=StockShape.ROUND_BAR,
        ...     dimensions={'diameter': 20, 'length': 100},
        ...     price_category_id=1,
        ...     quantity=10,
        ...     db=db
        ... )
        >>> print(f"Weight: {result.weight_kg}kg, Cost: {result.cost_per_piece}Kč")
    """
    if db is None:
        raise ValueError("DB session is required")

    result = MaterialCalculation(quantity=quantity)

    # === 1. LOAD PRICE CATEGORY (with MaterialGroup for density) ===
    stmt = select(MaterialPriceCategory).where(
        MaterialPriceCategory.id == price_category_id
    ).options(selectinload(MaterialPriceCategory.material_group))

    pc_result = await db.execute(stmt)
    price_category = pc_result.scalar_one_or_none()

    if not price_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialPriceCategory {price_category_id} not found"
        )

    # Verify material_group exists (ADR-014: required for density)
    if not price_category.material_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MaterialPriceCategory {price_category_id} has no MaterialGroup assigned"
        )

    material_group = price_category.material_group

    if material_group.density is None or material_group.density <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MaterialGroup {material_group.id} has invalid density "
                   f"({material_group.density})"
        )

    result.density = material_group.density

    # === 2. CALCULATE VOLUME ===
    try:
        volume_mm3 = calculate_volume(stock_shape, dimensions)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid geometry: {str(e)}"
        )

    if volume_mm3 <= 0:
        logger.warning(
            f"Zero volume calculated for {stock_shape} with dimensions {dimensions}"
        )
        # Return zero-cost result (not an error - might be intentional)
        result.volume_mm3 = 0.0
        result.volume_dm3 = 0.0
        return result

    result.volume_mm3 = round(volume_mm3, 0)
    result.volume_dm3 = round(volume_mm3 / 1_000_000, 6)

    # === 3. CALCULATE WEIGHT ===
    weight_per_piece = result.volume_dm3 * result.density
    result.weight_kg = round(weight_per_piece, 3)
    result.total_weight_kg = round(weight_per_piece * quantity, 3)

    # === 4. FIND PRICE TIER ===
    tier = await find_price_tier(price_category_id, result.total_weight_kg, db)

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching price tier found for weight {result.total_weight_kg}kg "
                   f"in price_category_id {price_category_id}"
        )

    if tier.price_per_kg is None or tier.price_per_kg <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MaterialPriceTier {tier.id} has invalid price_per_kg "
                   f"({tier.price_per_kg})"
        )

    result.price_per_kg = tier.price_per_kg
    result.tier_id = tier.id

    # Format tier range for display
    max_w = f"{tier.max_weight}kg" if tier.max_weight else "∞"
    result.tier_range = f"{tier.min_weight}-{max_w}"

    # === 5. CALCULATE COST ===
    result.cost_per_piece = round(result.weight_kg * result.price_per_kg, 2)
    result.total_cost = round(result.cost_per_piece * quantity, 2)

    logger.info(
        f"Material calculation: {stock_shape} | "
        f"Weight: {result.weight_kg}kg × {quantity} = {result.total_weight_kg}kg | "
        f"Tier: {result.tier_range} @ {result.price_per_kg}Kč/kg | "
        f"Cost: {result.cost_per_piece}Kč/pc × {quantity} = {result.total_cost}Kč"
    )

    return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def calculate_from_material_item(
    material_item,
    length_mm: float,
    quantity: int = 1,
    db: AsyncSession = None
) -> MaterialCalculation:
    """
    Calculate material cost from MaterialItem + custom length.

    This is a convenience wrapper that extracts geometry and IDs from
    MaterialItem and calls calculate_material_weight_and_price.

    Args:
        material_item: MaterialItem instance (with shape, diameter, etc.)
        length_mm: Custom length in mm
        quantity: Number of pieces
        db: AsyncSession

    Returns:
        MaterialCalculation

    Raises:
        HTTPException: If MaterialItem has invalid configuration
    """
    if db is None:
        raise ValueError("DB session is required")

    # Build dimensions dict from MaterialItem
    dimensions = {'length': length_mm}

    if material_item.diameter:
        dimensions['diameter'] = material_item.diameter
    if material_item.width:
        dimensions['width'] = material_item.width
    if material_item.thickness:
        dimensions['thickness'] = material_item.thickness
    if material_item.wall_thickness:
        dimensions['wall_thickness'] = material_item.wall_thickness

    # For PLATE, use 'height' field if present (some items use thickness as height)
    if material_item.shape == StockShape.PLATE:
        # PLATE needs width × height × thickness
        # Assuming: width=width, height=thickness, thickness=length override
        if 'thickness' not in dimensions:
            dimensions['thickness'] = length_mm
            dimensions['height'] = material_item.thickness or 0

    return await calculate_material_weight_and_price(
        stock_shape=material_item.shape,
        dimensions=dimensions,
        price_category_id=material_item.price_category_id,
        quantity=quantity,
        db=db
    )
