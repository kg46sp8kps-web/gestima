"""GESTIMA - ProductionRecord service

Business logic for production records (actual manufacturing data).
"""

import logging
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_record import (
    ProductionRecord,
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordResponse,
)
from app.models.work_center import WorkCenter
from app.db_helpers import set_audit, safe_commit

logger = logging.getLogger(__name__)


class ProductionRecordService:
    """Service for managing production records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_part(self, part_id: int, include_deleted: bool = False) -> List[ProductionRecordResponse]:
        """Get all production records for a part, ordered by date desc."""
        query = select(ProductionRecord).where(ProductionRecord.part_id == part_id)
        if not include_deleted:
            query = query.where(ProductionRecord.deleted_at.is_(None))
        query = query.order_by(
            ProductionRecord.production_date.desc().nullslast(),
            ProductionRecord.operation_seq.asc().nullslast(),
        )

        result = await self.db.execute(query)
        records = result.scalars().all()

        # Resolve WC names
        responses = []
        for record in records:
            resp = ProductionRecordResponse.model_validate(record)
            if record.work_center_id:
                wc = await self.db.get(WorkCenter, record.work_center_id)
                if wc:
                    resp.work_center_name = wc.name
            responses.append(resp)
        return responses

    async def get(self, record_id: int) -> Optional[ProductionRecord]:
        """Get single production record by ID."""
        result = await self.db.execute(
            select(ProductionRecord).where(
                ProductionRecord.id == record_id,
                ProductionRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: ProductionRecordCreate, username: str) -> ProductionRecord:
        """Create a new production record."""
        record = ProductionRecord(**data.model_dump())
        set_audit(record, username)
        self.db.add(record)
        record = await safe_commit(
            self.db, record,
            "vytváření production record",
            "Konflikt dat (neplatná reference na díl nebo pracoviště)",
        )
        logger.info(
            f"Created production record for part_id={data.part_id}, seq={data.operation_seq}",
            extra={"record_id": record.id, "user": username},
        )
        return record

    async def update(self, record_id: int, data: ProductionRecordUpdate, username: str) -> ProductionRecord:
        """Update an existing production record with optimistic locking."""
        record = await self.get(record_id)
        if not record:
            raise ValueError(f"Production record {record_id} not found")

        # Optimistic locking check
        if record.version != data.version:
            raise ValueError("Version conflict — record was modified by another user")

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for key, value in update_data.items():
            setattr(record, key, value)

        set_audit(record, username, is_update=True)
        record = await safe_commit(
            self.db, record,
            "aktualizace production record",
            "Konflikt dat",
        )
        logger.info(
            f"Updated production record {record_id}",
            extra={"record_id": record_id, "user": username},
        )
        return record

    async def delete(self, record_id: int, username: str) -> bool:
        """Soft-delete a production record."""
        record = await self.get(record_id)
        if not record:
            return False

        from app.db_helpers import soft_delete
        await soft_delete(self.db, record, deleted_by=username)
        logger.info(
            f"Deleted production record {record_id}",
            extra={"record_id": record_id, "user": username},
        )
        return True

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

        # Aggregate by infor_order_number for unique batches
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
