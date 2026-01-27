"""GESTIMA - Part model"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockShape

if TYPE_CHECKING:
    from app.models.material import MaterialItemWithGroupResponse, MaterialPriceCategoryWithGroupResponse


class Part(Base, AuditMixin):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(7), unique=True, nullable=False, index=True)  # 7-digit random: 1XXXXXX
    article_number = Column(String(50), nullable=True, index=True)  # Dodavatelské číslo
    name = Column(String(200), nullable=True)

    # Material hierarchy (ADR-011: Two-Tier Model)
    # Migration 2026-01-26: Part nyní odkazuje na MaterialPriceCategory (pro cenu podle množství)
    # MaterialItem zůstává pro budoucnost (specifické polotovary s normou + rozměrem)
    material_item_id = Column(Integer, ForeignKey("material_items.id"), nullable=True)  # Future: norma + rozměr
    price_category_id = Column(Integer, ForeignKey("material_price_categories.id"), nullable=True)  # Cenová kategorie

    # Geometrie polotovaru (editovatelné, inicializováno z MaterialItem)
    stock_shape = Column(Enum(StockShape), nullable=True)  # Migration 2026-01-26: Typ polotovaru
    stock_diameter = Column(Float, nullable=True)        # mm - pro tyče, trubky
    stock_length = Column(Float, nullable=True)          # mm - délka polotovaru
    stock_width = Column(Float, nullable=True)           # mm - pro ploché, plechy
    stock_height = Column(Float, nullable=True)          # mm - pro ploché, plechy
    stock_wall_thickness = Column(Float, nullable=True)  # mm - pro trubky

    # Rozměry dílu (ne polotovaru!)
    length = Column(Float, default=0.0)  # mm - délka obráběné části

    notes = Column(String(500), default="")
    drawing_path = Column(String(500), nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    material_item = relationship("MaterialItem", back_populates="parts")
    price_category = relationship("MaterialPriceCategory", foreign_keys=[price_category_id])
    operations = relationship("Operation", back_populates="part", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="part", cascade="all, delete-orphan")


class PartBase(BaseModel):
    part_number: str = Field(..., min_length=7, max_length=7, description="Číslo dílu (unikátní, 7-digit)")
    article_number: Optional[str] = Field(None, max_length=50, description="Dodavatelské číslo")
    name: str = Field("", max_length=200, description="Název dílu")
    material_item_id: Optional[int] = Field(None, gt=0, description="ID materiálové položky (future)")
    price_category_id: Optional[int] = Field(None, gt=0, description="ID cenové kategorie")
    length: float = Field(0.0, ge=0, description="Délka obráběné části v mm")
    notes: str = Field("", max_length=500, description="Poznámky")
    # Geometrie polotovaru
    stock_shape: Optional[StockShape] = Field(None, description="Typ polotovaru (tyč, plech...)")
    stock_diameter: Optional[float] = Field(None, ge=0, description="Průměr polotovaru v mm")
    stock_length: Optional[float] = Field(None, ge=0, description="Délka polotovaru v mm")
    stock_width: Optional[float] = Field(None, ge=0, description="Šířka polotovaru v mm")
    stock_height: Optional[float] = Field(None, ge=0, description="Výška polotovaru v mm")
    stock_wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm")


class PartCreate(BaseModel):
    """Create new part - part_number is auto-generated if not provided"""
    part_number: Optional[str] = Field(None, min_length=7, max_length=7, description="Číslo dílu (auto-generated)")
    article_number: Optional[str] = Field(None, max_length=50, description="Dodavatelské číslo")
    name: str = Field("", max_length=200, description="Název dílu")
    material_item_id: Optional[int] = Field(None, gt=0, description="ID materiálové položky (future)")
    price_category_id: Optional[int] = Field(None, gt=0, description="ID cenové kategorie")
    length: float = Field(0.0, ge=0, description="Délka obráběné části v mm")
    notes: str = Field("", max_length=500, description="Poznámky")
    # Geometrie polotovaru
    stock_shape: Optional[StockShape] = Field(None, description="Typ polotovaru (tyč, plech...)")
    stock_diameter: Optional[float] = Field(None, ge=0, description="Průměr polotovaru v mm")
    stock_length: Optional[float] = Field(None, ge=0, description="Délka polotovaru v mm")
    stock_width: Optional[float] = Field(None, ge=0, description="Šířka polotovaru v mm")
    stock_height: Optional[float] = Field(None, ge=0, description="Výška polotovaru v mm")
    stock_wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm")


class PartUpdate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=7, max_length=7)
    article_number: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    material_item_id: Optional[int] = Field(None, gt=0)
    price_category_id: Optional[int] = Field(None, gt=0)
    length: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)
    # Geometrie polotovaru
    stock_shape: Optional[StockShape] = Field(None)
    stock_diameter: Optional[float] = Field(None, ge=0)
    stock_length: Optional[float] = Field(None, ge=0)
    stock_width: Optional[float] = Field(None, ge=0)
    stock_height: Optional[float] = Field(None, ge=0)
    stock_wall_thickness: Optional[float] = Field(None, ge=0)
    version: int  # Optimistic locking (ADR-008)


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class PartFullResponse(PartResponse):
    """Part s eager-loaded MaterialPriceCategory + MaterialGroup"""
    material_item: Optional["MaterialItemWithGroupResponse"] = None  # Future: specifické polotovary
    price_category: Optional["MaterialPriceCategoryWithGroupResponse"] = None  # Migration 2026-01-26


class StockCostResponse(BaseModel):
    """Výpočet ceny polotovaru (z backendu)"""
    volume_mm3: float = 0
    weight_kg: float = 0
    price_per_kg: float = 0
    cost: float = 0
    density: float = 0
