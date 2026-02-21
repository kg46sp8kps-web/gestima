"""GESTIMA - Drawing Import Schemas

Pydantic models for drawing import from network share.
2-step workflow: preview (scan + match) -> execute (import).
"""

from typing import Optional
from pydantic import BaseModel, Field


class ShareFileInfo(BaseModel):
    """Single file in a share folder."""
    filename: str = Field(..., max_length=255)
    file_size: int = Field(..., ge=0)
    file_type: str = Field(..., max_length=10)  # "pdf", "step"


class ShareFolderPreview(BaseModel):
    """Preview of a single folder from the share."""
    folder_name: str = Field(..., max_length=100, description="Folder name = article_number")
    matched_part_id: Optional[int] = Field(None, description="Part.id if matched")
    matched_part_number: Optional[str] = Field(None, max_length=8, description="Part.part_number")
    matched_article_number: Optional[str] = Field(None, max_length=50)
    pdf_files: list[ShareFileInfo] = Field(default_factory=list)
    step_files: list[ShareFileInfo] = Field(default_factory=list)
    primary_pdf: Optional[str] = Field(None, max_length=255, description="Suggested primary PDF filename")
    already_imported: bool = Field(False)
    status: str = Field(..., max_length=20, description="ready | no_match | already_imported | no_pdf")


class DrawingImportPreviewResponse(BaseModel):
    """Response for preview scan."""
    share_path: str = Field(...)
    total_folders: int = Field(..., ge=0)
    matched: int = Field(0, ge=0)
    unmatched: int = Field(0, ge=0)
    already_imported: int = Field(0, ge=0)
    ready: int = Field(0, ge=0)
    no_pdf: int = Field(0, ge=0)
    skipped: int = Field(0, ge=0, description="Folders skipped by prefix filter (46*, 47*)")
    folders: list[ShareFolderPreview] = Field(default_factory=list)


class ShareStatusResponse(BaseModel):
    """Response for share status check."""
    share_path: str = Field(...)
    is_accessible: bool = Field(...)
    total_folders: int = Field(0, ge=0)
    message: str = Field("")


class ImportFolderRequest(BaseModel):
    """Request to import a specific folder."""
    folder_name: str = Field(..., max_length=100)
    part_id: int = Field(..., gt=0)
    primary_pdf: str = Field(..., max_length=255, description="Filename of primary PDF")
    import_step: bool = Field(True, description="Also import STEP files")


class DrawingImportExecuteRequest(BaseModel):
    """Request to execute drawing import."""
    folders: list[ImportFolderRequest] = Field(..., min_length=1)


class DrawingImportExecuteResponse(BaseModel):
    """Response after import execution."""
    success: bool = Field(...)
    files_created: int = Field(0, ge=0)
    links_created: int = Field(0, ge=0)
    parts_updated: int = Field(0, ge=0)
    skipped: int = Field(0, ge=0)
    errors: list[str] = Field(default_factory=list)
