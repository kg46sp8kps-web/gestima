"""GESTIMA - ModuleDefaults model

Module-wide default settings (distinct from per-user ModuleLayout).

Purpose:
- ModuleDefaults: Global defaults for module types (e.g., 'part-main', 'part-pricing')
- ModuleLayout: User-specific saved layouts/views

Example:
- ModuleDefaults: "part-pricing" module defaults to 800x600px
- ModuleLayout: User "john" has custom "My Layout" for "part-pricing"

ADR-031: Visual Editor System
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, JSON

from app.database import Base, AuditMixin


class ModuleDefaults(Base, AuditMixin):
    __tablename__ = "module_defaults"

    id = Column(Integer, primary_key=True, index=True)
    module_type = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "part-main", "part-pricing"
    default_width = Column(Integer, nullable=False)  # 200-3000
    default_height = Column(Integer, nullable=False)  # 200-3000
    settings = Column(JSON, nullable=True)  # splitPositions, columnWidths, etc.

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ModuleDefaultsBase(BaseModel):
    """Base schema for ModuleDefaults"""
    module_type: str = Field(..., max_length=100, description="Module type identifier (e.g., 'part-main')")
    default_width: int = Field(..., gt=200, le=3000, description="Default width in pixels (200-3000)")
    default_height: int = Field(..., gt=200, le=3000, description="Default height in pixels (200-3000)")
    settings: Optional[Dict[str, Any]] = Field(None, description="Additional settings as JSON")


class ModuleDefaultsCreate(ModuleDefaultsBase):
    """Create new module defaults"""
    pass


class ModuleDefaultsUpdate(BaseModel):
    """Update module defaults (all fields optional)"""
    default_width: Optional[int] = Field(None, gt=200, le=3000, description="Default width in pixels")
    default_height: Optional[int] = Field(None, gt=200, le=3000, description="Default height in pixels")
    settings: Optional[Dict[str, Any]] = Field(None, description="Additional settings as JSON")


class ModuleDefaultsResponse(ModuleDefaultsBase):
    """Module defaults response with metadata"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    version: int
