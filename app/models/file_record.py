"""GESTIMA - FileRecord and FileLink models

Centralized file management system (ADR-044).

FileRecord:
- Physical file storage registry
- SHA-256 hash for integrity
- Status lifecycle (temp → active → archived)
- NO entity-specific logic (generic storage)

FileLink:
- Polymorphic entity-file relationships
- One file can be linked to multiple entities
- Business metadata (is_primary, revision) lives here
- Unique constraint: one file can be linked to same entity only once

Features:
- Deduplication via file_hash index
- Soft delete via AuditMixin
- Temp file cleanup via status field
- Orphan detection (files without links)
"""

from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin

if TYPE_CHECKING:
    pass  # Future: from app.models.part import Part


class FileRecord(Base, AuditMixin):
    """
    Physical file storage registry.

    One FileRecord = one physical file on disk.
    Business logic (primary, revision) lives in FileLink, not here.
    """
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)

    # File identity
    file_hash = Column(String(64), nullable=False, index=True)           # SHA-256 (not unique - same file can be uploaded multiple times)
    file_path = Column(String(500), nullable=False, unique=True)         # Relative path: "parts/10900635/rev_A.pdf"
    original_filename = Column(String(255), nullable=False)              # Original name from upload

    # File metadata
    file_size = Column(Integer, nullable=False)                          # Bytes
    file_type = Column(String(10), nullable=False, index=True)           # "pdf", "step", "nc", "xlsx"
    mime_type = Column(String(100), nullable=False)                      # "application/pdf"

    # Lifecycle status
    status = Column(String(20), default="active", nullable=False, index=True)  # "temp", "active", "archived"

    # AuditMixin provides:
    # - created_at, updated_at, created_by, updated_by
    # - deleted_at, deleted_by (soft delete)
    # - version (optimistic locking)

    # Relationships
    links = relationship("FileLink", back_populates="file_record", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FileRecord(id={self.id}, file_path='{self.file_path}', status='{self.status}')>"


class FileLink(Base, AuditMixin):
    """
    Polymorphic file-entity relationship.

    Links FileRecord to business entities (Part, QuoteItem, TimeVisionEstimation, etc.).
    Business metadata (is_primary, revision) lives here.
    """
    __tablename__ = "file_links"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_records.id", ondelete="CASCADE"), nullable=False, index=True)

    # Polymorphic link (no DB-level FK - validated in application layer)
    entity_type = Column(String(50), nullable=False, index=True)         # "part", "quote_item", "timevision"
    entity_id = Column(Integer, nullable=False, index=True)              # FK to specific entity

    # Business metadata (belongs to LINK, not to FILE)
    is_primary = Column(Boolean, default=False, nullable=False)
    revision = Column(String(2), nullable=True)                          # "A", "B", "C"... (optional)
    link_type = Column(String(20), default="drawing", nullable=False)    # "drawing", "step_model", "nc_program"
    drawing_number = Column(String(50), nullable=True)                   # Číslo výkresu (z Part.drawing_number)

    # AuditMixin provides:
    # - created_at, updated_at, created_by, updated_by
    # - deleted_at, deleted_by (soft delete)
    # - version (optimistic locking)

    # Relationships
    file_record = relationship("FileRecord", back_populates="links")

    # Constraints
    __table_args__ = (
        # Composite index for entity lookup
        Index("ix_file_links_entity", "entity_type", "entity_id"),
        # Unique: one file can be linked to same entity only once
        UniqueConstraint("file_id", "entity_type", "entity_id", name="uq_file_link"),
    )

    def __repr__(self) -> str:
        return f"<FileLink(id={self.id}, file_id={self.file_id}, entity='{self.entity_type}:{self.entity_id}', primary={self.is_primary})>"
