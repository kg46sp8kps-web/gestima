"""GESTIMA - Quote and QuoteItem models

Quotations workflow (ADR-VIS-002):
- DRAFT: Editable
- SENT: Read-only, snapshot created
- APPROVED/REJECTED: Final states

Design principles:
- Denormalized fields (part_number, part_name) for snapshot integrity
- Auto-load pricing from latest frozen batch_set
- Edit lock after SENT (must clone to edit)
- Snapshot on status change to SENT
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import QuoteStatus

if TYPE_CHECKING:
    from app.models.partner import Partner
    from app.models.part import Part


class Quote(Base, AuditMixin):
    """Quote model - customer quotations with workflow"""
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    quote_number = Column(String(8), unique=True, nullable=False, index=True)  # 85XXXXXX
    partner_id = Column(Integer, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True)

    # Metadata
    title = Column(String(200), nullable=False, default="")
    description = Column(Text, nullable=True)
    valid_until = Column(DateTime, nullable=True, index=True)

    # Workflow
    status = Column(String(20), default=QuoteStatus.DRAFT.value, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # Pricing (recalculated from items)
    subtotal = Column(Float, default=0.0, nullable=False)  # Sum of line_totals
    discount_percent = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    tax_percent = Column(Float, default=21.0, nullable=False)  # Czech DPH
    tax_amount = Column(Float, default=0.0, nullable=False)
    total = Column(Float, default=0.0, nullable=False)

    # Snapshot (JSON) - created when status changes to SENT
    snapshot_data = Column(JSON, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


class QuoteItem(Base, AuditMixin):
    """Quote item - individual line items with denormalized fields"""
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True, index=True)

    # Denormalized fields (for snapshot integrity)
    part_number = Column(String(8), nullable=True, index=True)
    part_name = Column(String(200), nullable=True)

    # Pricing (auto-loaded from latest frozen batch_set)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    line_total = Column(Float, default=0.0, nullable=False)  # quantity * unit_price

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    quote = relationship("Quote", back_populates="items")
    part = relationship("Part")

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


# =============================================================================
# Pydantic Schemas
# =============================================================================

class QuoteItemBase(BaseModel):
    part_id: Optional[int] = Field(None, description="ID dílu")
    part_number: Optional[str] = Field(None, max_length=8, description="Číslo dílu (denormalizováno)")
    part_name: Optional[str] = Field(None, max_length=200, description="Název dílu (denormalizováno)")
    quantity: int = Field(1, gt=0, description="Množství")
    unit_price: float = Field(0.0, ge=0.0, description="Jednotková cena")
    line_total: float = Field(0.0, ge=0.0, description="Celkem za řádek")
    notes: Optional[str] = Field(None, description="Poznámky")


class QuoteItemCreate(BaseModel):
    """Create quote item - part_id required, pricing auto-loaded from frozen batch"""
    part_id: int = Field(..., gt=0, description="ID dílu")
    quantity: int = Field(1, gt=0, description="Množství")
    notes: Optional[str] = Field(None, description="Poznámky")


class QuoteItemUpdate(BaseModel):
    """Update quote item - only quantity and notes editable"""
    quantity: Optional[int] = Field(None, gt=0, description="Množství")
    unit_price: Optional[float] = Field(None, ge=0.0, description="Jednotková cena")
    notes: Optional[str] = Field(None, description="Poznámky")
    version: int = Field(..., description="Optimistic locking")


class QuoteItemResponse(QuoteItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    version: int
    created_at: datetime
    updated_at: datetime


class QuoteBase(BaseModel):
    quote_number: str = Field(..., min_length=8, max_length=8, description="Číslo nabídky")
    partner_id: Optional[int] = Field(None, description="ID partnera (zákazníka)")
    title: str = Field("", max_length=200, description="Název nabídky")
    description: Optional[str] = Field(None, description="Popis")
    valid_until: Optional[datetime] = Field(None, description="Platnost do")
    status: str = Field(QuoteStatus.DRAFT.value, description="Stav nabídky")
    subtotal: float = Field(0.0, ge=0.0, description="Mezisoučet")
    discount_percent: float = Field(0.0, ge=0.0, le=100.0, description="Sleva %")
    discount_amount: float = Field(0.0, ge=0.0, description="Sleva částka")
    tax_percent: float = Field(21.0, ge=0.0, le=100.0, description="DPH %")
    tax_amount: float = Field(0.0, ge=0.0, description="DPH částka")
    total: float = Field(0.0, ge=0.0, description="Celkem")
    notes: Optional[str] = Field(None, description="Poznámky")


class QuoteCreate(BaseModel):
    """Create new quote - quote_number auto-generated"""
    partner_id: int = Field(..., gt=0, description="ID partnera (zákazníka)")
    title: str = Field("", max_length=200, description="Název nabídky")
    description: Optional[str] = Field(None, description="Popis")
    valid_until: Optional[datetime] = Field(None, description="Platnost do")
    discount_percent: float = Field(0.0, ge=0.0, le=100.0, description="Sleva %")
    tax_percent: float = Field(21.0, ge=0.0, le=100.0, description="DPH %")
    notes: Optional[str] = Field(None, description="Poznámky")


class QuoteUpdate(BaseModel):
    """Update quote - only allowed in DRAFT status"""
    title: Optional[str] = Field(None, max_length=200, description="Název nabídky")
    description: Optional[str] = Field(None, description="Popis")
    valid_until: Optional[datetime] = Field(None, description="Platnost do")
    discount_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Sleva %")
    tax_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="DPH %")
    notes: Optional[str] = Field(None, description="Poznámky")
    version: int = Field(..., description="Optimistic locking")


class QuoteResponse(QuoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sent_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    snapshot_data: Optional[dict] = None
    version: int
    created_at: datetime
    updated_at: datetime


class QuoteWithItemsResponse(QuoteResponse):
    """Quote with nested items for detail view"""
    items: List[QuoteItemResponse] = []


class QuoteListResponse(BaseModel):
    """Lightweight quote for list views"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_number: str
    partner_id: Optional[int]
    title: str
    status: str
    total: float
    valid_until: Optional[datetime] = None
    created_at: datetime
    version: int
