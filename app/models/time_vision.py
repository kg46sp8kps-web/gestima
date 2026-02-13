"""GESTIMA - TimeVision models (AI machining time estimation from PDF)"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class TimeVisionEstimation(Base, AuditMixin):
    """AI-generated machining time estimation from PDF drawing"""
    __tablename__ = "time_vision_estimations"

    id = Column(Integer, primary_key=True, index=True)

    # Source
    pdf_filename = Column(String(255), nullable=False)
    pdf_path = Column(String(500), nullable=False)

    # AI provider: "openai" (base GPT-4o), "openai_ft" (fine-tuned)
    ai_provider = Column(String(20), default="openai", nullable=False)
    # Full model identifier (e.g. "ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH")
    ai_model = Column(String(200), nullable=True)

    # Vision extraction results (Call 1)
    part_number_detected = Column(String(100), nullable=True)
    material_detected = Column(String(100), nullable=True)
    material_group_id = Column(Integer, ForeignKey("material_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    material_coefficient = Column(Float, default=1.0)

    part_type = Column(String(10), default="PRI")  # ROT / PRI / COMBINED
    complexity = Column(String(20), default="medium")  # simple / medium / complex

    max_diameter_mm = Column(Float, nullable=True)
    max_length_mm = Column(Float, nullable=True)
    max_width_mm = Column(Float, nullable=True)
    max_height_mm = Column(Float, nullable=True)
    shape_ratio = Column(Float, nullable=True)  # L/D for ROT, computed

    manufacturing_description = Column(Text, nullable=True)  # Free text from Vision
    operations_detected = Column(Text, nullable=True)  # JSON list: ["soustružení", "vrtání"]

    vision_extraction_json = Column(Text, nullable=True)  # Full Call 1 JSON result

    # Estimation results (Call 2)
    estimated_time_min = Column(Float, nullable=True)
    estimation_reasoning = Column(Text, nullable=True)
    estimation_breakdown_json = Column(Text, nullable=True)  # JSON: [{operation, time_min, notes}]
    confidence = Column(String(20), nullable=True)  # low / medium / high

    # Similar parts used
    similar_parts_json = Column(Text, nullable=True)  # JSON: [{id, score, time, ...}]

    # Actual production time (real shop floor time, filled after manufacturing)
    actual_time_min = Column(Float, nullable=True)
    actual_entered_at = Column(DateTime, nullable=True)
    actual_notes = Column(Text, nullable=True)

    # Human estimate (user's estimate before/during manufacturing)
    human_estimate_min = Column(Float, nullable=True)

    # Status lifecycle: pending → extracted → estimated → calibrated → verified
    # calibrated = human estimate filled, verified = actual production time filled
    status = Column(String(20), default="pending", nullable=False, index=True)

    # Relationships
    material_group = relationship("MaterialGroup", foreign_keys=[material_group_id])


# ========== PYDANTIC SCHEMAS ==========

class VisionExtractionResult(BaseModel):
    """Structured output from AI vision analysis"""
    model_config = ConfigDict(from_attributes=True)

    part_type: Literal["ROT", "PRI", "COMBINED"] = Field(description="Part classification")
    complexity: Literal["simple", "medium", "complex"] = Field(description="Complexity profile")

    max_diameter_mm: Optional[float] = Field(None, gt=0, lt=5000)
    max_length_mm: Optional[float] = Field(None, gt=0, lt=10000)
    max_width_mm: Optional[float] = Field(None, gt=0, lt=5000)
    max_height_mm: Optional[float] = Field(None, gt=0, lt=5000)

    material_hint: Optional[str] = Field(None, max_length=100)
    part_number_hint: Optional[str] = Field(None, max_length=100)

    manufacturing_description: str = Field(min_length=10, max_length=2000, description="Detailed manufacturing description")
    operations: List[str] = Field(min_length=1, description="List of operations")
    surface_finish: Optional[str] = Field(None, max_length=50)
    requires_grinding: bool = Field(default=False)


class OperationBreakdown(BaseModel):
    """Per-operation time breakdown"""
    operation: str = Field(min_length=1, max_length=100)
    time_min: float = Field(ge=0, lt=10000)
    notes: Optional[str] = Field(None, max_length=500)


class TimeEstimationResult(BaseModel):
    """Structured output from AI time estimation"""
    model_config = ConfigDict(from_attributes=True)

    estimated_time_min: float = Field(gt=0, lt=10000)
    confidence: Literal["low", "medium", "high"] = Field(description="Estimation confidence")
    reasoning: str = Field(min_length=10, max_length=5000)
    breakdown: List[OperationBreakdown] = Field(min_length=1)


class SimilarPartMatch(BaseModel):
    """Similar part found in DB"""
    estimation_id: int
    pdf_filename: str
    part_type: str
    material_group: Optional[str] = None
    complexity: str
    max_diameter_mm: Optional[float] = None
    max_length_mm: Optional[float] = None
    actual_time_min: float
    similarity_score: float = Field(ge=0, le=1)
    score_breakdown: dict = Field(default_factory=dict)


class TimeVisionResponse(BaseModel):
    """Full estimation response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    pdf_filename: str
    status: str
    ai_provider: str = Field(default="openai")
    ai_model: Optional[str] = None

    part_type: Optional[str] = None
    complexity: Optional[str] = None
    material_detected: Optional[str] = None
    material_coefficient: float = Field(default=1.0)

    max_diameter_mm: Optional[float] = None
    max_length_mm: Optional[float] = None
    max_width_mm: Optional[float] = None
    max_height_mm: Optional[float] = None
    shape_ratio: Optional[float] = None

    manufacturing_description: Optional[str] = None
    operations_detected: Optional[str] = None  # JSON string

    estimated_time_min: Optional[float] = None
    estimation_reasoning: Optional[str] = None
    estimation_breakdown_json: Optional[str] = None
    confidence: Optional[str] = None

    similar_parts_json: Optional[str] = None
    vision_extraction_json: Optional[str] = None

    actual_time_min: Optional[float] = None
    actual_notes: Optional[str] = None
    human_estimate_min: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = Field(default=0)


class TimeVisionListItem(BaseModel):
    """Lightweight response for list view"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    pdf_filename: str
    status: str
    ai_provider: str = Field(default="openai")
    ai_model: Optional[str] = None
    part_type: Optional[str] = None
    complexity: Optional[str] = None
    material_detected: Optional[str] = None
    estimated_time_min: Optional[float] = None
    actual_time_min: Optional[float] = None
    human_estimate_min: Optional[float] = None
    confidence: Optional[str] = None
    created_at: Optional[datetime] = None


class TimeVisionActualTimeUpdate(BaseModel):
    """Update actual time after manufacturing"""
    actual_time_min: float = Field(gt=0, lt=10000)
    actual_notes: Optional[str] = Field(None, max_length=2000)
    version: int = Field(ge=0)
