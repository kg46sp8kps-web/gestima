"""GESTIMA - Machine model"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Boolean

from app.database import Base, AuditMixin


class MachineDB(Base, AuditMixin):
    """SQLAlchemy model for machines"""
    __tablename__ = "machines"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # saw, lathe, mill
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
    
    # Economics - Hourly Rate Breakdown (ADR-016)
    hourly_rate_amortization = Column(Float, default=400.0, nullable=False)  # Odpisy stroje
    hourly_rate_labor = Column(Float, default=300.0, nullable=False)         # Mzda operátora
    hourly_rate_tools = Column(Float, default=200.0, nullable=False)         # Nástroje
    hourly_rate_overhead = Column(Float, default=300.0, nullable=False)      # Provozní režie

    setup_base_min = Column(Float, default=30.0)
    setup_per_tool_min = Column(Float, default=3.0)
    default_k_machine = Column(Float, nullable=True)
    default_k_operator = Column(Float, nullable=True)

    @property
    def hourly_rate_setup(self) -> float:
        """Seřizovací sazba (BEZ nástrojů)"""
        return (self.hourly_rate_amortization +
                self.hourly_rate_labor +
                self.hourly_rate_overhead)

    @property
    def hourly_rate_operation(self) -> float:
        """Výrobní sazba (S nástroji)"""
        return (self.hourly_rate_amortization +
                self.hourly_rate_labor +
                self.hourly_rate_tools +
                self.hourly_rate_overhead)

    @property
    def hourly_rate_total(self) -> float:
        """Alias pro operation rate (backward compatibility)"""
        return self.hourly_rate_operation
    
    # Workflow
    priority = Column(Integer, default=99)
    active = Column(Boolean, default=True)
    
    notes = Column(String(1000), nullable=True)


class MachineBase(BaseModel):
    """Pydantic schema for Machine"""
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., max_length=50, description="Unikátní kód stroje")
    name: str = Field(..., max_length=200, description="Název stroje")
    type: str = Field(..., max_length=50, description="Typ stroje (saw, lathe, mill)")
    subtype: Optional[str] = Field(None, max_length=50)

    max_bar_dia: Optional[float] = Field(None, ge=0)
    max_cut_diameter: Optional[float] = Field(None, ge=0)
    max_workpiece_dia: Optional[float] = Field(None, ge=0)
    max_workpiece_length: Optional[float] = Field(None, ge=0)
    min_workpiece_dia: Optional[float] = Field(None, ge=0)
    bar_feed_max_length: Optional[float] = Field(None, ge=0)

    has_bar_feeder: bool = False
    has_milling: bool = False
    max_milling_tools: Optional[int] = Field(None, ge=0)
    has_sub_spindle: bool = False
    axes: Optional[int] = Field(None, ge=2, le=9)

    suitable_for_series: bool = True
    suitable_for_single: bool = True

    # Hourly Rate Breakdown (ADR-016)
    hourly_rate_amortization: float = Field(400.0, ge=0, description="Odpisy stroje (Kč/h)")
    hourly_rate_labor: float = Field(300.0, ge=0, description="Mzda operátora (Kč/h)")
    hourly_rate_tools: float = Field(200.0, ge=0, description="Nástroje (Kč/h)")
    hourly_rate_overhead: float = Field(300.0, ge=0, description="Provozní režie (Kč/h)")

    setup_base_min: float = Field(30.0, ge=0, description="Základní čas seřízení (min)")
    setup_per_tool_min: float = Field(3.0, ge=0, description="Čas seřízení na nástroj (min)")
    default_k_machine: Optional[float] = Field(None, ge=0)
    default_k_operator: Optional[float] = Field(None, ge=0)

    priority: int = Field(99, ge=0, description="Priorita stroje")
    active: bool = True

    notes: Optional[str] = Field(None, max_length=1000)


class MachineCreate(MachineBase):
    """Schema for creating machine"""
    pass


class MachineUpdate(BaseModel):
    """Schema for updating machine"""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[str] = Field(None, max_length=50)
    subtype: Optional[str] = Field(None, max_length=50)
    max_bar_dia: Optional[float] = Field(None, ge=0)
    max_cut_diameter: Optional[float] = Field(None, ge=0)
    max_workpiece_dia: Optional[float] = Field(None, ge=0)
    max_workpiece_length: Optional[float] = Field(None, ge=0)
    min_workpiece_dia: Optional[float] = Field(None, ge=0)
    bar_feed_max_length: Optional[float] = Field(None, ge=0)
    has_bar_feeder: Optional[bool] = None
    has_milling: Optional[bool] = None
    max_milling_tools: Optional[int] = Field(None, ge=0)
    has_sub_spindle: Optional[bool] = None
    axes: Optional[int] = Field(None, ge=2, le=9)
    suitable_for_series: Optional[bool] = None
    suitable_for_single: Optional[bool] = None

    # Hourly Rate Breakdown (ADR-016)
    hourly_rate_amortization: Optional[float] = Field(None, ge=0)
    hourly_rate_labor: Optional[float] = Field(None, ge=0)
    hourly_rate_tools: Optional[float] = Field(None, ge=0)
    hourly_rate_overhead: Optional[float] = Field(None, ge=0)

    setup_base_min: Optional[float] = Field(None, ge=0)
    setup_per_tool_min: Optional[float] = Field(None, ge=0)
    default_k_machine: Optional[float] = Field(None, ge=0)
    default_k_operator: Optional[float] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=0)
    active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    version: int  # Optimistic locking (ADR-008)


class MachineResponse(MachineBase):
    """Schema for returning machine"""
    id: int
    version: int
    created_at: datetime
    updated_at: datetime

    # Computed fields (read-only)
    hourly_rate_setup: float = Field(..., description="Computed: seřizovací sazba (bez nástrojů)")
    hourly_rate_operation: float = Field(..., description="Computed: výrobní sazba (s nástroji)")
    hourly_rate_total: float = Field(..., description="Computed: celková sazba (alias pro operation)")

    @classmethod
    def from_orm(cls, machine):
        """Factory method with computed fields"""
        data = {
            **{k: getattr(machine, k) for k in MachineBase.model_fields.keys()},
            'id': machine.id,
            'version': machine.version,
            'created_at': machine.created_at,
            'updated_at': machine.updated_at,
            'hourly_rate_setup': machine.hourly_rate_setup,
            'hourly_rate_operation': machine.hourly_rate_operation,
            'hourly_rate_total': machine.hourly_rate_total,
        }
        return cls(**data)
