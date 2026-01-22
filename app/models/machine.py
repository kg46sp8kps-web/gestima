"""GESTIMA - Machine model"""

from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float, Boolean

from app.database import Base, AuditMixin


class MachineDB(Base, AuditMixin):
    """SQLAlchemy model for machines"""
    __tablename__ = "machines"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    type = Column(String(50))  # saw, lathe, mill
    subtype = Column(String(50), nullable=True)  # horizontal, vertical
    
    # Dimensions
    max_bar_dia = Column(Float, nullable=True)
    max_cut_diameter = Column(Float, nullable=True)
    max_workpiece_dia = Column(Float, nullable=True)
    max_workpiece_length = Column(Float, nullable=True)
    min_workpiece_dia = Column(Float, nullable=True)
    bar_feed_max_length = Column(Float, nullable=True)
    
    # Capabilities
    has_bar_feeder = Column(Boolean, default=False)
    has_milling = Column(Boolean, default=False)
    max_milling_tools = Column(Integer, nullable=True)
    has_sub_spindle = Column(Boolean, default=False)
    axes = Column(Integer, nullable=True)  # 3, 4, 5
    
    # Production
    suitable_for_series = Column(Boolean, default=True)
    suitable_for_single = Column(Boolean, default=True)
    
    # Economics
    hourly_rate = Column(Float, default=1000.0)
    setup_base_min = Column(Float, default=30.0)
    setup_per_tool_min = Column(Float, default=3.0)
    default_k_machine = Column(Float, nullable=True)
    default_k_operator = Column(Float, nullable=True)
    
    # Workflow
    priority = Column(Integer, default=99)
    active = Column(Boolean, default=True)
    
    notes = Column(String(1000), nullable=True)


class MachineBase(BaseModel):
    """Pydantic schema for Machine"""
    model_config = ConfigDict(from_attributes=True)
    
    code: str
    name: str
    type: str
    subtype: Optional[str] = None
    
    max_bar_dia: Optional[float] = None
    max_cut_diameter: Optional[float] = None
    max_workpiece_dia: Optional[float] = None
    max_workpiece_length: Optional[float] = None
    min_workpiece_dia: Optional[float] = None
    bar_feed_max_length: Optional[float] = None
    
    has_bar_feeder: bool = False
    has_milling: bool = False
    max_milling_tools: Optional[int] = None
    has_sub_spindle: bool = False
    axes: Optional[int] = None
    
    suitable_for_series: bool = True
    suitable_for_single: bool = True
    
    hourly_rate: float = 1000.0
    setup_base_min: float = 30.0
    setup_per_tool_min: float = 3.0
    default_k_machine: Optional[float] = None
    default_k_operator: Optional[float] = None
    
    priority: int = 99
    active: bool = True
    
    notes: Optional[str] = None


class MachineCreate(MachineBase):
    """Schema for creating machine"""
    pass


class MachineResponse(MachineBase):
    """Schema for returning machine"""
    id: int
