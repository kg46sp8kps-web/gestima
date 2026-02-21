"""GESTIMA - ProductionRecord model

Records actual production data imported from Infor ERP or entered manually.
Used for:
- FT model training (real times vs AI estimates)
- Production history tracking per Part
- Future optimizer (batch size → time correlation)

Part is identified by article_number (shared with Infor SLItems).
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class ProductionRecord(Base, AuditMixin):
    """Actual production record from Infor or manual entry."""
    __tablename__ = "production_records"

    id = Column(Integer, primary_key=True, index=True)

    # Link to Part (required)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Infor production order
    infor_order_number = Column(String(50), nullable=True, index=True)

    # Batch info
    batch_quantity = Column(Integer, nullable=True)

    # Operation info
    operation_seq = Column(Integer, nullable=True)
    work_center_id = Column(Integer, ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True, index=True)

    # Times — planned per piece (from Infor norms, min/ks)
    planned_time_min = Column(Float, nullable=True)  # stroj min/ks = 60 / DerRunMchHrs
    planned_labor_time_min = Column(Float, nullable=True)  # obsluha min/ks = 60 / DerRunLbrHrs
    planned_setup_min = Column(Float, nullable=True)  # seřízení min = JshSetupHrs * 60

    # Times — actual per piece (computed from batch totals, min/ks)
    actual_time_min = Column(Float, nullable=True)  # stroj min/ks = (RunHrsTMch * 60) / qty
    actual_labor_time_min = Column(Float, nullable=True)  # obsluha min/ks = (RunHrsTLbr * 60) / qty
    actual_setup_min = Column(Float, nullable=True)  # seřízení min = SetupHrsT * 60

    # Times — actual whole batch (for analysis, min)
    actual_run_machine_min = Column(Float, nullable=True)  # RunHrsTMch * 60 (celá dávka)
    actual_run_labor_min = Column(Float, nullable=True)  # RunHrsTLbr * 60 (celá dávka)

    # Manning coefficient — planned (DerRunMchHrs / DerRunLbrHrs * 100)
    manning_coefficient = Column(Float, nullable=True)
    # Manning coefficient — actual (RunHrsTMch / RunHrsTLbr * 100)
    actual_manning_coefficient = Column(Float, nullable=True)

    # When was this produced
    production_date = Column(Date, nullable=True)

    # Data source
    source = Column(String(20), default="manual", nullable=False)  # "infor", "manual"

    # Notes
    notes = Column(String(500), nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    part = relationship("Part", back_populates="production_records")
    work_center = relationship("WorkCenter")


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class ProductionRecordBase(BaseModel):
    """Base schema for ProductionRecord."""
    model_config = ConfigDict(from_attributes=True)

    infor_order_number: Optional[str] = Field(None, max_length=50, description="Infor production order number")
    batch_quantity: Optional[int] = Field(None, gt=0, description="Batch quantity (pieces)")
    operation_seq: Optional[int] = Field(None, ge=1, description="Operation sequence (10, 20, 30...)")
    work_center_id: Optional[int] = Field(None, gt=0, description="Work center ID")
    planned_time_min: Optional[float] = Field(None, ge=0, description="Planned machine time per piece (min/ks)")
    planned_labor_time_min: Optional[float] = Field(None, ge=0, description="Planned labor time per piece (min/ks)")
    planned_setup_min: Optional[float] = Field(None, ge=0, description="Planned setup time (min)")
    actual_time_min: Optional[float] = Field(None, ge=0, description="Actual machine time per piece (min/ks)")
    actual_labor_time_min: Optional[float] = Field(None, ge=0, description="Actual labor time per piece (min/ks)")
    actual_setup_min: Optional[float] = Field(None, ge=0, description="Actual setup time (min)")
    actual_run_machine_min: Optional[float] = Field(None, ge=0, description="Actual machine run time - whole batch (min)")
    actual_run_labor_min: Optional[float] = Field(None, ge=0, description="Actual labor run time - whole batch (min)")
    manning_coefficient: Optional[float] = Field(None, ge=0, description="Manning coefficient planned (%)")
    actual_manning_coefficient: Optional[float] = Field(None, ge=0, description="Manning coefficient actual (%)")
    production_date: Optional[date] = Field(None, description="Production date")
    source: str = Field("manual", max_length=20, description="Data source (infor/manual)")
    notes: Optional[str] = Field(None, max_length=500, description="Notes")


class ProductionRecordCreate(ProductionRecordBase):
    """Schema for creating a production record."""
    part_id: int = Field(..., gt=0, description="Part ID")


class ProductionRecordUpdate(BaseModel):
    """Schema for updating a production record."""
    infor_order_number: Optional[str] = Field(None, max_length=50)
    batch_quantity: Optional[int] = Field(None, gt=0)
    operation_seq: Optional[int] = Field(None, ge=1)
    work_center_id: Optional[int] = Field(None, gt=0)
    planned_time_min: Optional[float] = Field(None, ge=0)
    planned_labor_time_min: Optional[float] = Field(None, ge=0)
    planned_setup_min: Optional[float] = Field(None, ge=0)
    actual_time_min: Optional[float] = Field(None, ge=0)
    actual_labor_time_min: Optional[float] = Field(None, ge=0)
    actual_setup_min: Optional[float] = Field(None, ge=0)
    actual_run_machine_min: Optional[float] = Field(None, ge=0)
    actual_run_labor_min: Optional[float] = Field(None, ge=0)
    manning_coefficient: Optional[float] = Field(None, ge=0)
    actual_manning_coefficient: Optional[float] = Field(None, ge=0)
    production_date: Optional[date] = None
    source: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    version: int = Field(..., ge=0, description="Optimistic locking version")


class ProductionRecordResponse(ProductionRecordBase):
    """Schema for returning a production record."""
    id: int
    part_id: int
    version: int
    created_at: datetime
    updated_at: datetime

    # Resolved work center fields (populated by service)
    work_center_name: Optional[str] = Field(None, description="Work center name (resolved)")
    work_center_type: Optional[str] = Field(None, description="Work center type (resolved, e.g. CNC_LATHE)")
