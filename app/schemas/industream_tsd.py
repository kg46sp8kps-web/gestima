"""Industream TSD — Request/Response schemas.

Clean START/END pairing with machine transactions (2.har verified).
"""

from typing import Optional

from pydantic import BaseModel, Field


class TsdStartRequest(BaseModel):
    """Request for start-setup, end-setup, start-work."""

    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field(default="0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)
    wc: str = Field(default="", max_length=20, description="Work center")
    item: str = Field(default="", max_length=30, description="DerJobItem")
    whse: str = Field(default="MAIN", max_length=10, description="Warehouse")


class TsdEndWorkRequest(TsdStartRequest):
    """Request for end-work — includes quantities + flags."""

    qty_complete: float = Field(default=0.0, ge=0)
    qty_scrapped: float = Field(default=0.0, ge=0)
    oper_complete: bool = False
    job_complete: bool = False


class TsdResponse(BaseModel):
    """Response from any TSD operation."""

    status: str  # "ok" or "error"
    message: str = ""
    actual_hours: Optional[float] = None
    stroj: Optional[str] = None
    wc: Optional[str] = None
