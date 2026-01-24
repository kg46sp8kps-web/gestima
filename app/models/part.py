"""GESTIMA - Part model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class Part(Base, AuditMixin):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)

    # Material hierarchy (ADR-011: Two-Tier Model)
    # BREAKING CHANGE: stock_type, material_group, stock_* fields removed
    # Geometrie polotovaru je nyní v MaterialItem
    material_item_id = Column(Integer, ForeignKey("material_items.id"), nullable=False)

    # Rozměry dílu (ne polotovaru!)
    length = Column(Float, default=0.0)  # mm - délka obráběné části

    notes = Column(String(500), default="")
    drawing_path = Column(String(500), nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    material_item = relationship("MaterialItem", back_populates="parts")
    operations = relationship("Operation", back_populates="part", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="part", cascade="all, delete-orphan")


class PartBase(BaseModel):
    part_number: str = Field(..., min_length=1, max_length=50, description="Číslo dílu (unikátní)")
    name: str = Field("", max_length=200, description="Název dílu")
    material_item_id: int = Field(..., gt=0, description="ID materiálové položky")
    length: float = Field(0.0, ge=0, description="Délka obráběné části v mm")
    notes: str = Field("", max_length=500, description="Poznámky")


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    material_item_id: Optional[int] = Field(None, gt=0)
    length: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)
    version: int  # Optimistic locking (ADR-008)


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime
