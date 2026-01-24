"""GESTIMA - Material models (ADR-011: Two-Tier Hierarchy)"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockShape


class MaterialGroup(Base, AuditMixin):
    """
    Kategorie materiálu pro výpočty (hustota, řezné podmínky).
    Příklad: "Ocel automatová", "Hliník 6060", "Mosaz".
    """
    __tablename__ = "material_groups"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)    # "11xxx", "S235"
    name = Column(String(100), nullable=False)                            # "Ocel automatová"
    density = Column(Float, nullable=False)                               # kg/dm³ (pro výpočet váhy)

    # Relationships
    items = relationship("MaterialItem", back_populates="group", cascade="all, delete-orphan")
    # cutting_conditions = relationship("CuttingCondition", back_populates="material_group")  # Future


class MaterialItem(Base, AuditMixin):
    """
    Konkrétní polotovar (skladová položka).
    Příklad: "1.0715 D20 - tyč kruhová ocel".
    """
    __tablename__ = "material_items"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)    # "1.0715-D20"
    name = Column(String(200), nullable=False)                            # "1.0715 D20 - tyč kruhová ocel"

    # Geometrie polotovaru
    shape = Column(Enum(StockShape), nullable=False)                      # ROUND_BAR, SQUARE_BAR, ...
    diameter = Column(Float, nullable=True)                               # mm (pro round_bar, hexagonal_bar)
    width = Column(Float, nullable=True)                                  # mm (pro square_bar, flat_bar, plate)
    thickness = Column(Float, nullable=True)                              # mm (pro plate, flat_bar)
    wall_thickness = Column(Float, nullable=True)                         # mm (pro tube - tloušťka stěny)

    # Ekonomika (LIVE data)
    price_per_kg = Column(Float, nullable=False)                          # Kč/kg (aktuální nákupní cena)
    supplier = Column(String(100), nullable=True)                         # Dodavatel
    stock_available = Column(Float, nullable=True, default=0.0)           # kg (dostupné skladem)

    # Vazba k nadřazené skupině
    material_group_id = Column(Integer, ForeignKey("material_groups.id"), nullable=False)
    group = relationship("MaterialGroup", back_populates="items")

    # Vztah k dílům
    parts = relationship("Part", back_populates="material_item")


# ========== PYDANTIC SCHEMAS ==========

class MaterialGroupBase(BaseModel):
    code: str = Field(..., max_length=20, description="Kód skupiny (např. 11xxx, S235)")
    name: str = Field(..., max_length=100, description="Název skupiny")
    density: float = Field(..., gt=0, description="Hustota v kg/dm³")


class MaterialGroupCreate(MaterialGroupBase):
    pass


class MaterialGroupUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    density: Optional[float] = Field(None, gt=0)
    version: int  # Optimistic locking


class MaterialGroupResponse(MaterialGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class MaterialItemBase(BaseModel):
    code: str = Field(..., max_length=50, description="Kód položky (např. 1.0715-D20)")
    name: str = Field(..., max_length=200, description="Název položky")
    shape: StockShape = Field(..., description="Tvar polotovaru")
    diameter: Optional[float] = Field(None, ge=0, description="Průměr v mm (pro round_bar)")
    width: Optional[float] = Field(None, ge=0, description="Šířka v mm (pro square/flat/plate)")
    thickness: Optional[float] = Field(None, ge=0, description="Tloušťka v mm (pro plate)")
    wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm (pro tube)")
    price_per_kg: float = Field(..., gt=0, description="Cena za kg v Kč")
    supplier: Optional[str] = Field(None, max_length=100, description="Dodavatel")
    stock_available: Optional[float] = Field(0.0, ge=0, description="Dostupné skladem (kg)")
    material_group_id: int = Field(..., description="ID nadřazené skupiny")


class MaterialItemCreate(MaterialItemBase):
    pass


class MaterialItemUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    shape: Optional[StockShape] = None
    diameter: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    thickness: Optional[float] = Field(None, ge=0)
    wall_thickness: Optional[float] = Field(None, ge=0)
    price_per_kg: Optional[float] = Field(None, gt=0)
    supplier: Optional[str] = Field(None, max_length=100)
    stock_available: Optional[float] = Field(None, ge=0)
    material_group_id: Optional[int] = None
    version: int  # Optimistic locking


class MaterialItemResponse(MaterialItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class MaterialItemWithGroupResponse(MaterialItemResponse):
    """MaterialItem s eager-loaded group informací"""
    group: MaterialGroupResponse
