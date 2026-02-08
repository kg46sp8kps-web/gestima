"""
Vision Hybrid Schemas — Pydantic models for Vision API integration.

ADR-TBD: Vision Hybrid Pipeline
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class VisionSpatialMapping(BaseModel):
    """
    Vision API output: mapping of annotations to drawing features.

    Structured output from Claude Vision API.
    """

    annotation_label: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Label text from PDF annotation (e.g., 'SHAFT Ø40.00 L=80.00')"
    )
    pdf_bbox: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box [x, y, width, height] in PDF points"
    )
    match_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) for annotation-to-feature match"
    )
    dimension_verified: bool = Field(
        ...,
        description="Whether dimensions in annotation match drawing dimensions"
    )


class VisionMappingResponse(BaseModel):
    """Complete Vision API response with all mappings."""

    mappings: List[VisionSpatialMapping] = Field(
        default_factory=list,
        description="List of annotation-to-feature mappings"
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="PDF page number analyzed"
    )
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Additional notes from Vision API (e.g., warnings, issues)"
    )


class RefinementStatus(BaseModel):
    """Status of coordinate refinement iteration."""

    iteration: int = Field(
        ...,
        ge=0,
        le=10,
        description="Current iteration number"
    )
    error: float = Field(
        ...,
        ge=0.0,
        description="Average coordinate error (0-1)"
    )
    converged: bool = Field(
        ...,
        description="Whether refinement converged"
    )
    scale_factor: float = Field(
        ...,
        gt=0.0,
        description="Current scale factor (PDF points per mm)"
    )
    features: List[dict] = Field(
        default_factory=list,
        description="Feature segments with refined coordinates"
    )
    annotated_pdf_url: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="URL to download annotated PDF"
    )


class VisionRefinementRequest(BaseModel):
    """Request to start Vision refinement job."""

    part_id: int = Field(
        ...,
        gt=0,
        description="Part ID with PDF and STEP drawings"
    )
    max_iterations: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum refinement iterations"
    )
    convergence_threshold: float = Field(
        0.01,
        gt=0.0,
        lt=1.0,
        description="Error threshold for convergence"
    )


class AvailablePartResponse(BaseModel):
    """Part with both PDF and STEP drawings available."""

    part_id: int = Field(..., gt=0)
    part_number: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=200)  # Part.name, not description
    pdf_drawing_id: int = Field(..., gt=0)
    pdf_filename: str = Field(..., min_length=1, max_length=500)
    step_drawing_id: int = Field(..., gt=0)
    step_filename: str = Field(..., min_length=1, max_length=500)
