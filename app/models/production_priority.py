"""GESTIMA - ProductionPriority model

Lokalni priorita a "hori" flag pro VP v Production Planner.
DB uklada POUZE prioritu + hot flag. Vsechna data (operace, datumy, mnozstvi)
vzdy z Inforu. CO terminy pres existujici Item-based matching.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint

from app.database import Base, AuditMixin


class ProductionPriority(Base, AuditMixin):
    """Lokalni priorita a hot flag pro VP."""
    __tablename__ = "production_priorities"
    __table_args__ = (
        UniqueConstraint(
            "infor_job", "infor_suffix",
            name="uq_production_priority_job_suffix",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    infor_job = Column(String(30), nullable=False)
    infor_suffix = Column(String(5), nullable=False, default="0")
    priority = Column(Integer, nullable=False, default=100)
    is_hot = Column(Boolean, nullable=False, default=False)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class ProductionPrioritySetRequest(BaseModel):
    """Nastavit prioritu VP."""
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    priority: int = Field(..., ge=1, le=9999)


class ProductionPriorityFireRequest(BaseModel):
    """Toggle hot flag na VP."""
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    is_hot: bool = Field(True)


class ProductionPriorityTierRequest(BaseModel):
    """Nastavit tier (hot/urgent/frozen/normal) na VP."""
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    tier: Literal['hot', 'urgent', 'frozen', 'normal']
