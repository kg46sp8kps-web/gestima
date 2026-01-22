"""GESTIMA - Part model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockType, PartStatus


class Part(Base, AuditMixin):
    __tablename__ = "parts"
    
    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    
    material_name = Column(String(100), nullable=True)
    material_group = Column(String(50), nullable=False, default="konstrukcni_ocel")
    
    stock_type = Column(Enum(StockType), default=StockType.ROD)
    stock_diameter = Column(Float, default=0.0)
    stock_diameter_inner = Column(Float, default=0.0)
    stock_length = Column(Float, default=0.0)
    stock_width = Column(Float, default=0.0)  # Pro přířez (d x š x v)
    stock_height = Column(Float, default=0.0)  # Pro přířez (d x š x v)
    
    status = Column(Enum(PartStatus), default=PartStatus.DRAFT)
    notes = Column(String(500), default="")
    drawing_path = Column(String(500), nullable=True)
    
    # AuditMixin provides: created_at, updated_at, created_by, updated_by, 
    #                      deleted_at, deleted_by, version
    
    operations = relationship("Operation", back_populates="part", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="part", cascade="all, delete-orphan")


class PartBase(BaseModel):
    part_number: str
    name: str = ""
    material_name: str = ""
    material_group: str = "konstrukcni_ocel"
    stock_type: StockType = StockType.ROD
    stock_diameter: float = 0.0
    stock_diameter_inner: float = 0.0
    stock_length: float = 0.0
    stock_width: float = 0.0
    stock_height: float = 0.0
    notes: str = ""


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    part_number: Optional[str] = None
    name: Optional[str] = None
    material_name: Optional[str] = None
    material_group: Optional[str] = None
    stock_type: Optional[StockType] = None
    stock_diameter: Optional[float] = None
    stock_diameter_inner: Optional[float] = None
    stock_length: Optional[float] = None
    stock_width: Optional[float] = None
    stock_height: Optional[float] = None
    status: Optional[PartStatus] = None
    notes: Optional[str] = None


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PartStatus
    created_at: datetime
    updated_at: datetime
