"""GESTIMA - Operation model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class Operation(Base, AuditMixin):
    __tablename__ = "operations"
    
    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), index=True)
    seq = Column(Integer, default=10)
    
    name = Column(String(200), default="")
    type = Column(String(50), default="turning")
    icon = Column(String(10), default="🔄")
    
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    cutting_mode = Column(String(10), default="mid")
    
    setup_time_min = Column(Float, default=30.0)
    operation_time_min = Column(Float, default=0.0)
    
    setup_time_locked = Column(Boolean, default=False)
    operation_time_locked = Column(Boolean, default=False)
    
    is_coop = Column(Boolean, default=False)
    coop_type = Column(String(50), nullable=True)
    coop_price = Column(Float, default=0.0)
    coop_min_price = Column(Float, default=0.0)
    coop_days = Column(Integer, default=0)
    
    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version
    
    part = relationship("Part", back_populates="operations")
    features = relationship("Feature", back_populates="operation", cascade="all, delete-orphan")


class OperationBase(BaseModel):
    seq: int = Field(10, ge=1, description="Pořadí operace")
    name: str = Field("", max_length=200, description="Název operace")
    type: str = Field("turning", max_length=50, description="Typ operace")
    icon: str = Field("🔄", max_length=10, description="Ikona operace")
    machine_id: Optional[int] = Field(None, gt=0, description="ID stroje")
    cutting_mode: str = Field("mid", max_length=10, description="Režim obrábění")
    setup_time_min: float = Field(30.0, ge=0, description="Čas seřízení v minutách")
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
    machine_id: Optional[int] = Field(None, gt=0)
    cutting_mode: Optional[str] = Field(None, max_length=10)
    setup_time_min: Optional[float] = Field(None, ge=0)
    operation_time_min: Optional[float] = Field(None, ge=0)
    setup_time_locked: Optional[bool] = None
    operation_time_locked: Optional[bool] = None
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
    operation_time_min: float
    setup_time_locked: bool
    operation_time_locked: bool
    version: int
    created_at: datetime
    updated_at: datetime
