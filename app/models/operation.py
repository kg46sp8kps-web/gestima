"""GESTIMA - Operation model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
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
    
    machine_id = Column(Integer, nullable=True)
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
    seq: int = 10
    name: str = ""
    type: str = "turning"
    icon: str = "🔄"
    machine_id: Optional[int] = None
    cutting_mode: str = "mid"
    setup_time_min: float = 30.0
    is_coop: bool = False
    coop_type: Optional[str] = None
    coop_price: float = 0.0
    coop_min_price: float = 0.0
    coop_days: int = 0


class OperationCreate(OperationBase):
    part_id: int


class OperationUpdate(BaseModel):
    seq: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    icon: Optional[str] = None
    machine_id: Optional[int] = None
    cutting_mode: Optional[str] = None
    setup_time_min: Optional[float] = None
    operation_time_min: Optional[float] = None
    setup_time_locked: Optional[bool] = None
    operation_time_locked: Optional[bool] = None
    is_coop: Optional[bool] = None
    coop_type: Optional[str] = None
    coop_price: Optional[float] = None
    coop_min_price: Optional[float] = None
    coop_days: Optional[int] = None


class OperationResponse(OperationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    part_id: int
    operation_time_min: float
    setup_time_locked: bool
    operation_time_locked: bool
    created_at: datetime
    updated_at: datetime
