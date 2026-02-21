"""GESTIMA - Infor Sync State Models

Models for tracking Infor Smart Polling Sync state and audit logs.
Manages per-step configuration, watermarks, and sync history.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index

from app.database import Base


class SyncState(Base):
    """Per-step sync configuration and watermark state."""
    __tablename__ = "sync_states"

    id = Column(Integer, primary_key=True, index=True)

    # Step identifier (unique) — "parts", "materials", "documents", etc.
    step_name = Column(String(50), unique=True, nullable=False, index=True)

    # IDO query config
    ido_name = Column(String(100), nullable=False)
    properties = Column(Text, nullable=False)  # Comma-separated field list
    date_field = Column(String(50), default="RecordDate", nullable=False)
    filter_template = Column(Text, nullable=True)  # Base filter without date

    # Sync config
    interval_seconds = Column(Integer, default=30, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)

    # Watermark — last successful sync time
    last_sync_at = Column(DateTime, nullable=True)

    # Last run stats
    last_error = Column(Text, nullable=True)
    created_count = Column(Integer, default=0, nullable=False)
    updated_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SyncLog(Base):
    """Audit trail for sync executions."""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Step identifier
    step_name = Column(String(50), nullable=False, index=True)

    # Execution result
    status = Column(String(20), nullable=False)  # "success", "error", "skipped"
    fetched_count = Column(Integer, default=0, nullable=False)
    created_count = Column(Integer, default=0, nullable=False)
    updated_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)

    # Performance
    duration_ms = Column(Integer, nullable=True)

    # Error details
    error_message = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('ix_sync_logs_step_created', 'step_name', 'created_at'),
    )


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class SyncStateRead(BaseModel):
    """Response schema for SyncState."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_name: str
    ido_name: str
    properties: str
    date_field: str
    filter_template: Optional[str] = None
    interval_seconds: int
    enabled: bool
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_count: int
    updated_count: int
    error_count: int
    created_at: datetime
    updated_at: datetime


class SyncStateUpdate(BaseModel):
    """Update schema for SyncState."""
    enabled: Optional[bool] = None
    interval_seconds: Optional[int] = Field(None, ge=10, le=3600)


class SyncLogRead(BaseModel):
    """Response schema for SyncLog."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_name: str
    status: str
    fetched_count: int
    created_count: int
    updated_count: int
    error_count: int
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime


class SyncStatusResponse(BaseModel):
    """Overall sync status response."""
    running: bool
    steps: list[SyncStateRead]


class SyncTriggerResponse(BaseModel):
    """Manual sync trigger response."""
    status: str
    step_name: str
    fetched: int
    created: int
    updated: int
    errors: int
    duration_ms: int
