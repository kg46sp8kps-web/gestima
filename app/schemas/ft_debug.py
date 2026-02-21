"""GESTIMA - FT Debug schemas for fine-tuning data inspection."""

from typing import Optional
from pydantic import BaseModel, Field


class FtPartOperation(BaseModel):
    """Ground truth operation for one machine category."""

    category: str = Field(..., description="SAW/LATHE/MILL/DRILL/MANUAL/QC")
    machine: str = Field(..., description="Most common machine name")
    operation_time_min: float = Field(..., description="Trimmed mean operation time (min/ks)")
    setup_time_min: float = Field(0, description="Trimmed mean setup time (min)")
    manning_pct: int = Field(100, description="Manning coefficient (%)")
    num_operations: int = Field(1, description="Mode of operation count per VP")
    n_vp: int = Field(0, description="Number of VPs used for this category")
    planned_time_min: Optional[float] = Field(None, description="Planned operation time from Infor norms (median across VPs)")
    norm_ratio: Optional[float] = Field(None, description="actual/planned ratio (>1 = slower than norm)")
    cv: Optional[float] = Field(None, description="Coefficient of variation for time (std/mean)")
    manning_cv: Optional[float] = Field(None, description="Coefficient of variation for manning (std/mean)")


class FtPartSummary(BaseModel):
    """Summary of one part for FT debug listing."""

    part_id: int = Field(..., description="Part database ID")
    article_number: str = Field(..., description="Part article number")
    name: Optional[str] = Field(None, description="Part name")
    file_id: Optional[int] = Field(None, description="File record ID for drawing PDF")
    vp_count: int = Field(0, description="Number of distinct VPs")
    material_norm: Optional[str] = Field(None, description="Resolved material W.Nr")
    stock_shape: Optional[str] = Field(None, description="Stock shape from material_inputs")
    operations: list[FtPartOperation] = Field(default_factory=list)
    max_cv: Optional[float] = Field(None, description="Max CV across categories")
    total_production_time: float = Field(0, description="Sum op time excl QC")
    total_planned_time: Optional[float] = Field(None, description="Sum planned time from Infor norms excl QC")
    norm_ratio: Optional[float] = Field(None, description="Total actual/planned ratio")
    skip_reason: Optional[str] = Field(None, description="Why excluded from FT")
    is_eligible: bool = Field(True, description="Passed all FT filters")


class FtPartsResponse(BaseModel):
    """Response for GET /api/ft/debug/parts."""

    total: int = Field(..., description="Total parts found (before eligibility filter)")
    eligible: int = Field(..., description="Parts passing all FT eligibility criteria")
    skipped: int = Field(..., description="Parts excluded (with skip_reason)")
    parts: list[FtPartSummary] = Field(default_factory=list)


class FtInferenceRequest(BaseModel):
    """Request for POST /api/ft/debug/inference."""

    part_id: int = Field(..., gt=0, description="Part ID to run inference on")


class FtInferenceComparison(BaseModel):
    """Per-category comparison: AI vs GT."""

    category: str = Field(..., description="Machine category (SAW/LATHE/MILL/DRILL/MANUAL/QC)")
    ai_time: float = Field(..., description="AI-predicted operation time (min)")
    gt_time: float = Field(..., description="Ground truth operation time (min)")
    delta: float = Field(..., description="AI time minus GT time")
    ai_setup: float = Field(..., description="AI-predicted setup time (min)")
    gt_setup: float = Field(..., description="Ground truth setup time (min)")


class FtInferenceResult(BaseModel):
    """Response for POST /api/ft/debug/inference."""

    part_id: int = Field(..., description="Part ID that was tested")
    article_number: str = Field(..., description="Part article number")
    material_gt: Optional[str] = Field(None, description="Ground truth material W.Nr")
    material_ai: Optional[str] = Field(None, description="AI-predicted material")
    material_match: bool = Field(False, description="Whether AI material matches GT")
    gt_operations: list[FtPartOperation] = Field(
        default_factory=list,
        description="Ground truth operations",
    )
    ai_operations: list[dict] = Field(
        default_factory=list,
        description="Raw AI-predicted operations",
    )
    comparisons: list[FtInferenceComparison] = Field(
        default_factory=list,
        description="Per-category time comparisons",
    )
    mape: Optional[float] = Field(
        None,
        description="Mean Absolute Percentage Error (%)",
    )
    tokens_used: int = Field(0, description="Total tokens consumed by inference call")
    cost_estimate: float = Field(0.0, description="Estimated USD cost of inference call")


class FtExportRequest(BaseModel):
    """Request for POST /api/ft/debug/export."""

    part_ids: list[int] = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="List of part IDs to include in JSONL export",
    )
