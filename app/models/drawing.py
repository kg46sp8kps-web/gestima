"""GESTIMA - Drawing model

Multiple drawings per part support.
Each part can have multiple PDF drawings with one marked as primary.

Features:
- SHA-256 hash for deduplication
- Primary flag with auto-promotion on delete
- Soft delete via AuditMixin
- Revision tracking (A, B, C...)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin

if TYPE_CHECKING:
    from app.models.part import Part


class Drawing(Base, AuditMixin):
    """Drawing file metadata for parts (1:N relationship)"""
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)

    # File metadata
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 (not globally unique - same file can be used for multiple parts)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)

    # Drawing metadata
    is_primary = Column(Boolean, default=False, nullable=False, index=True)
    revision = Column(String(2), default="A", nullable=False)

    # AuditMixin provides:
    # - created_at, updated_at, created_by, updated_by
    # - deleted_at, deleted_by (soft delete)
    # - version (optimistic locking)

    # Relationship
    part = relationship("Part", back_populates="drawings")

    def __repr__(self) -> str:
        return f"<Drawing(id={self.id}, part_id={self.part_id}, filename='{self.filename}', primary={self.is_primary})>"
