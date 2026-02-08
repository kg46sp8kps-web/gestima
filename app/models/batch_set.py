"""GESTIMA - BatchSet model (ADR-022: Sady cen)

BatchSet groups multiple Batches for a Part into a single pricing set.
Key features:
- Auto-generated timestamp name
- Atomic freeze operation (all batches in set)
- Soft delete support
- Prepared for Workspace module (ADR-023)
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin

if TYPE_CHECKING:
    from app.models.batch import BatchResponse


class BatchSet(Base, AuditMixin):
    """
    BatchSet model - groups Batches into pricing sets.

    Numbering: 35XXXXXX (ADR-022)
    """
    __tablename__ = "batch_sets"

    id = Column(Integer, primary_key=True, index=True)
    set_number = Column(String(8), unique=True, nullable=False, index=True)  # 35XXXXXX
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # Auto: "2026-01-28 14:35"
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft | frozen

    # Freeze metadata
    frozen_at = Column(DateTime, nullable=True, index=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    part = relationship("Part", back_populates="batch_sets")
    batches = relationship("Batch", back_populates="batch_set", cascade="all, delete-orphan")
    frozen_by = relationship("User")

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


def generate_batch_set_name() -> str:
    """Generate auto-name from current timestamp (ISO sortable + readable)."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")


# =============================================================================
# Pydantic Schemas
# =============================================================================

class BatchSetCreate(BaseModel):
    """Create new BatchSet - only part_id required, rest is auto-generated."""
    part_id: int = Field(..., gt=0, description="ID dílu")


class BatchSetUpdate(BaseModel):
    """Update BatchSet - only name can be changed manually."""
    name: Optional[str] = Field(None, max_length=100, description="Název sady")
    version: int = Field(..., description="Optimistic locking")


class BatchSetResponse(BaseModel):
    """BatchSet response with computed fields."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_number: str
    part_id: Optional[int]
    name: str
    status: str
    frozen_at: Optional[datetime] = None
    frozen_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    version: int

    # Nested batches (loaded separately to avoid circular import)
    # Will be populated by router when needed


class BatchSetWithBatchesResponse(BatchSetResponse):
    """BatchSet response with nested batches for detail view."""
    batches: List["BatchResponse"] = []

    @computed_field
    @property
    def batch_count(self) -> int:
        """Number of batches in this set."""
        return len(self.batches)

    @computed_field
    @property
    def total_value(self) -> float:
        """Sum of all batch total_costs in this set."""
        return sum(b.total_cost for b in self.batches) if self.batches else 0.0


class BatchSetListResponse(BaseModel):
    """Lightweight BatchSet for list views (no nested batches)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_number: str
    part_id: Optional[int]
    name: str
    status: str
    frozen_at: Optional[datetime] = None
    created_at: datetime
    version: int
    batch_count: int = 0  # Computed by query


# Update forward references
from app.models.batch import BatchResponse  # noqa: E402
BatchSetWithBatchesResponse.model_rebuild()
