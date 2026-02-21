"""GESTIMA - Drawing schemas

Pydantic validation schemas for Drawing model.
All validation follows L-009 (Field() with constraints).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DrawingResponse(BaseModel):
    """
    Drawing response schema.

    Built from FileRecord + FileLink data.
    Used by drawings_router (ADR-044 architecture).
    """
    model_config = ConfigDict(from_attributes=False)

    id: int = Field(..., description="FileRecord.id")
    part_id: int = Field(..., description="Part.id")
    drawing_number: Optional[str] = Field(None, max_length=50, description="Číslo výkresu (z Part.drawing_number)")
    filename: str = Field(..., max_length=255, description="Původní název souboru")
    original_filename: str = Field(..., max_length=255, description="Původní název souboru (duplicate for compatibility)")
    file_path: str = Field(..., max_length=500, description="Relativní cesta k souboru")
    file_type: Optional[str] = Field(None, max_length=10, description="Typ souboru (pdf, step)")
    file_size: Optional[int] = Field(None, gt=0, description="Velikost souboru v bytech")
    revision: Optional[str] = Field(None, max_length=2, pattern=r"^[A-Z]{1,2}$", description="Revize výkresu")
    is_primary: bool = Field(default=False, description="Primární výkres pro díl")
    created_at: datetime = Field(..., description="Datum vytvoření")
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
