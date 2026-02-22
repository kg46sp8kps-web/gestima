"""GESTIMA - UserLayout model

Stores named workspace tile layouts per user.
- Each layout holds a full TileNode tree as JSON
- Supports default layout and header quick-access visibility
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class UserLayout(Base, AuditMixin):
    __tablename__ = "user_layouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    tree_json = Column(JSON, nullable=False)       # full TileNode tree
    is_default = Column(Boolean, default=False, nullable=False)
    show_in_header = Column(Boolean, default=True, nullable=False)

    # AuditMixin: created_at, updated_at, created_by, updated_by,
    #             deleted_at, deleted_by, version

    user = relationship("User", backref="user_layouts")


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class UserLayoutCreate(BaseModel):
    name: str = Field(..., max_length=200)
    tree_json: Dict[str, Any] = Field(...)
    is_default: bool = Field(False)
    show_in_header: bool = Field(True)


class UserLayoutUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    tree_json: Optional[Dict[str, Any]] = Field(None)
    is_default: Optional[bool] = Field(None)
    show_in_header: Optional[bool] = Field(None)
    version: int   # optimistic lock — required


class UserLayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    tree_json: Dict[str, Any]
    is_default: bool
    show_in_header: bool
    created_at: datetime
    updated_at: datetime
    version: int
