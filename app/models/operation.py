"""GESTIMA - Operation model

ADR-024: MaterialInput refactor (v1.8.0)
- Added M:N relationship with MaterialInput
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.material_input import material_operation_link


class Operation(Base, AuditMixin):
    __tablename__ = "operations"
    
    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), index=True)
    seq = Column(Integer, default=10)
    
    name = Column(String(200), default="")
    type = Column(String(50), default="turning")
    icon = Column(String(10), default="settings")
    
    work_center_id = Column(Integer, ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    cutting_mode = Column(String(10), default="mid")
    
    setup_time_min = Column(Float, default=30.0)
    operation_time_min = Column(Float, default=0.0)
    
    setup_time_locked = Column(Boolean, default=False)
    operation_time_locked = Column(Boolean, default=False)

    manning_coefficient = Column(Float, default=100.0)  # Koeficient plnění v %
    machine_utilization_coefficient = Column(Float, default=100.0)  # Koeficient využití strojů v %

    is_coop = Column(Boolean, default=False)
    coop_type = Column(String(50), nullable=True)
    coop_price = Column(Float, default=0.0)
    coop_min_price = Column(Float, default=0.0)
    coop_days = Column(Integer, default=0)
    
    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    part = relationship("Part", back_populates="operations")
    features = relationship("Feature", back_populates="operation", cascade="all, delete-orphan")

    # ADR-024: M:N relationship with MaterialInput
    material_inputs = relationship(
        "MaterialInput",
        secondary=material_operation_link,
        back_populates="operations"
    )


class OperationBase(BaseModel):
    seq: int = Field(10, ge=1, description="Pořadí operace")
    name: str = Field("", max_length=200, description="Název operace")
    type: str = Field("turning", max_length=50, description="Typ operace")
    icon: str = Field("settings", max_length=10, description="Ikona operace")
    work_center_id: Optional[int] = Field(None, gt=0, description="ID pracoviště")
    cutting_mode: str = Field("mid", max_length=10, description="Režim obrábění")
    setup_time_min: float = Field(30.0, ge=0, description="Čas seřízení v minutách")
    operation_time_min: float = Field(0.0, ge=0, description="Čas operace v minutách")
    manning_coefficient: float = Field(100.0, ge=0, le=200, description="Koeficient plnění v %")
    machine_utilization_coefficient: float = Field(100.0, ge=0, le=200, description="Koeficient využití strojů v %")
    is_coop: bool = False
    coop_type: Optional[str] = Field(None, max_length=50, description="Typ kooperace")
    coop_price: float = Field(0.0, ge=0, description="Cena kooperace za kus")
    coop_min_price: float = Field(0.0, ge=0, description="Minimální cena kooperace")
    coop_days: int = Field(0, ge=0, description="Doba kooperace ve dnech")


class OperationCreate(OperationBase):
    part_id: int = Field(..., gt=0, description="ID dílu")


class OperationUpdate(BaseModel):
    seq: Optional[int] = Field(None, ge=1)
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[str] = Field(None, max_length=50)
    icon: Optional[str] = Field(None, max_length=10)
    work_center_id: Optional[int] = Field(None, gt=0)
    cutting_mode: Optional[str] = Field(None, max_length=10)
    setup_time_min: Optional[float] = Field(None, ge=0)
    operation_time_min: Optional[float] = Field(None, ge=0)
    setup_time_locked: Optional[bool] = None
    operation_time_locked: Optional[bool] = None
    manning_coefficient: Optional[float] = Field(None, ge=0, le=200)
    machine_utilization_coefficient: Optional[float] = Field(None, ge=0, le=200)
    is_coop: Optional[bool] = None
    coop_type: Optional[str] = Field(None, max_length=50)
    coop_price: Optional[float] = Field(None, ge=0)
    coop_min_price: Optional[float] = Field(None, ge=0)
    coop_days: Optional[int] = Field(None, ge=0)
    version: int  # Optimistic locking (ADR-008)


class OperationResponse(OperationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    setup_time_locked: bool
    operation_time_locked: bool
    version: int
    created_at: datetime
    updated_at: datetime

    @field_validator('setup_time_min', 'operation_time_min', 'coop_price', 'coop_min_price', mode='before')
    @classmethod
    def convert_none_to_default(cls, v, info):
        """Nahraď None hodnoty defaultními hodnotami (pro DB kompatibilitu)"""
        if v is None:
            defaults = {
                'setup_time_min': 30.0,
                'operation_time_min': 0.0,
                'coop_price': 0.0,
                'coop_min_price': 0.0
            }
            return defaults.get(info.field_name, 0.0)
        return v


from app.models.enums import CuttingMode


class ChangeModeRequest(BaseModel):
    """Request pro změnu režimu obrábění"""
    cutting_mode: CuttingMode = Field(..., description="Režim obrábění")
    version: int = Field(..., ge=0, description="Verze pro optimistic locking")
