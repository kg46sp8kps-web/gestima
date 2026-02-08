"""GESTIMA - Drawing schemas

Pydantic validation schemas for Drawing model.
All validation follows L-009 (Field() with constraints).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DrawingBase(BaseModel):
    """Base drawing schema with common fields"""
    filename: str = Field(..., max_length=255, description="Původní název souboru")
    file_hash: str = Field(
        ...,
        max_length=64,
        min_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 hash souboru (pro deduplikaci)"
    )
    file_size: int = Field(..., gt=0, description="Velikost souboru v bytech")
    is_primary: bool = Field(default=False, description="Primární výkres pro díl")
    revision: str = Field(
        default="A",
        max_length=2,
        pattern=r"^[A-Z]{1,2}$",
        description="Revize výkresu (A, B, C...)"
    )
    file_type: str = Field(default="pdf", description="Typ souboru (pdf nebo step)")


class DrawingCreate(BaseModel):
    """
    Internal schema for creating drawing records.
    Used by DrawingService, not exposed in API directly.
    """
    part_id: int = Field(..., gt=0, description="ID dílu")
    filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    file_hash: str = Field(..., max_length=64, min_length=64, pattern=r"^[a-f0-9]{64}$")
    file_size: int = Field(..., gt=0)
    is_primary: bool = Field(default=False)
    revision: str = Field(default="A", max_length=2, pattern=r"^[A-Z]{1,2}$")
    file_type: str = Field(default="pdf")


class DrawingResponse(DrawingBase):
    """Drawing response schema (from database)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    file_path: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int
    file_exists: bool = Field(
        default=True,
        description="Zda soubor fyzicky existuje na disku (false = orphan record)"
    )


class DrawingListResponse(BaseModel):
    """Response for listing part's drawings"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "drawings": [
                    {
                        "id": 1,
                        "part_id": 123,
                        "filename": "bearing_housing_rev_A.pdf",
                        "file_hash": "a" * 64,
                        "file_size": 524288,
                        "is_primary": True,
                        "revision": "A",
                        "file_path": "drawings/10123456_2026-01-31_A.pdf",
                        "created_at": "2026-01-31T10:00:00Z",
                        "updated_at": "2026-01-31T10:00:00Z",
                        "created_by": "admin",
                        "version": 0
                    }
                ],
                "primary_id": 1
            }
        }
    )

    drawings: List[DrawingResponse] = Field(
        default_factory=list,
        description="Seznam výkresů (seřazeno: primární první, pak nejnovější)"
    )
    primary_id: Optional[int] = Field(
        None,
        description="ID primárního výkresu (pro zvýraznění ve frontend)"
    )


class DrawingUploadRequest(BaseModel):
    """Request schema for drawing upload (form data)"""
    revision: str = Field(
        default="A",
        max_length=2,
        pattern=r"^[A-Z]{1,2}$",
        description="Revize výkresu"
    )


class SetPrimaryRequest(BaseModel):
    """Request schema for setting primary drawing"""
    # No body needed - drawing_id from path parameter
    pass
