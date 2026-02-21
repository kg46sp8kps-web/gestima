"""GESTIMA - Part model

ADR-024: MaterialInput refactor (v1.8.0)
- Removed material fields (moved to MaterialInput table)
- Added revision fields (revision, customer_revision, status)
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockShape, PartStatus, PartSource

if TYPE_CHECKING:
    from app.models.material import MaterialItemWithGroupResponse, MaterialPriceCategoryWithGroupResponse
    from app.models.file_record import FileRecord


class Part(Base, AuditMixin):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(8), unique=True, nullable=False, index=True)  # 8-digit random: 10XXXXXX
    article_number = Column(String(50), nullable=True, index=True)  # Dodavatelské číslo (partial unique index via migration ab002)
    name = Column(String(200), nullable=True)

    # ADR-024: Revize (v1.8.0 - MaterialInput refactor)
    revision = Column(String(2), nullable=True)  # Interní revize (A-Z) - volitelné
    customer_revision = Column(String(50), nullable=True)      # Zákaznická revize (zobrazená na výkresu)
    drawing_number = Column(String(50), nullable=True)         # Číslo výkresu (zobrazené v hlavičce)
    status = Column(String(20), default="active", nullable=False)  # Lifecycle status (validated by Pydantic)
    source = Column(String(20), default="manual", nullable=False)  # Původ dílu: manual, infor_import, quote_request
    # Rozměry dílu (ne polotovaru!)
    length = Column(Float, default=0.0)  # mm - délka obráběné části

    notes = Column(String(500), default="")
    # DEPRECATED: drawing_path - use drawings relationship (multiple drawings support)
    # Kept for backwards compatibility during migration period
    # Will be removed after migration to drawings table
    drawing_path = Column(String(500), nullable=True)

    # ADR-044 Phase 2b: Primary drawing reference (FileRecord)
    file_id = Column(Integer, ForeignKey("file_records.id", ondelete="SET NULL"), nullable=True, index=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    material_inputs = relationship("MaterialInput", back_populates="part", cascade="all, delete-orphan", order_by="MaterialInput.seq")  # ADR-024
    operations = relationship("Operation", back_populates="part", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="part", cascade="all, delete-orphan")
    batch_sets = relationship("BatchSet", back_populates="part")  # ADR-022: Sady cen
    file_record = relationship("FileRecord", foreign_keys=[file_id])
    production_records = relationship(
        "ProductionRecord",
        back_populates="part",
        cascade="all, delete-orphan",
        order_by="ProductionRecord.production_date.desc()"
    )


class PartBase(BaseModel):
    part_number: str = Field(..., min_length=8, max_length=8, description="Číslo dílu (unikátní, 8-digit)")
    article_number: Optional[str] = Field(None, max_length=50, description="Dodavatelské číslo")
    drawing_path: Optional[str] = Field(None, max_length=500, description="Cesta k PDF výkresu")
    name: Optional[str] = Field(None, max_length=200, description="Název dílu")
    revision: Optional[str] = Field(None, min_length=1, max_length=2, pattern=r"^[A-Z]{1,2}$", description="Interní revize (A-Z) - volitelné")
    customer_revision: Optional[str] = Field(None, max_length=50, description="Zákaznická revize")
    drawing_number: Optional[str] = Field(None, max_length=50, description="Číslo výkresu")
    status: PartStatus = Field(PartStatus.ACTIVE, description="Status dílu (default: active)")
    source: PartSource = Field(PartSource.MANUAL, description="Původ dílu (manual, infor_import, quote_request)")
    length: float = Field(0.0, ge=0, description="Délka obráběné části v mm")
    notes: Optional[str] = Field(None, max_length=500, description="Poznámky")


class PartCreate(BaseModel):
    """Create new part - simplified (part_number auto-generated 10XXXXXX)"""
    article_number: str = Field("", max_length=50, description="Dodavatelské číslo")
    name: str = Field("", max_length=200, description="Název dílu")
    customer_revision: Optional[str] = Field(None, max_length=50, description="Zákaznická revize")
    drawing_number: Optional[str] = Field(None, max_length=50, description="Číslo výkresu")
    notes: Optional[str] = Field(None, max_length=500, description="Poznámky")


class PartUpdate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=8, max_length=8)
    article_number: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    revision: Optional[str] = Field(None, min_length=1, max_length=2, pattern=r"^[A-Z]{1,2}$")
    customer_revision: Optional[str] = Field(None, max_length=50)
    drawing_number: Optional[str] = Field(None, max_length=50)
    status: Optional[PartStatus] = None
    length: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)
    version: int  # Optimistic locking (ADR-008)


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: Optional[int] = Field(None, description="Primary drawing FileRecord ID")
    version: int
    created_at: datetime
    updated_at: datetime
    created_by_name: Optional[str] = Field(None, description="Username of user who created the part")


class PartFullResponse(PartResponse):
    """Part s eager-loaded relationships"""
    pass  # MaterialInputs added via separate endpoint


class StockCostResponse(BaseModel):
    """Výpočet ceny polotovaru (z backendu) - DEPRECATED, use MaterialInput"""
    volume_mm3: float = 0
    weight_kg: float = 0
    price_per_kg: float = 0
    cost: float = 0
    density: float = 0
