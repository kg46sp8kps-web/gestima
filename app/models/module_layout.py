"""GESTIMA - ModuleLayout model

ADR-031: Visual Editor System
- Stores user-specific layout configurations for CustomizableModule
- Supports multiple layouts per module per user
- Default layout support
- JSON config storage (ModuleLayoutConfig)
"""

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin

if TYPE_CHECKING:
    from app.models.user import User


class ModuleLayout(Base, AuditMixin):
    __tablename__ = "module_layouts"

    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(100), nullable=False)  # e.g., "manufacturing-items-detail"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    layout_name = Column(String(200), nullable=False)  # e.g., "Custom Layout 2026-02-02"
    config = Column(JSON, nullable=False)  # ModuleLayoutConfig as JSON
    is_default = Column(Boolean, default=False, nullable=False)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    user = relationship("User", backref="module_layouts")


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ModuleLayoutBase(BaseModel):
    """Base schema for ModuleLayout"""
    module_key: str = Field(..., max_length=100, description="Module identifier (e.g., 'parts-detail')")
    layout_name: str = Field(..., max_length=200, description="Layout name (e.g., 'Custom Layout 2026-02-02')")
    config: Dict[str, Any] = Field(..., description="ModuleLayoutConfig as JSON")


class ModuleLayoutCreate(ModuleLayoutBase):
    """Create new module layout"""
    user_id: int = Field(..., description="User ID who owns this layout")
    is_default: bool = Field(False, description="Set as default layout for this module")


class ModuleLayoutUpdate(BaseModel):
    """Update module layout (all fields optional)"""
    layout_name: Optional[str] = Field(None, max_length=200, description="New layout name")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated config")
    is_default: Optional[bool] = Field(None, description="Set as default layout")


class ModuleLayoutResponse(ModuleLayoutBase):
    """Module layout response with metadata"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    version: int
