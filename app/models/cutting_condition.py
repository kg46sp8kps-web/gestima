"""GESTIMA - CuttingCondition model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
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

    material_group: str = Field(..., max_length=50, description="Kód skupiny materiálu")
    material_name: Optional[str] = Field(None, max_length=200)
    operation_type: str = Field(..., max_length=50, description="Typ operace (turning, milling, drilling)")
    operation: str = Field(..., max_length=50, description="Operace (hrubovani, dokoncovani)")
    mode: str = Field(..., max_length=10, description="Režim (low, mid, high)")
    Vc: Optional[float] = Field(None, gt=0, description="Řezná rychlost (m/min)")
    f: float = Field(..., gt=0, description="Posuv (mm/ot nebo mm/zub)")
    Ap: Optional[float] = Field(None, gt=0, description="Hloubka řezu (mm)")
    notes: Optional[str] = Field(None, max_length=1000)


class CuttingConditionCreate(CuttingConditionBase):
    """Schema for creating cutting condition"""
    pass


class CuttingConditionUpdate(BaseModel):
    """Schema for updating cutting condition"""
    material_group: Optional[str] = Field(None, max_length=50)
    material_name: Optional[str] = Field(None, max_length=200)
    operation_type: Optional[str] = Field(None, max_length=50)
    operation: Optional[str] = Field(None, max_length=50)
    mode: Optional[str] = Field(None, max_length=10)
    Vc: Optional[float] = Field(None, gt=0)
    f: Optional[float] = Field(None, gt=0)
    Ap: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=1000)
    version: int  # Optimistic locking (ADR-008)


class CuttingConditionResponse(CuttingConditionBase):
    """Schema for returning cutting condition"""
    id: int
    version: int
    created_at: datetime
    updated_at: datetime
