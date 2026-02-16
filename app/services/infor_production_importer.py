"""GESTIMA - ProductionRecord importer from Infor SLJobRoutes

Imports ProductionRecords (actual production times) from Infor Job Routes IDO.
Uses generic InforImporterBase infrastructure with Part + WC resolution.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_record import ProductionRecord
from app.models.part import Part
from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
)
from app.services.infor_wc_mapper import InforWcMapper

logger = logging.getLogger(__name__)


class ProductionImporter(InforImporterBase[ProductionRecord]):
    """
    Importer for ProductionRecord from Infor SLJobRoutes.

    STUB field mappings (TBD after IDO discovery):
    - Job → infor_order_number
    - OperNum → operation_seq
    - Wc → infor_wc_code (resolved via InforWcMapper)
    - QtyComplete → batch_quantity
    - RunHrsTPc → planned_time_min (hours × 60)
    - ActRunHrs → actual_time_min (hours × 60)

    Requires Part resolution (article_number → part_id).
    """

    def __init__(self, wc_mapper: InforWcMapper):
        """
        Initialize importer with WC mapper.

        Args:
            wc_mapper: InforWcMapper instance for WC resolution
        """
        super().__init__()
        self.wc_mapper = wc_mapper

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for ProductionRecord import."""
        return InforImporterConfig(
            entity_name="ProductionRecord",
            ido_name="SLJobRoutes",
            field_mappings=[
                # Required fields
                FieldMapping("Job", "infor_order_number", required=True),
                FieldMapping("Item", "article_number", required=False),  # For Part lookup (removed after map_row_custom)
                # Optional fields
                FieldMapping("OperNum", "operation_seq", required=False, transform=int),
                FieldMapping("Wc", "infor_wc_code", required=False),
                FieldMapping("QtyComplete", "batch_quantity", required=False, transform=int),
                FieldMapping("RunHrsTPc", "planned_time_hours", required=False, transform=float),
                FieldMapping("ActRunHrs", "actual_time_hours", required=False, transform=float),
            ],
            duplicate_check_field="infor_order_number"
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Custom mapping for ProductionRecord.

        - Resolves part_id from article_number
        - Resolves work_center_id from Infor WC code
        - Converts hours to minutes

        Args:
            row: Raw Infor row
            basic_mapped: Basic field-mapped data
            db: Database session

        Returns:
            Dict with additional custom fields
        """
        custom = {}

        # Resolve part_id from article_number
        article_number = basic_mapped.get("article_number")
        if article_number:
            part_id = await self._resolve_part_id(article_number, db)
            custom["part_id"] = part_id
            if not part_id:
                logger.warning(f"Part not found for article_number '{article_number}'")
        else:
            custom["part_id"] = None

        # Resolve work_center_id via WC mapper
        infor_wc_code = basic_mapped.get("infor_wc_code")
        if infor_wc_code:
            wc_id, warning = await self.wc_mapper.resolve(infor_wc_code, db)
            custom["work_center_id"] = wc_id
            if warning:
                logger.warning(f"WC resolution failed: {warning}")
        else:
            custom["work_center_id"] = None

        # Convert hours to minutes
        planned_hours = basic_mapped.get("planned_time_hours")
        actual_hours = basic_mapped.get("actual_time_hours")

        custom["planned_time_min"] = float(planned_hours * 60) if planned_hours else None
        custom["actual_time_min"] = float(actual_hours * 60) if actual_hours else None

        # Set source
        custom["source"] = "infor"

        # Remove temp fields
        custom["article_number"] = None
        custom["infor_wc_code"] = None
        custom["planned_time_hours"] = None
        custom["actual_time_hours"] = None

        return custom

    async def _resolve_part_id(
        self,
        article_number: str,
        db: AsyncSession
    ) -> Optional[int]:
        """
        Resolve Part.id from article_number.

        Args:
            article_number: Article number from Infor
            db: Database session

        Returns:
            Part.id or None if not found
        """
        result = await db.execute(
            select(Part.id).where(
                Part.article_number == article_number,
                Part.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> ProductionRecord:
        """
        Create ProductionRecord instance.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            ProductionRecord instance (not yet committed)
        """
        record = ProductionRecord(
            part_id=mapped_data.get("part_id"),
            infor_order_number=mapped_data.get("infor_order_number"),
            batch_quantity=mapped_data.get("batch_quantity"),
            operation_seq=mapped_data.get("operation_seq"),
            work_center_id=mapped_data.get("work_center_id"),
            planned_time_min=mapped_data.get("planned_time_min"),
            actual_time_min=mapped_data.get("actual_time_min"),
            source="infor"
        )

        logger.info(
            f"Created ProductionRecord: order={record.infor_order_number}, "
            f"part_id={record.part_id}, seq={record.operation_seq}"
        )
        return record

    async def update_entity(
        self,
        existing: ProductionRecord,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Update existing ProductionRecord (only mutable fields).

        Args:
            existing: Existing ProductionRecord instance
            mapped_data: New mapped data
            db: Database session
        """
        # Update mutable fields
        existing.actual_time_min = mapped_data.get("actual_time_min")
        existing.batch_quantity = mapped_data.get("batch_quantity")
        existing.work_center_id = mapped_data.get("work_center_id")

        logger.info(
            f"Updated ProductionRecord: order={existing.infor_order_number}, "
            f"part_id={existing.part_id}"
        )

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[ProductionRecord]:
        """
        Check if ProductionRecord with same part_id + order + seq exists.

        Args:
            mapped_data: Mapped data dict
            db: Database session

        Returns:
            Existing ProductionRecord or None
        """
        part_id = mapped_data.get("part_id")
        infor_order_number = mapped_data.get("infor_order_number")
        operation_seq = mapped_data.get("operation_seq")

        if not part_id or not infor_order_number or not operation_seq:
            return None

        result = await db.execute(
            select(ProductionRecord).where(
                ProductionRecord.part_id == part_id,
                ProductionRecord.infor_order_number == infor_order_number,
                ProductionRecord.operation_seq == operation_seq,
                ProductionRecord.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
