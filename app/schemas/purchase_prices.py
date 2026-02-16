"""GESTIMA - Purchase Price Analysis Schemas

Pydantic v2 schemas for analyzing purchase prices from Infor SLPoItems.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TierAnalysis(BaseModel):
    """Real data analysis for one PriceTier.

    Contains actual purchase order data aggregated by weight tier,
    compared against current PriceTier configuration.
    """
    tier_id: int = Field(..., gt=0, description="PriceTier DB ID")
    tier_label: str = Field(..., min_length=1, max_length=50)
    min_weight: float = Field(..., ge=0)
    max_weight: Optional[float] = Field(None, ge=0)
    avg_price_per_kg: float = Field(..., ge=0)
    total_qty_kg: float = Field(..., ge=0)
    total_cost_czk: float = Field(..., ge=0)
    po_line_count: int = Field(..., ge=0)
    min_price: float = Field(..., ge=0)
    max_price: float = Field(..., ge=0)
    current_price: Optional[float] = Field(None, ge=0)
    diff_pct: Optional[float] = Field(None)
    current_tier_version: int = Field(..., ge=0, description="Current tier version for optimistic locking")
    sufficient_data: bool = Field(...)


class SuggestedBoundary(BaseModel):
    """Suggested tier boundary based on distribution analysis."""
    tier_index: int = Field(..., ge=0, description="Tier position (0=first, 1=second, etc.)")
    current_max_weight: Optional[float] = Field(None, ge=0)
    suggested_max_weight: Optional[float] = Field(None, ge=0)
    reason: str = Field(..., min_length=1, max_length=200)


class WeightDistribution(BaseModel):
    """Weight distribution analysis for tier boundary recommendations.

    Provides statistical breakdown of QtyReceived values to help
    define optimal weight tier boundaries.
    """
    p25: float = Field(..., ge=0)
    p50: float = Field(..., ge=0)
    p75: float = Field(..., ge=0)
    min_qty: float = Field(..., ge=0)
    max_qty: float = Field(..., ge=0)
    avg_qty: float = Field(..., ge=0)
    sample_count: int = Field(..., ge=0)
    suggested_boundaries: List[SuggestedBoundary] = Field(default_factory=list)


class PriceCategoryAnalysis(BaseModel):
    """Full purchase price analysis for one PriceCategory.

    Aggregates PO data from Infor SLPoItems, calculates weighted averages
    by weight tier, and compares against current PriceTier configuration.
    """
    price_category_id: int = Field(..., gt=0)
    price_category_code: str = Field(..., min_length=1, max_length=50)
    price_category_name: str = Field(..., min_length=1, max_length=200)
    material_group_id: Optional[int] = Field(None, gt=0)
    material_group_name: Optional[str] = Field(None, min_length=1, max_length=100)
    shape: Optional[str] = Field(None, min_length=1, max_length=50)
    total_po_lines: int = Field(..., ge=0)
    total_qty_received_kg: float = Field(..., ge=0)
    total_cost_czk: float = Field(..., ge=0)
    weighted_avg_price_per_kg: float = Field(..., ge=0)
    min_unit_price: float = Field(..., ge=0)
    max_unit_price: float = Field(..., ge=0)
    unique_vendors: int = Field(..., ge=0)
    top_vendors: List[str] = Field(default_factory=list)
    tiers: List[TierAnalysis] = Field(default_factory=list)
    weight_distribution: Optional[WeightDistribution] = Field(None)
    quarterly_prices: Dict[str, float] = Field(default_factory=dict)


class UnmatchedItem(BaseModel):
    """PO line item that couldn't be matched to PriceCategory.

    Tracks items that failed W.Nr extraction or MaterialNorm matching
    to help identify gaps in master data.
    """
    item: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=500)
    w_nr: Optional[str] = Field(None, min_length=1, max_length=20)
    reason: str = Field(..., min_length=1, max_length=200)
    total_cost: float = Field(..., ge=0)
    count: int = Field(..., ge=1)


class PurchasePriceAnalysisResponse(BaseModel):
    """Full API response for purchase price analysis.

    Contains aggregated purchase order data from Infor SLPoItems,
    matched against Gestima MaterialNorms and PriceCategories.
    """
    year_from: int = Field(..., ge=2000, le=2100)
    date_range: str = Field(..., min_length=1, max_length=50)
    total_po_lines_fetched: int = Field(..., ge=0)
    total_po_lines_matched: int = Field(..., ge=0)
    total_po_lines_unmatched: int = Field(..., ge=0)
    unique_materials: int = Field(..., ge=0)
    categories: List[PriceCategoryAnalysis] = Field(default_factory=list)
    unmatched: List[UnmatchedItem] = Field(default_factory=list)
    cached: bool = Field(...)
    fetch_time_seconds: float = Field(..., ge=0)


class TierUpdate(BaseModel):
    """Single tier price update with optimistic locking."""
    tier_id: int = Field(..., gt=0)
    new_price: float = Field(..., ge=0)
    version: int = Field(..., ge=0)


class ApplyPriceRequest(BaseModel):
    """Request to update prices for one PriceCategory."""
    category_id: int = Field(..., gt=0)
    tier_updates: List[TierUpdate] = Field(..., min_length=1)


class ApplyPriceBulkRequest(BaseModel):
    """Request to bulk update prices across multiple categories."""
    updates: List[ApplyPriceRequest] = Field(..., min_length=1)


class TierBoundaryUpdate(BaseModel):
    """Single tier boundary update."""
    tier_id: int = Field(..., gt=0)
    new_min_weight: float = Field(..., ge=0)
    new_max_weight: Optional[float] = Field(None, ge=0, description="None = infinity (last tier)")
    version: int = Field(..., ge=0, description="Optimistic locking version")


class ApplyBoundariesRequest(BaseModel):
    """Request to update tier boundaries for one PriceCategory."""
    category_id: int = Field(..., gt=0)
    tier_boundaries: List[TierBoundaryUpdate] = Field(..., min_length=1)


class ApplyPriceResponse(BaseModel):
    """Response for price update operations."""
    success: bool = Field(...)
    updated_count: int = Field(..., ge=0)
    errors: List[str] = Field(default_factory=list)
