"""GESTIMA - Part importer from Infor SLItems

Imports Parts (article_number, name, drawing info) from Infor SLItems IDO.
Uses generic InforImporterBase infrastructure.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
)
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


class PartImporter(InforImporterBase[Part]):
    """
    Importer for Part from Infor SLItems.

    Field mappings:
    - Item → article_number
    - Description → name
    - DrawingNbr → drawing_number
    - Revision → customer_revision
    - RybTridaNazev1 → status (Nabídka→quote, Aktivní→active)
    - FamilyCode → (info only, not imported)
    """

    # Infor RybTridaNazev1 → Gestima PartStatus
    STATUS_MAP = {
        "Nabídka": "quote",
        "Aktivní": "active",
    }

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for Part import."""
        return InforImporterConfig(
            entity_name="Part",
            ido_name="SLItems",
            field_mappings=[
                # Required fields
                FieldMapping("Item", "article_number", required=True),
                # Optional fields
                FieldMapping("Description", "name", required=False),
                FieldMapping("DrawingNbr", "drawing_number", required=False),
                FieldMapping("Revision", "customer_revision", required=False),
                FieldMapping("RybTridaNazev1", "infor_status", required=False),
                FieldMapping("FamilyCode", "family_code", required=False),
            ],
            duplicate_check_field="article_number"
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Custom mapping for Part.

        Auto-generates part_number (10XXXXXX pattern).

        Args:
            row: Raw Infor row
            basic_mapped: Basic field-mapped data
            db: Database session

        Returns:
            Dict with additional custom fields
        """
        custom = {}

        # part_number will be generated in create_entity
        custom["part_number"] = None

        # RybTridaNazev1 → status (Nabídka→quote, Aktivní→active)
        infor_status = basic_mapped.get("infor_status")
        if infor_status and infor_status in self.STATUS_MAP:
            custom["status"] = self.STATUS_MAP[infor_status]
        else:
            custom["status"] = "quote"  # Default for unknown

        # Remove temp fields (info only, not in Part model)
        custom["family_code"] = None
        custom["infor_status"] = None

        return custom

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Part:
        """
        Create Part instance with auto-generated part_number.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            Part instance (not yet committed)
        """
        # Generate part_number (10XXXXXX pattern - same as parts_router)
        part_number = await NumberGenerator.generate_part_number(db)

        part = Part(
            part_number=part_number,
            article_number=mapped_data.get("article_number"),
            name=mapped_data.get("name"),
            drawing_number=mapped_data.get("drawing_number"),
            customer_revision=mapped_data.get("customer_revision"),
            # Defaults for imported parts
            revision="A",
            status=mapped_data.get("status", "quote"),
            source="infor_import",
            length=0.0
        )

        logger.info(
            f"Created Part: {part.part_number} (article_number={part.article_number})"
        )
        return part

    async def update_entity(
        self,
        existing: Part,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Update existing Part (only mutable fields).

        Does NOT update part_number (immutable identifier).
        Only overwrites fields when Infor provides a non-empty value
        to preserve user-entered data.

        Args:
            existing: Existing Part instance
            mapped_data: New mapped data
            db: Database session
        """
        # Update only non-empty values (don't overwrite user data with None)
        for field in ("name", "drawing_number", "customer_revision", "status"):
            value = mapped_data.get(field)
            if value:  # Only overwrite if Infor provides a non-empty value
                setattr(existing, field, value)

        logger.info(f"Updated Part: {existing.part_number} (article_number={existing.article_number})")

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Part]:
        """
        Check if Part with same article_number exists.

        Args:
            mapped_data: Mapped data dict
            db: Database session

        Returns:
            Existing Part or None
        """
        article_number = mapped_data.get("article_number")
        if not article_number:
            return None

        result = await db.execute(
            select(Part).where(
                Part.article_number == article_number,
                Part.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
