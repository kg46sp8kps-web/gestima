"""GESTIMA - MaterialInput model

Material inputs for Part (nezávislý na operacích).

Podporuje:
- Díl s materiálem ale bez operací (nakupovaný díl)
- Díl s operacemi ale bez materiálu (montáž)
- M:N vztah materiál ↔ operace (jedna tyč na více řezů)
- Přeřazení operací (seq změna) = pouze update reference

ADR-024: MaterialInput refactor (v1.8.0)
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Table, Index
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockShape

if TYPE_CHECKING:
    from app.models.part import Part
    from app.models.operation import Operation
    from app.models.material import MaterialPriceCategory, MaterialItem


# ═══════════════════════════════════════════════════════════════
# ASSOCIATION TABLE (M:N)
# ═══════════════════════════════════════════════════════════════

material_operation_link = Table(
    'material_operation_link',
    Base.metadata,
    Column('material_input_id', Integer, ForeignKey('material_inputs.id', ondelete='CASCADE'), primary_key=True),
    Column('operation_id', Integer, ForeignKey('operations.id', ondelete='CASCADE'), primary_key=True),
    Column('consumed_quantity', Integer, nullable=True),  # Kolik z tohoto materiálu se spotřebovává v TÉTO operaci
    Index('ix_mat_op_link_material', 'material_input_id'),
    Index('ix_mat_op_link_operation', 'operation_id'),
)


# ═══════════════════════════════════════════════════════════════
# MATERIAL INPUT MODEL
# ═══════════════════════════════════════════════════════════════

class MaterialInput(Base, AuditMixin):
    """
    Materiálový vstup pro Part (nezávislý na operacích).

    Use cases:
    - Díl s materiálem ale bez operací (nakupovaný díl)
    - Díl s operacemi ale bez materiálu (montáž)
    - M:N vztah materiál ↔ operace (jedna tyč na více řezů)
    - Přeřazení operací (seq změna) = pouze update reference
    """
    __tablename__ = "material_inputs"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Pořadí (pro UI zobrazení)
    seq = Column(Integer, nullable=False, default=0)

    # ─────────────────────────────────────────────────────────────
    # CENOVÁ KATEGORIE (povinné)
    # ─────────────────────────────────────────────────────────────
    price_category_id = Column(
        Integer,
        ForeignKey("material_price_categories.id", ondelete="SET NULL"),
        nullable=False
    )

    # ─────────────────────────────────────────────────────────────
    # KONKRÉTNÍ NORMA (volitelné - může být "generický" materiál)
    # ─────────────────────────────────────────────────────────────
    material_item_id = Column(
        Integer,
        ForeignKey("material_items.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─────────────────────────────────────────────────────────────
    # TVAR POLOTOVARU (povinné)
    # ─────────────────────────────────────────────────────────────
    stock_shape = Column(Enum(StockShape), nullable=False)

    # Rozměry (dynamické podle stock_shape)
    stock_diameter = Column(Float, nullable=True)
    stock_length = Column(Float, nullable=True)
    stock_width = Column(Float, nullable=True)
    stock_height = Column(Float, nullable=True)
    stock_wall_thickness = Column(Float, nullable=True)

    # ─────────────────────────────────────────────────────────────
    # MNOŽSTVÍ (kolik kusů tohoto materiálu na 1 díl)
    # ─────────────────────────────────────────────────────────────
    quantity = Column(Integer, default=1, nullable=False)

    # ─────────────────────────────────────────────────────────────
    # POZNÁMKA
    # ─────────────────────────────────────────────────────────────
    notes = Column(String(500), nullable=True)

    # ─────────────────────────────────────────────────────────────
    # RELATIONSHIPS
    # ─────────────────────────────────────────────────────────────
    part = relationship("Part", back_populates="material_inputs")
    price_category = relationship("MaterialPriceCategory")
    material_item = relationship("MaterialItem")

    # M:N relationship přes association table
    operations = relationship(
        "Operation",
        secondary=material_operation_link,
        back_populates="material_inputs"
    )

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


# ═══════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════

class MaterialInputBase(BaseModel):
    """Base schema pro MaterialInput"""
    seq: int = Field(0, ge=0, description="Pořadí materiálu")
    price_category_id: int = Field(..., gt=0, description="ID cenové kategorie")
    material_item_id: Optional[int] = Field(None, gt=0, description="ID materiálové položky (volitelné)")
    stock_shape: StockShape = Field(..., description="Tvar polotovaru")
    stock_diameter: Optional[float] = Field(None, ge=0, description="Průměr polotovaru v mm")
    stock_length: Optional[float] = Field(None, ge=0, description="Délka polotovaru v mm")
    stock_width: Optional[float] = Field(None, ge=0, description="Šířka polotovaru v mm")
    stock_height: Optional[float] = Field(None, ge=0, description="Výška polotovaru v mm")
    stock_wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm")
    quantity: int = Field(1, gt=0, description="Množství kusů materiálu na 1 díl")
    notes: Optional[str] = Field(None, max_length=500, description="Poznámky")


class MaterialInputCreate(MaterialInputBase):
    """Create new material input"""
    part_id: int = Field(..., gt=0, description="ID dílu")


class MaterialInputUpdate(BaseModel):
    """Update material input"""
    seq: Optional[int] = Field(None, ge=0)
    price_category_id: Optional[int] = Field(None, gt=0)
    material_item_id: Optional[int] = Field(None, gt=0)
    stock_shape: Optional[StockShape] = None
    stock_diameter: Optional[float] = Field(None, ge=0)
    stock_length: Optional[float] = Field(None, ge=0)
    stock_width: Optional[float] = Field(None, ge=0)
    stock_height: Optional[float] = Field(None, ge=0)
    stock_wall_thickness: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=500)
    version: int = Field(..., description="Optimistic locking (ADR-008)")


class MaterialInputResponse(MaterialInputBase):
    """Response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    version: int
    created_at: datetime
    updated_at: datetime


class OperationSummary(BaseModel):
    """Lightweight Operation summary for MaterialInput response (avoids circular import)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    seq: int
    name: str
    type: str


class MaterialInputWithOperationsResponse(MaterialInputResponse):
    """MaterialInput s eager-loaded operations"""
    operations: List[OperationSummary] = []
    weight_kg: Optional[float] = Field(None, description="Hmotnost za kus v kg (kalkulováno)")
    cost_per_piece: Optional[float] = Field(None, description="Cena za kus v Kč (kalkulováno)")
    price_per_kg: Optional[float] = Field(None, description="Cena za kg z tieru (kalkulováno)")


# ═══════════════════════════════════════════════════════════════
# LINK REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════

class MaterialOperationLinkRequest(BaseModel):
    """Request pro link/unlink materiál ↔ operace"""
    consumed_quantity: Optional[int] = Field(None, gt=0, description="Kolik z materiálu se spotřebovává v této operaci")


