"""GESTIMA - ProductionRecord service

Business logic for production records (actual manufacturing data).
Inherits BaseCrudService for standard CRUD, adds domain-specific methods.
"""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_record import (
    ProductionRecord,
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordResponse,
)
from app.models.work_center import WorkCenter
from app.db_helpers import set_audit
from app.services.base_service import BaseCrudService

logger = logging.getLogger(__name__)


class ProductionRecordService(BaseCrudService[ProductionRecord, ProductionRecordCreate, ProductionRecordUpdate]):
    model = ProductionRecord
    entity_name = "production record"
    default_order = ()
    parent_field = "part_id"

    # ── DOMAIN-SPECIFIC ──────────────────────────────────────────

    async def list_by_part(self, part_id: int, include_deleted: bool = False) -> List[ProductionRecordResponse]:
        """Get all production records for a part with WC name resolution."""
        query = (
            select(ProductionRecord)
            .options(selectinload(ProductionRecord.work_center))
            .where(ProductionRecord.part_id == part_id)
        )
        if not include_deleted:
            query = query.where(ProductionRecord.deleted_at.is_(None))
        query = query.order_by(
            ProductionRecord.production_date.desc().nullslast(),
            ProductionRecord.operation_seq.asc().nullslast(),
        )

        result = await self.db.execute(query)
        records = result.scalars().all()

        # Resolve WC names using preloaded relationship (no N+1 query)
        responses = []
        for record in records:
            resp = ProductionRecordResponse.model_validate(record)
            if record.work_center:
                resp.work_center_name = record.work_center.name
                resp.work_center_type = record.work_center.work_center_type.value if record.work_center.work_center_type else None
            responses.append(resp)
        return responses

    async def bulk_create(self, records: List[ProductionRecordCreate], username: str) -> List[ProductionRecord]:
        """Bulk create production records (for Infor import)."""
        created = []
        for data in records:
            record = ProductionRecord(**data.model_dump())
            set_audit(record, username)
            self.db.add(record)
            created.append(record)

        try:
            await self.db.commit()
            for record in created:
                await self.db.refresh(record)
        except Exception:
            await self.db.rollback()
            raise

        logger.info(
            f"Bulk created {len(created)} production records",
            extra={"count": len(created), "user": username},
        )
        return created

    async def get_summary_by_part(self, part_id: int) -> dict:
        """Get production summary for a part (avg times, batch counts)."""
        records = await self.list_by_part(part_id)

        if not records:
            return {
                "total_records": 0,
                "total_batches": 0,
                "avg_actual_time_min": None,
                "min_actual_time_min": None,
                "max_actual_time_min": None,
                "total_pieces_produced": 0,
            }

        order_numbers = set()
        actual_times = []
        total_pieces = 0

        for r in records:
            if r.infor_order_number:
                order_numbers.add(r.infor_order_number)
            if r.actual_time_min is not None:
                actual_times.append(r.actual_time_min)
            if r.batch_quantity is not None:
                total_pieces += r.batch_quantity

        return {
            "total_records": len(records),
            "total_batches": len(order_numbers),
            "avg_actual_time_min": sum(actual_times) / len(actual_times) if actual_times else None,
            "min_actual_time_min": min(actual_times) if actual_times else None,
            "max_actual_time_min": max(actual_times) if actual_times else None,
            "total_pieces_produced": total_pieces,
        }
