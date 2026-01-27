"""GESTIMA - Feature model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import FeatureType


class Feature(Base, AuditMixin):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id", ondelete="CASCADE"), index=True)
    seq = Column(Integer, default=1)
    
    feature_type = Column(Enum(FeatureType), default=FeatureType.FACE)
    
    from_diameter = Column(Float, nullable=True)
    to_diameter = Column(Float, nullable=True)
    length = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    pocket_length = Column(Float, nullable=True)
    pocket_width = Column(Float, nullable=True)
    corner_radius = Column(Float, nullable=True)
    thread_pitch = Column(Float, nullable=True)
    
    Vc = Column(Float, nullable=True)
    f = Column(Float, nullable=True)
    Ap = Column(Float, nullable=True)
    fz = Column(Float, nullable=True)
    
    Vc_locked = Column(Boolean, default=False)
    f_locked = Column(Boolean, default=False)
    Ap_locked = Column(Boolean, default=False)
    
    blade_width = Column(Float, default=3.0)
    count = Column(Integer, default=1)
    
    predicted_time_sec = Column(Float, default=0.0)
    
    note = Column(String(200), default="")
    
    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version
    
    operation = relationship("Operation", back_populates="features")


class FeatureBase(BaseModel):
    seq: int = Field(1, ge=1, description="Pořadí prvku v operaci")
    feature_type: FeatureType = FeatureType.FACE
    from_diameter: Optional[float] = Field(None, ge=0, description="Výchozí průměr v mm")
    to_diameter: Optional[float] = Field(None, ge=0, description="Cílový průměr v mm")
    length: Optional[float] = Field(None, ge=0, description="Délka v mm")
    depth: Optional[float] = Field(None, ge=0, description="Hloubka v mm")
    width: Optional[float] = Field(None, ge=0, description="Šířka v mm")
    pocket_length: Optional[float] = Field(None, ge=0, description="Délka kapsy v mm")
    pocket_width: Optional[float] = Field(None, ge=0, description="Šířka kapsy v mm")
    corner_radius: Optional[float] = Field(None, ge=0, description="Rádius rohu v mm")
    thread_pitch: Optional[float] = Field(None, gt=0, description="Stoupání závitu v mm")
    Vc: Optional[float] = Field(None, gt=0, description="Řezná rychlost m/min")
    f: Optional[float] = Field(None, gt=0, description="Posuv mm/ot")
    Ap: Optional[float] = Field(None, gt=0, description="Hloubka řezu mm")
    fz: Optional[float] = Field(None, gt=0, description="Posuv na zub mm")
    blade_width: float = Field(3.0, gt=0, description="Šířka břitu v mm")
    count: int = Field(1, ge=1, description="Počet opakování")
    note: str = Field("", max_length=200, description="Poznámka")


class FeatureCreate(FeatureBase):
    operation_id: int = Field(..., gt=0, description="ID operace")


class FeatureUpdate(BaseModel):
    seq: Optional[int] = Field(None, ge=1)
    feature_type: Optional[FeatureType] = None
    from_diameter: Optional[float] = Field(None, ge=0)
    to_diameter: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    depth: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    pocket_length: Optional[float] = Field(None, ge=0)
    pocket_width: Optional[float] = Field(None, ge=0)
    corner_radius: Optional[float] = Field(None, ge=0)
    thread_pitch: Optional[float] = Field(None, gt=0)
    Vc: Optional[float] = Field(None, gt=0)
    f: Optional[float] = Field(None, gt=0)
    Ap: Optional[float] = Field(None, gt=0)
    fz: Optional[float] = Field(None, gt=0)
    Vc_locked: Optional[bool] = None
    f_locked: Optional[bool] = None
    Ap_locked: Optional[bool] = None
    blade_width: Optional[float] = Field(None, gt=0)
    count: Optional[int] = Field(None, ge=1)
    note: Optional[str] = Field(None, max_length=200)
    version: int  # Optimistic locking (ADR-008)


class FeatureResponse(FeatureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: int
    Vc_locked: bool
    f_locked: bool
    Ap_locked: bool
    predicted_time_sec: float
    version: int
    created_at: datetime
    updated_at: datetime
