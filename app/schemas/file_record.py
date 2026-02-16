"""GESTIMA - FileRecord and FileLink schemas

Pydantic validation schemas for centralized file management (ADR-044).
All validation follows L-009 (Field() with constraints).

FileRecord:
- Physical file storage registry
- SHA-256 hash for integrity
- Status lifecycle (temp → active → archived)

FileLink:
- Polymorphic entity-file relationships
- Business metadata (is_primary, revision) lives here
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FileRecordResponse(BaseModel):
    """Response schema for FileRecord (from database)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_hash: str = Field(
        ...,
        max_length=64,
        min_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 hash souboru (pro integritu)"
    )
    file_path: str = Field(..., max_length=500, description="Relativní cesta k souboru (např. 'parts/10900635/rev_A.pdf')")
    original_filename: str = Field(..., max_length=255, description="Původní název souboru od uživatele")
    file_size: int = Field(..., gt=0, description="Velikost souboru v bytech")
    file_type: str = Field(..., max_length=10, description="Typ souboru (pdf, step, nc, xlsx)")
    mime_type: str = Field(..., max_length=100, description="MIME type (např. 'application/pdf')")
    status: str = Field(
        ...,
        max_length=20,
        pattern=r"^(temp|active|archived)$",
        description="Status životního cyklu souboru"
    )
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = Field(None, max_length=100)
    updated_by: Optional[str] = Field(None, max_length=100)


class FileLinkResponse(BaseModel):
    """Response schema for FileLink (from database)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int = Field(..., gt=0, description="ID FileRecord záznamu")
    entity_type: str = Field(..., max_length=50, description="Typ entity (part, quote_item, timevision)")
    entity_id: int = Field(..., gt=0, description="ID konkrétní entity")
    is_primary: bool = Field(default=False, description="Primární soubor pro entitu")
    revision: Optional[str] = Field(
        None,
        max_length=2,
        pattern=r"^[A-Z]{1,2}$",
        description="Revize (A, B, C...)"
    )
    link_type: str = Field(
        ...,
        max_length=20,
        description="Typ vazby (drawing, step_model, nc_program)"
    )
    created_at: datetime
    created_by: Optional[str] = Field(None, max_length=100)


class FileWithLinksResponse(FileRecordResponse):
    """FileRecord response extended with links"""
    links: list[FileLinkResponse] = Field(
        default_factory=list,
        description="Seznam vazeb na entity"
    )


class FileListResponse(BaseModel):
    """Response for listing files with filters"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    {
                        "id": 1,
                        "file_hash": "a" * 64,
                        "file_path": "parts/10900635/rev_A.pdf",
                        "original_filename": "výkres_v3.pdf",
                        "file_size": 2097152,
                        "file_type": "pdf",
                        "mime_type": "application/pdf",
                        "status": "active",
                        "created_at": "2026-02-15T10:00:00Z",
                        "updated_at": "2026-02-15T10:00:00Z",
                        "created_by": "admin",
                        "links": [
                            {
                                "id": 1,
                                "file_id": 1,
                                "entity_type": "part",
                                "entity_id": 123,
                                "is_primary": True,
                                "revision": "A",
                                "link_type": "drawing",
                                "created_at": "2026-02-15T10:00:00Z",
                                "created_by": "admin"
                            }
                        ]
                    }
                ],
                "total": 1
            }
        }
    )

    files: list[FileWithLinksResponse] = Field(
        default_factory=list,
        description="Seznam souborů"
    )
    total: int = Field(..., ge=0, description="Celkový počet souborů")


class FileLinkRequest(BaseModel):
    """Request schema for linking file to entity"""
    entity_type: str = Field(..., min_length=1, max_length=50, description="Typ entity (part, quote_item, timevision)")
    entity_id: int = Field(..., gt=0, description="ID entity")
    is_primary: bool = Field(default=False, description="Nastavit jako primární soubor")
    revision: Optional[str] = Field(
        None,
        max_length=2,
        pattern=r"^[A-Z]{1,2}$",
        description="Revize (volitelné, A-Z)"
    )
    link_type: str = Field(
        default="drawing",
        max_length=20,
        description="Typ vazby (drawing, step_model, nc_program)"
    )


class FileUploadResponse(FileRecordResponse):
    """Response after file upload (FileRecord + optional link)"""
    link: Optional[FileLinkResponse] = Field(
        None,
        description="Vazba na entitu (pokud byla vytvořena při uploadu)"
    )
