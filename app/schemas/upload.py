"""GESTIMA - Upload schemas"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TempUploadResponse(BaseModel):
    """Response from temporary file upload"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "temp_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "filename": "drawing.pdf",
                "size": 524288,
                "uploaded_at": "2026-01-31T10:00:00Z"
            }
        }
    )

    temp_id: str = Field(..., description="UUID for temporary file")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., gt=0, le=10485760, description="File size in bytes (max 10MB)")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
