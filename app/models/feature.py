"""GESTIMA - Feature model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
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
    seq: int = 1
    feature_type: FeatureType = FeatureType.FACE
    from_diameter: Optional[float] = None
    to_diameter: Optional[float] = None
    length: Optional[float] = None
    depth: Optional[float] = None
    width: Optional[float] = None
    pocket_length: Optional[float] = None
    pocket_width: Optional[float] = None
    corner_radius: Optional[float] = None
    thread_pitch: Optional[float] = None
    Vc: Optional[float] = None
    f: Optional[float] = None
    Ap: Optional[float] = None
    fz: Optional[float] = None
    blade_width: float = 3.0
    count: int = 1
    note: str = ""


class FeatureCreate(FeatureBase):
    operation_id: int


class FeatureUpdate(BaseModel):
    seq: Optional[int] = None
    feature_type: Optional[FeatureType] = None
    from_diameter: Optional[float] = None
    to_diameter: Optional[float] = None
    length: Optional[float] = None
    depth: Optional[float] = None
    width: Optional[float] = None
    pocket_length: Optional[float] = None
    pocket_width: Optional[float] = None
    corner_radius: Optional[float] = None
    thread_pitch: Optional[float] = None
    Vc: Optional[float] = None
    f: Optional[float] = None
    Ap: Optional[float] = None
    fz: Optional[float] = None
    Vc_locked: Optional[bool] = None
    f_locked: Optional[bool] = None
    Ap_locked: Optional[bool] = None
    blade_width: Optional[float] = None
    count: Optional[int] = None
    note: Optional[str] = None


class FeatureResponse(FeatureBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    operation_id: int
    Vc_locked: bool
    f_locked: bool
    Ap_locked: bool
    predicted_time_sec: float
    created_at: datetime
    updated_at: datetime
