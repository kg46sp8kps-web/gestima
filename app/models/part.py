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
from app.models.enums import StockShape, PartStatus

if TYPE_CHECKING:
    from app.models.material import MaterialItemWithGroupResponse, MaterialPriceCategoryWithGroupResponse
    from app.models.drawing import Drawing


class Part(Base, AuditMixin):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(8), unique=True, nullable=False, index=True)  # 8-digit random: 10XXXXXX
    article_number = Column(String(50), nullable=False, index=True)  # Dodavatelské číslo (REQUIRED)
    name = Column(String(200), nullable=True)

    # ADR-024: Revize (v1.8.0 - MaterialInput refactor)
    revision = Column(String(2), default="A", nullable=False)  # Interní revize (A-Z)
    customer_revision = Column(String(50), nullable=True)      # Zákaznická revize (zobrazená na výkresu)
    status = Column(String(20), default="active", nullable=False)  # Lifecycle status (validated by Pydantic)

    # Rozměry dílu (ne polotovaru!)
    length = Column(Float, default=0.0)  # mm - délka obráběné části

    notes = Column(String(500), default="")
    # DEPRECATED: drawing_path - use drawings relationship (multiple drawings support)
    # Kept for backwards compatibility during migration period
    # Will be removed after migration to drawings table
    drawing_path = Column(String(500), nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    material_inputs = relationship("MaterialInput", back_populates="part", cascade="all, delete-orphan", order_by="MaterialInput.seq")  # ADR-024
    operations = relationship("Operation", back_populates="part", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="part", cascade="all, delete-orphan")
    batch_sets = relationship("BatchSet", back_populates="part")  # ADR-022: Sady cen
    drawings = relationship(
        "Drawing",
        back_populates="part",
        cascade="all, delete-orphan",
        order_by="Drawing.is_primary.desc(), Drawing.created_at.desc()"
    )

    @property
    def primary_drawing_path(self) -> Optional[str]:
        """
        Computed property for backwards compatibility.
        Returns file_path of primary drawing or None.

        DEPRECATED: Use drawings relationship directly.
        This property will be removed after full migration.
        """
        for drawing in self.drawings:
            if drawing.is_primary and drawing.deleted_at is None:
                return drawing.file_path
        return None


class PartBase(BaseModel):
    part_number: str = Field(..., min_length=8, max_length=8, description="Číslo dílu (unikátní, 8-digit)")
    article_number: str = Field(..., max_length=50, description="Dodavatelské číslo (REQUIRED)")
    drawing_path: Optional[str] = Field(None, max_length=500, description="Cesta k PDF výkresu")
    name: str = Field("", max_length=200, description="Název dílu")
    revision: str = Field("A", min_length=1, max_length=2, pattern=r"^[A-Z]{1,2}$", description="Interní revize (A-Z)")
    customer_revision: Optional[str] = Field(None, max_length=50, description="Zákaznická revize")
    status: PartStatus = Field(PartStatus.DRAFT, description="Status dílu")
    length: float = Field(0.0, ge=0, description="Délka obráběné části v mm")
    notes: str = Field("", max_length=500, description="Poznámky")


class PartCreate(BaseModel):
    """Create new part - simplified (part_number auto-generated 10XXXXXX)"""
    article_number: str = Field(..., max_length=50, description="Dodavatelské číslo (REQUIRED)")
    drawing_path: Optional[str] = Field(None, max_length=500, description="Cesta k výkresu (deprecated, use temp_drawing_id)")
    temp_drawing_id: Optional[str] = Field(None, description="UUID temp file to move to permanent storage")
    name: str = Field(..., max_length=200, description="Název dílu (REQUIRED)")
    customer_revision: Optional[str] = Field(None, max_length=50, description="Zákaznická revize")
    notes: Optional[str] = Field(None, max_length=500, description="Poznámky")


class PartUpdate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=8, max_length=8)
    article_number: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    revision: Optional[str] = Field(None, min_length=1, max_length=2, pattern=r"^[A-Z]{1,2}$")
    customer_revision: Optional[str] = Field(None, max_length=50)
    status: Optional[PartStatus] = None
    length: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)
    version: int  # Optimistic locking (ADR-008)


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


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
