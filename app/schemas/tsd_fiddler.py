"""TSD Fiddler — Request/Response schemas.

Fiddler-verified START/END flow with machine transactions.
Completely separate from old Presunout-based industream_tsd schemas.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TsdFiddlerStartRequest(BaseModel):
    """Request for start-setup, start-work."""

    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field(default="0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)
    item: str = Field(default="", max_length=30, description="DerJobItem")
    whse: str = Field(default="MAIN", max_length=10)
    kapacity_guid: str = Field(default="0", max_length=50)


class TsdFiddlerEndWorkRequest(TsdFiddlerStartRequest):
    """Request for end-work — includes quantities + flags."""

    qty_complete: float = Field(default=0.0, ge=0)
    qty_scrapped: float = Field(default=0.0, ge=0)
    oper_complete: bool = False


class TsdFiddlerResponse(BaseModel):
    """Response from any TSD Fiddler operation."""

    status: str  # "ok" or "error"
    message: str = ""
    stroj: Optional[str] = None
    wc: Optional[str] = None
    sp_results: Optional[dict] = None  # debug info
