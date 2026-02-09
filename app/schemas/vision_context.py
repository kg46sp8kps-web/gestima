"""GESTIMA - Vision Context Schema

Pydantic schema for context extracted from PDF drawings via Claude Vision API.

UNIVERSAL SERVICE: Used in both Quote and Parts/Technology modules.

Vision extracts:
- Part number (for filename matching)
- Material designation (ČSN, EN, DIN, W.Nr, AISI)
- ROT/PRI hint (shape type from orthographic views)
- Confidence score (0.0-1.0)

See: ADR-042 (Proxy Features ML Architecture - Vision integration)
"""

from pydantic import BaseModel, Field
from typing import Literal


class VisionContext(BaseModel):
    """Context extracted from PDF drawing via Claude Vision API.

    Attributes:
        part_number: Part number from drawing titleblock or header
        material_designation: Material code (e.g., "11 500", "C45", "EN 10025")
        rot_pri_hint: Part type hint (ROT=turning, PRI=milling, UNKNOWN=cannot determine)
        confidence: Extraction confidence (0.0-1.0)
        extraction_timestamp: ISO 8601 timestamp
        pdf_filename: Source PDF filename
    """

    part_number: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Part number extracted from drawing"
    )

    material_designation: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Material designation (ČSN/EN/DIN/W.Nr/AISI)"
    )

    rot_pri_hint: Literal["ROT", "PRI", "UNKNOWN"] = Field(
        ...,
        description="Part type hint from drawing geometry (ROT=rotational, PRI=prismatic)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score (0.0-1.0)"
    )

    extraction_timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of extraction"
    )

    pdf_filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Source PDF filename"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "part_number": "JR811181",
                "material_designation": "11 500",
                "rot_pri_hint": "ROT",
                "confidence": 0.92,
                "extraction_timestamp": "2026-02-09T14:30:00Z",
                "pdf_filename": "JR811181_drawing.pdf"
            }
        }
    }
