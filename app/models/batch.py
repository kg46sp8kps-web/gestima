"""GESTIMA - Batch model"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class Batch(Base, AuditMixin):
    __tablename__ = "batches"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(8), unique=True, nullable=False, index=True)  # 8-digit random: 30XXXXXX
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, default=1, nullable=False)
    is_default = Column(Boolean, default=False)
    
    unit_time_min = Column(Float, default=0.0)
    
    material_cost = Column(Float, default=0.0)
    machining_cost = Column(Float, default=0.0)
    setup_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)  # Režie (ADR-016)
    margin_cost = Column(Float, default=0.0)    # Marže (ADR-016)
    coop_cost = Column(Float, default=0.0)

    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # Material snapshot fields (ADR-017: Hybrid material snapshot)
    material_weight_kg = Column(Float, nullable=True)
    material_price_per_kg = Column(Float, nullable=True)

    # Freeze metadata (ADR-012: Minimal Snapshot)
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    frozen_at = Column(DateTime, nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Snapshot (minimal - pouze ceny a metadata)
    snapshot_data = Column(JSON, nullable=True)

    # Redundantní sloupce pro reporty (hybrid approach)
    unit_price_frozen = Column(Float, nullable=True, index=True)
    total_price_frozen = Column(Float, nullable=True)

    # BatchSet FK (ADR-022: Sady cen)
    batch_set_id = Column(Integer, ForeignKey("batch_sets.id", ondelete="CASCADE"), nullable=True, index=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    part = relationship("Part", back_populates="batches")
    batch_set = relationship("BatchSet", back_populates="batches")
    frozen_by = relationship("User")


class BatchBase(BaseModel):
    batch_number: str = Field(..., min_length=8, max_length=8, description="Číslo šarže (8-digit)")
    quantity: int = Field(1, gt=0, description="Množství kusů (musí být > 0)")
    is_default: bool = False


class BatchCreate(BaseModel):
    """Create new batch - batch_number is auto-generated if not provided"""
    batch_number: Optional[str] = Field(None, min_length=8, max_length=8, description="Číslo šarže (auto-generated)")
    part_id: int = Field(..., gt=0, description="ID dílu")
    quantity: int = Field(1, gt=0, description="Množství kusů (musí být > 0)")
    is_default: bool = False


class BatchUpdate(BaseModel):
    """Schema for updating batch"""
    batch_number: Optional[str] = Field(None, min_length=8, max_length=8)
    quantity: Optional[int] = Field(None, gt=0, description="Množství kusů")
    is_default: Optional[bool] = None
    version: int  # Optimistic locking (ADR-008)


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_number: str
    part_id: int
    batch_set_id: Optional[int] = None  # ADR-022
    quantity: int
    is_default: bool
    unit_time_min: float
    material_cost: float
    machining_cost: float
    setup_cost: float
    overhead_cost: float  # ADR-016
    margin_cost: float    # ADR-016
    coop_cost: float
    unit_cost: float
    total_cost: float
    version: int
    created_at: datetime
    updated_at: datetime

    # Material snapshot fields (ADR-017)
    material_weight_kg: Optional[float] = None
    material_price_per_kg: Optional[float] = None

    # Freeze fields (ADR-012)
    is_frozen: bool
    frozen_at: Optional[datetime] = None
    frozen_by_id: Optional[int] = None
    snapshot_data: Optional[Dict[str, Any]] = None
    unit_price_frozen: Optional[float] = None
    total_price_frozen: Optional[float] = None

    # Cost percentages (ADR-016: Výpočty POUZE Python)
    @computed_field
    @property
    def material_percent(self) -> float:
        """Podíl materiálu v %"""
        if self.unit_cost > 0:
            return round((self.material_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def machining_percent(self) -> float:
        """Podíl obrábění v %"""
        if self.unit_cost > 0:
            return round((self.machining_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def setup_percent(self) -> float:
        """Podíl seřízení v %"""
        if self.unit_cost > 0:
            return round((self.setup_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def overhead_percent(self) -> float:
        """Podíl režie v %"""
        if self.unit_cost > 0:
            return round((self.overhead_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def margin_percent(self) -> float:
        """Podíl marže v %"""
        if self.unit_cost > 0:
            return round((self.margin_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def coop_percent(self) -> float:
        """Podíl kooperací v %"""
        if self.unit_cost > 0:
            return round((self.coop_cost / self.unit_cost) * 100, 1)
        return 0.0

    @computed_field
    @property
    def unit_price(self) -> float:
        """Alias pro unit_cost (pro kompatibilitu s frontendem)"""
        return self.unit_cost
