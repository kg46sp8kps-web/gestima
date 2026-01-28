"""GESTIMA - WorkCenter model (ADR-021)

Pracoviště - fyzický stroj nebo virtuální pracovní stanice.
Single model approach (Machine + WorkCenter combined).

Sequential numbering: 80XXXXXX (80000001-80999999)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Enum as SQLEnum

from app.database import Base, AuditMixin
from app.models.enums import WorkCenterType


class WorkCenter(Base, AuditMixin):
    """SQLAlchemy model for work centers (ADR-021)"""
    __tablename__ = "work_centers"

    id = Column(Integer, primary_key=True, index=True)

    # Identification (ADR-017 v2.0: 8-digit, prefix 80, SEQUENTIAL)
    work_center_number = Column(String(8), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)

    # Type classification
    work_center_type = Column(SQLEnum(WorkCenterType), nullable=False)

    # Economics (pro TPV kalkulace)
    hourly_rate_amortization = Column(Float, nullable=True)  # Odpisy stroje (Kč/h)
    hourly_rate_labor = Column(Float, nullable=True)         # Mzda operátora (Kč/h)
    hourly_rate_tools = Column(Float, nullable=True)         # Nástroje (Kč/h)
    hourly_rate_overhead = Column(Float, nullable=True)      # Provozní režie (Kč/h)

    # Tech specs (optional - pro constraint checking)
    max_workpiece_diameter = Column(Float, nullable=True)   # mm
    max_workpiece_length = Column(Float, nullable=True)     # mm
    min_workpiece_diameter = Column(Float, nullable=True)   # mm
    axes = Column(Integer, nullable=True)                   # 3, 4, 5
    subtype = Column(String(50), nullable=True)             # horizontal, vertical

    # Bar feeder / Saw specs
    max_bar_diameter = Column(Float, nullable=True)         # mm (pro bar feeder)
    max_cut_diameter = Column(Float, nullable=True)         # mm (pro pily)
    bar_feed_max_length = Column(Float, nullable=True)      # mm

    # Capabilities (z Machine modelu)
    has_bar_feeder = Column(Boolean, default=False)
    has_sub_spindle = Column(Boolean, default=False)
    has_milling = Column(Boolean, default=False)            # Live tooling
    max_milling_tools = Column(Integer, nullable=True)

    # Production suitability
    suitable_for_series = Column(Boolean, default=True)
    suitable_for_single = Column(Boolean, default=True)

    # Setup times (pro kalkulace)
    setup_base_min = Column(Float, default=30.0)            # Základní seřízení (min)
    setup_per_tool_min = Column(Float, default=3.0)         # Seřízení na nástroj (min)

    # Organization
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=99)
    notes = Column(Text, nullable=True)

    @property
    def hourly_rate_setup(self) -> Optional[float]:
        """Seřizovací sazba (BEZ nástrojů) - používá se při tp"""
        rates = [
            self.hourly_rate_amortization,
            self.hourly_rate_labor,
            self.hourly_rate_overhead
        ]
        if all(r is not None for r in rates):
            return sum(rates)
        return None

    @property
    def hourly_rate_operation(self) -> Optional[float]:
        """Výrobní sazba (S nástroji) - používá se při tj"""
        rates = [
            self.hourly_rate_amortization,
            self.hourly_rate_labor,
            self.hourly_rate_tools,
            self.hourly_rate_overhead
        ]
        if all(r is not None for r in rates):
            return sum(rates)
        return None

    @property
    def hourly_rate_total(self) -> Optional[float]:
        """Celková hodinová sazba (alias pro hourly_rate_operation)"""
        return self.hourly_rate_operation


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class WorkCenterBase(BaseModel):
    """Base schema for WorkCenter"""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., max_length=200, description="Název pracoviště")
    work_center_type: WorkCenterType = Field(..., description="Typ pracoviště")
    subtype: Optional[str] = Field(None, max_length=50, description="Podtyp (horizontal, vertical)")

    # Economics (optional - virtuální pracoviště nemusí mít sazby)
    hourly_rate_amortization: Optional[float] = Field(None, ge=0, description="Odpisy stroje (Kč/h)")
    hourly_rate_labor: Optional[float] = Field(None, ge=0, description="Mzda operátora (Kč/h)")
    hourly_rate_tools: Optional[float] = Field(None, ge=0, description="Nástroje (Kč/h)")
    hourly_rate_overhead: Optional[float] = Field(None, ge=0, description="Provozní režie (Kč/h)")

    # Tech specs (optional)
    max_workpiece_diameter: Optional[float] = Field(None, ge=0, description="Max průměr obrobku (mm)")
    max_workpiece_length: Optional[float] = Field(None, ge=0, description="Max délka obrobku (mm)")
    min_workpiece_diameter: Optional[float] = Field(None, ge=0, description="Min průměr obrobku (mm)")
    axes: Optional[int] = Field(None, ge=2, le=9, description="Počet os (3, 4, 5)")

    # Bar feeder / Saw specs
    max_bar_diameter: Optional[float] = Field(None, ge=0, description="Max průměr tyče pro bar feeder (mm)")
    max_cut_diameter: Optional[float] = Field(None, ge=0, description="Max průměr řezu pro pilu (mm)")
    bar_feed_max_length: Optional[float] = Field(None, ge=0, description="Max délka tyče pro bar feeder (mm)")

    # Capabilities
    has_bar_feeder: bool = Field(False, description="Má podavač tyčí")
    has_sub_spindle: bool = Field(False, description="Má protivřeteno")
    has_milling: bool = Field(False, description="Má live tooling (frézování)")
    max_milling_tools: Optional[int] = Field(None, ge=0, description="Max počet frézovacích nástrojů")

    # Production suitability
    suitable_for_series: bool = Field(True, description="Vhodný pro sériovou výrobu")
    suitable_for_single: bool = Field(True, description="Vhodný pro kusovou výrobu")

    # Setup times
    setup_base_min: float = Field(30.0, ge=0, description="Základní seřízení (min)")
    setup_per_tool_min: float = Field(3.0, ge=0, description="Seřízení na nástroj (min)")

    # Organization
    is_active: bool = Field(True, description="Pracoviště je aktivní")
    priority: int = Field(99, ge=0, description="Priorita (nižší = vyšší priorita)")
    notes: Optional[str] = Field(None, max_length=1000, description="Poznámky")


class WorkCenterCreate(WorkCenterBase):
    """Schema for creating work center"""
    # work_center_number is optional - if None, will be auto-generated
    work_center_number: Optional[str] = Field(
        None,
        min_length=8,
        max_length=8,
        pattern=r"^80\d{6}$",
        description="8-digit number (80XXXXXX) - auto-generated if not provided"
    )


class WorkCenterUpdate(BaseModel):
    """Schema for updating work center"""
    name: Optional[str] = Field(None, max_length=200)
    work_center_type: Optional[WorkCenterType] = None
    subtype: Optional[str] = Field(None, max_length=50)

    hourly_rate_amortization: Optional[float] = Field(None, ge=0)
    hourly_rate_labor: Optional[float] = Field(None, ge=0)
    hourly_rate_tools: Optional[float] = Field(None, ge=0)
    hourly_rate_overhead: Optional[float] = Field(None, ge=0)

    max_workpiece_diameter: Optional[float] = Field(None, ge=0)
    max_workpiece_length: Optional[float] = Field(None, ge=0)
    min_workpiece_diameter: Optional[float] = Field(None, ge=0)
    axes: Optional[int] = Field(None, ge=2, le=9)

    max_bar_diameter: Optional[float] = Field(None, ge=0)
    max_cut_diameter: Optional[float] = Field(None, ge=0)
    bar_feed_max_length: Optional[float] = Field(None, ge=0)

    has_bar_feeder: Optional[bool] = None
    has_sub_spindle: Optional[bool] = None
    has_milling: Optional[bool] = None
    max_milling_tools: Optional[int] = Field(None, ge=0)

    suitable_for_series: Optional[bool] = None
    suitable_for_single: Optional[bool] = None

    setup_base_min: Optional[float] = Field(None, ge=0)
    setup_per_tool_min: Optional[float] = Field(None, ge=0)

    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)

    version: int  # Optimistic locking (ADR-008)


class WorkCenterResponse(WorkCenterBase):
    """Schema for returning work center"""
    id: int
    work_center_number: str
    version: int
    created_at: datetime
    updated_at: datetime

    # Computed fields (read-only)
    hourly_rate_setup: Optional[float] = Field(None, description="Computed: seřizovací sazba (bez nástrojů)")
    hourly_rate_operation: Optional[float] = Field(None, description="Computed: výrobní sazba (s nástroji)")
    hourly_rate_total: Optional[float] = Field(None, description="Computed: celková hodinová sazba")

    @classmethod
    def from_orm(cls, work_center: WorkCenter) -> "WorkCenterResponse":
        """Factory method with computed fields"""
        return cls(
            id=work_center.id,
            work_center_number=work_center.work_center_number,
            name=work_center.name,
            work_center_type=work_center.work_center_type,
            subtype=work_center.subtype,
            hourly_rate_amortization=work_center.hourly_rate_amortization,
            hourly_rate_labor=work_center.hourly_rate_labor,
            hourly_rate_tools=work_center.hourly_rate_tools,
            hourly_rate_overhead=work_center.hourly_rate_overhead,
            max_workpiece_diameter=work_center.max_workpiece_diameter,
            max_workpiece_length=work_center.max_workpiece_length,
            min_workpiece_diameter=work_center.min_workpiece_diameter,
            axes=work_center.axes,
            max_bar_diameter=work_center.max_bar_diameter,
            max_cut_diameter=work_center.max_cut_diameter,
            bar_feed_max_length=work_center.bar_feed_max_length,
            has_bar_feeder=work_center.has_bar_feeder,
            has_sub_spindle=work_center.has_sub_spindle,
            has_milling=work_center.has_milling,
            max_milling_tools=work_center.max_milling_tools,
            suitable_for_series=work_center.suitable_for_series,
            suitable_for_single=work_center.suitable_for_single,
            setup_base_min=work_center.setup_base_min,
            setup_per_tool_min=work_center.setup_per_tool_min,
            is_active=work_center.is_active,
            priority=work_center.priority,
            notes=work_center.notes,
            version=work_center.version,
            created_at=work_center.created_at,
            updated_at=work_center.updated_at,
            hourly_rate_setup=work_center.hourly_rate_setup,
            hourly_rate_operation=work_center.hourly_rate_operation,
            hourly_rate_total=work_center.hourly_rate_total,
        )
