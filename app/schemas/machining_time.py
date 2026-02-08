"""GESTIMA - Machining Time Estimation Schemas

Pydantic schemas for machining time estimation API.
ADR-040: Machining Time Estimation System
"""

from pydantic import BaseModel, Field
from typing import Optional


class MachiningTimeEstimateRequest(BaseModel):
    """Request schema for machining time estimation."""

    material: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Material code (8-digit, e.g., '20910005')",
        pattern=r"^\d{8}$"
    )
    stock_type: str = Field(
        default="bbox",
        description="Stock type: 'bbox' or 'cylinder'",
        pattern=r"^(bbox|cylinder)$"
    )


class MachiningTimeBreakdown(BaseModel):
    """Breakdown details for time estimation."""

    material: str = Field(..., description="Material code")
    material_category: str = Field(..., description="Material category (e.g., 'alloy_steel')")
    iso_group: str = Field(..., description="ISO material group (P/M/K/N/S/H)")
    stock_volume_mm3: float = Field(..., ge=0, description="Stock volume in mm³")
    part_volume_mm3: float = Field(..., ge=0, description="Part volume in mm³")
    material_to_remove_mm3: float = Field(..., ge=0, description="Material to remove in mm³")
    surface_area_mm2: float = Field(..., ge=0, description="Part surface area in mm²")
    mrr_roughing_cm3_min: float = Field(..., gt=0, description="Roughing MRR in cm³/min")
    finishing_rate_cm2_min: float = Field(..., gt=0, description="Finishing rate in cm²/min")
    constraint_multiplier: float = Field(..., ge=1.0, description="Constraint penalty multiplier")
    critical_constraints: list[str] = Field(
        default_factory=list,
        description="List of detected constraints (e.g., ['deep_pocket', 'thin_wall'])"
    )
    stock_type: str = Field(..., description="Stock type used")


class MachiningTimeEstimateResponse(BaseModel):
    """Response schema for machining time estimation."""

    total_time_min: float = Field(..., ge=0, description="Total machining time in minutes")
    roughing_time_min: float = Field(..., ge=0, description="Total roughing time in minutes (main + aux)")
    roughing_time_main: float = Field(..., ge=0, description="Main roughing time (material removal)")
    roughing_time_aux: float = Field(..., ge=0, description="Auxiliary roughing time (rapids, tool changes - 20% of main)")
    finishing_time_min: float = Field(..., ge=0, description="Total finishing time in minutes (main + aux)")
    finishing_time_main: float = Field(..., ge=0, description="Main finishing time (surface machining)")
    finishing_time_aux: float = Field(..., ge=0, description="Auxiliary finishing time (rapids, tool changes - 15% of main)")
    setup_time_min: float = Field(default=0.0, ge=0, description="Setup time (deprecated, always 0)")
    breakdown: MachiningTimeBreakdown = Field(..., description="Detailed breakdown")
    deterministic: bool = Field(..., description="Always True (deterministic calculation)")


class MaterialListItem(BaseModel):
    """Material list item for available materials endpoint."""

    code: str = Field(..., description="8-digit material code")
    category: str = Field(..., description="Material category")
    iso_group: str = Field(..., description="ISO material group")
    hardness_hb: int = Field(..., description="Hardness in Brinell (HB)")
    density: float = Field(..., description="Density in kg/dm³")


class MachiningTimeReEstimateRequest(BaseModel):
    """Request schema for re-estimating machining time with different material."""

    filename: str = Field(..., min_length=1, max_length=255, description="STEP filename (from uploads/drawings)")
    material_code: str = Field(..., min_length=1, max_length=20, description="Material group code (e.g., 'OCEL-AUTO', 'HLINIK')")
    stock_type: str = Field(
        default="bbox",
        description="Stock type: 'bbox' or 'cylinder'",
        pattern=r"^(bbox|cylinder)$"
    )
