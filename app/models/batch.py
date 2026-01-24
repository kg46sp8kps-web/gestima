"""GESTIMA - Batch model"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class Batch(Base, AuditMixin):
    __tablename__ = "batches"
    
    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, default=1)
    is_default = Column(Boolean, default=False)
    
    unit_time_min = Column(Float, default=0.0)
    
    material_cost = Column(Float, default=0.0)
    machining_cost = Column(Float, default=0.0)
    setup_cost = Column(Float, default=0.0)
    coop_cost = Column(Float, default=0.0)
    
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # Freeze metadata (ADR-012: Minimal Snapshot)
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    frozen_at = Column(DateTime, nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Snapshot (minimal - pouze ceny a metadata)
    snapshot_data = Column(JSON, nullable=True)

    # Redundantní sloupce pro reporty (hybrid approach)
    unit_price_frozen = Column(Float, nullable=True, index=True)
    total_price_frozen = Column(Float, nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    part = relationship("Part", back_populates="batches")
    frozen_by = relationship("User")


class BatchBase(BaseModel):
    quantity: int = Field(1, gt=0, description="Množství kusů (musí být > 0)")
    is_default: bool = False


class BatchCreate(BatchBase):
    part_id: int = Field(..., gt=0, description="ID dílu")


class BatchResponse(BatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    unit_time_min: float
    material_cost: float
    machining_cost: float
    setup_cost: float
    coop_cost: float
    unit_cost: float
    total_cost: float
    version: int
    created_at: datetime
    updated_at: datetime

    # Freeze fields (ADR-012)
    is_frozen: bool
    frozen_at: Optional[datetime] = None
    frozen_by_id: Optional[int] = None
    snapshot_data: Optional[Dict[str, Any]] = None
    unit_price_frozen: Optional[float] = None
    total_price_frozen: Optional[float] = None
