"""GESTIMA - System Configuration model (ADR-016)"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String, Float

from app.database import Base, AuditMixin


class SystemConfig(Base, AuditMixin):
    """
    Globální nastavení kalkulací.

    Používané klíče:
    - overhead_coefficient: 1.20 (administrativní režie +20%)
    - margin_coefficient: 1.25 (marže +25%)
    - stock_coefficient: 1.15 (skladová přirážka na materiál +15%)
    - coop_coefficient: 1.10 (kooperační přirážka +10%)
    """
    __tablename__ = "system_config"

    key = Column(String(50), primary_key=True)
    value_float = Column(Float, nullable=False)
    description = Column(String(500), nullable=False)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


# ========== PYDANTIC SCHEMAS ==========

class SystemConfigBase(BaseModel):
    """Base schema for system config"""
    model_config = ConfigDict(from_attributes=True)

    key: str = Field(..., max_length=50, description="Konfigurační klíč")
    value_float: float = Field(..., description="Hodnota (koeficient)")
    description: str = Field(..., max_length=500, description="Popis nastavení")


class SystemConfigCreate(SystemConfigBase):
    """Schema for creating config"""
    pass


class SystemConfigUpdate(BaseModel):
    """Schema for updating config"""
    value_float: Optional[float] = None
    description: Optional[str] = Field(None, max_length=500)
    version: int  # Optimistic locking


class SystemConfigResponse(SystemConfigBase):
    """Schema for returning config"""
    version: int
    created_at: datetime
    updated_at: datetime
