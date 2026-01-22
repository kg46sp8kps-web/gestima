"""GESTIMA - Batch model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, DateTime
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
    
    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version
    
    part = relationship("Part", back_populates="batches")


class BatchBase(BaseModel):
    quantity: int = 1
    is_default: bool = False


class BatchCreate(BatchBase):
    part_id: int


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
    created_at: datetime
    updated_at: datetime
