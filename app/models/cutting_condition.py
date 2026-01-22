"""GESTIMA - CuttingCondition model"""

from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float

from app.database import Base, AuditMixin


class CuttingConditionDB(Base, AuditMixin):
    """SQLAlchemy model for cutting conditions"""
    __tablename__ = "cutting_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifikace
    material_group = Column(String(50), index=True)
    material_name = Column(String(200), nullable=True)
    operation_type = Column(String(50), index=True)  # turning, milling, drilling...
    operation = Column(String(50), index=True)  # hrubovani, dokoncovani...
    mode = Column(String(10), index=True)  # low, mid, high
    
    # Řezné parametry
    Vc = Column(Float)  # Řezná rychlost (m/min)
    f = Column(Float)   # Posuv (mm/ot nebo mm/zub)
    Ap = Column(Float)  # Hloubka řezu (mm)
    
    notes = Column(String(1000), nullable=True)


class CuttingConditionBase(BaseModel):
    """Pydantic schema for CuttingCondition"""
    model_config = ConfigDict(from_attributes=True)
    
    material_group: str
    material_name: Optional[str] = None
    operation_type: str
    operation: str
    mode: str
    Vc: float
    f: float
    Ap: float
    notes: Optional[str] = None


class CuttingConditionCreate(CuttingConditionBase):
    """Schema for creating cutting condition"""
    pass


class CuttingConditionResponse(CuttingConditionBase):
    """Schema for returning cutting condition"""
    id: int
