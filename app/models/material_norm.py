"""GESTIMA - MaterialNorm model (norma → MaterialGroup mapping s aliasy)"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.material import MaterialGroupResponse

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class MaterialNorm(Base, AuditMixin):
    """
    Conversion table: Material norms → MaterialGroup.

    4 fixed columns for different norm standards, each row maps to one MaterialGroup.
    When creating MaterialItem with code "D20 11109", system searches for "11109"
    across all 4 columns and auto-assigns the MaterialGroup.

    Příklady řádků:
    - W.Nr: 1.0503 | EN ISO: C45 | ČSN: 12050 | AISI: 1045 → Ocel konstrukční
    - W.Nr: 1.4301 | EN ISO: X5CrNi18-10 | ČSN: 17240 | AISI: 304 → Nerez
    - W.Nr: 1.0715 | EN ISO: 11SMnPb30 | ČSN: 11109 | AISI: - → Ocel konstrukční
    """
    __tablename__ = "material_norms"

    id = Column(Integer, primary_key=True, index=True)

    # 4 fixed columns for norm standards (nullable, case-insensitive search)
    w_nr = Column(String(50), nullable=True, index=True)        # W.Nr (Werkstoffnummer) - např. 1.0503, 1.4301
    en_iso = Column(String(50), nullable=True, index=True)      # EN ISO - např. C45, X5CrNi18-10
    csn = Column(String(50), nullable=True, index=True)         # ČSN - např. 12050, 11109
    aisi = Column(String(50), nullable=True, index=True)        # AISI - např. 1045, 304

    # FK → MaterialGroup (hustota, řezné podmínky, cena)
    material_group_id = Column(
        Integer,
        ForeignKey("material_groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Poznámka (volitelná)
    note = Column(Text, nullable=True)

    # Relationship
    material_group = relationship("MaterialGroup", back_populates="norms")

    # Index pro rychlé lookup
    __table_args__ = (
        Index('idx_material_norms_group', 'material_group_id'),
    )


# ========== PYDANTIC SCHEMAS ==========

class MaterialNormBase(BaseModel):
    w_nr: Optional[str] = Field(None, max_length=50, description="W.Nr (Werkstoffnummer) - např. 1.0503, 1.4301")
    en_iso: Optional[str] = Field(None, max_length=50, description="EN ISO - např. C45, X5CrNi18-10")
    csn: Optional[str] = Field(None, max_length=50, description="ČSN - např. 12050, 11109")
    aisi: Optional[str] = Field(None, max_length=50, description="AISI - např. 1045, 304")
    material_group_id: int = Field(..., gt=0, description="ID MaterialGroup (kategorie)")
    note: Optional[str] = Field(None, description="Poznámka")


class MaterialNormCreate(MaterialNormBase):
    pass


class MaterialNormUpdate(BaseModel):
    w_nr: Optional[str] = Field(None, max_length=50)
    en_iso: Optional[str] = Field(None, max_length=50)
    csn: Optional[str] = Field(None, max_length=50)
    aisi: Optional[str] = Field(None, max_length=50)
    material_group_id: Optional[int] = Field(None, gt=0)
    note: Optional[str] = None
    version: int  # Optimistic locking


class MaterialNormResponse(MaterialNormBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime
