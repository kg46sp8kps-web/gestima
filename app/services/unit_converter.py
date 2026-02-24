"""GESTIMA - Unit Converter (ADR-050: UOM System)

Pure functions for unit conversion. No DB dependencies, no state.

conv_factor semantic: 1 conv_uom = conv_factor uom
  e.g. conv_uom='m', conv_factor=15.41  →  1 m = 15.41 kg
"""


def to_base_uom(dim_mm: float, conv_uom: str, conv_factor: float) -> float:
    """
    Convert dimension in mm to base unit (kg) via conversion factor.

    Args:
        dim_mm: Dimension in mm (typically stock_length)
        conv_uom: Conversion unit ('m' or 'mm')
        conv_factor: How many base units per 1 conv_uom

    Returns:
        float: Weight in kg

    Raises:
        ValueError: If conv_uom is not supported

    Examples:
        to_base_uom(300, 'm', 15.41)  → 0.3 × 15.41 = 4.623 kg
        to_base_uom(300, 'mm', 0.01541) → 300 × 0.01541 = 4.623 kg
    """
    if conv_uom == 'm':
        return (dim_mm / 1000.0) * conv_factor
    elif conv_uom == 'mm':
        return dim_mm * conv_factor
    raise ValueError(f"Unsupported conv_uom: {conv_uom!r}. Supported: 'm', 'mm'")


def volume_to_weight(volume_mm3: float, density_kg_dm3: float) -> float:
    """
    Convert volume in mm³ to weight in kg using density.

    Args:
        volume_mm3: Volume in mm³
        density_kg_dm3: Density in kg/dm³ (from MaterialGroup)

    Returns:
        float: Weight in kg
    """
    return (volume_mm3 / 1_000_000.0) * density_kg_dm3


def mm_to_m(mm: float) -> float:
    """Convert mm to m."""
    return mm / 1000.0


def mm3_to_dm3(mm3: float) -> float:
    """Convert mm³ to dm³."""
    return mm3 / 1_000_000.0
