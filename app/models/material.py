"""GESTIMA - Material model"""

from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float

from app.database import Base, AuditMixin


class MaterialDB(Base, AuditMixin):
    """SQLAlchemy model for material groups"""
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    
    # Physical properties
    density = Column(Float)  # kg/dm³
    
    # Economics
    price_per_kg = Column(Float)
    
    # UI
    color = Column(String(20), nullable=True)  # Hex color for charts
    
    notes = Column(String(1000), nullable=True)


class MaterialBase(BaseModel):
    """Pydantic schema for Material"""
    model_config = ConfigDict(from_attributes=True)
    
    code: str
    name: str
    density: float
    price_per_kg: float
    color: Optional[str] = None
    notes: Optional[str] = None


class MaterialCreate(MaterialBase):
    """Schema for creating material"""
    pass


class MaterialResponse(MaterialBase):
    """Schema for returning material"""
    id: int
