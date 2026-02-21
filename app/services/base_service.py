"""GESTIMA - Generic CRUD Service base class

Eliminates ~500 LOC of repeated CRUD boilerplate across services.
Each concrete service inherits BaseCrudService and overrides only domain-specific logic.

Usage:
    class FeatureService(BaseCrudService[Feature, FeatureCreate, FeatureUpdate]):
        model = Feature
        entity_name = "krok"

    # Automatically gets: list_active(), get(), create(), update(), delete()
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, AuditMixin
from app.db_helpers import set_audit, safe_commit, soft_delete

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=Base)
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")


class BaseCrudService(Generic[TModel, TCreate, TUpdate]):
    """Generic async CRUD service with soft-delete + optimistic locking.

    Class attributes to set:
        model: SQLAlchemy model class
        entity_name: Czech name for logging/errors (e.g. "krok", "partner")
        default_order: Optional tuple of order_by clauses
        parent_field: Optional FK field name for parent-scoped lists (e.g. "operation_id")
    """

    model: Type[TModel]
    entity_name: str = "záznam"
    default_order: tuple = ()
    parent_field: Optional[str] = None

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── LIST ──────────────────────────────────────────────────────
    async def list_active(
        self,
        parent_id: Optional[int] = None,
        extra_filters: Optional[list] = None,
    ) -> List[TModel]:
        """List active (non-deleted) records, optionally scoped to parent."""
        query = select(self.model).where(self.model.deleted_at.is_(None))

        if parent_id is not None and self.parent_field:
            query = query.where(getattr(self.model, self.parent_field) == parent_id)

        if extra_filters:
            for f in extra_filters:
                query = query.where(f)

        if self.default_order:
            query = query.order_by(*self.default_order)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── GET ───────────────────────────────────────────────────────
    async def get(self, record_id: int) -> Optional[TModel]:
        """Get single active record by ID."""
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == record_id,
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_404(self, record_id: int) -> TModel:
        """Get record or raise ValueError (router converts to 404)."""
        record = await self.get(record_id)
        if not record:
            raise ValueError(f"{self.entity_name} {record_id} nenalezen")
        return record

    # ── CREATE ────────────────────────────────────────────────────
    async def create(self, data: TCreate, username: str) -> TModel:
        """Create a new record with audit trail."""
        record = self.model(**data.model_dump())
        set_audit(record, username)
        self.db.add(record)

        record = await safe_commit(
            self.db, record,
            f"vytváření {self.entity_name}",
            f"Konflikt dat (neplatná reference)",
        )
        logger.info(
            f"Created {self.entity_name} id={record.id}",
            extra={"record_id": record.id, "user": username},
        )
        return record

    # ── UPDATE ────────────────────────────────────────────────────
    async def update(
        self,
        record_id: int,
        data: TUpdate,
        username: str,
    ) -> TModel:
        """Update with optimistic locking (ADR-008)."""
        record = await self.get_or_404(record_id)

        # Optimistic locking
        if hasattr(data, "version") and record.version != data.version:
            raise ValueError(
                "Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
            )

        exclude = {"version"}
        update_data = data.model_dump(exclude_unset=True, exclude=exclude)

        # Hook for subclass validation (e.g. locked fields)
        self._validate_update(record, update_data)

        for key, value in update_data.items():
            setattr(record, key, value)

        set_audit(record, username, is_update=True)

        record = await safe_commit(
            self.db, record,
            f"aktualizace {self.entity_name}",
        )
        logger.info(
            f"Updated {self.entity_name} id={record_id}",
            extra={"record_id": record_id, "user": username},
        )
        return record

    def _validate_update(self, record: TModel, update_data: dict) -> None:
        """Override in subclass for domain-specific update validation.

        Raise HTTPException or ValueError to block the update.
        """
        pass

    # ── DELETE ────────────────────────────────────────────────────
    async def delete(self, record_id: int, username: str) -> bool:
        """Soft-delete a record."""
        record = await self.get(record_id)
        if not record:
            return False

        await soft_delete(self.db, record, deleted_by=username)
        logger.info(
            f"Deleted {self.entity_name} id={record_id}",
            extra={"record_id": record_id, "user": username},
        )
        return True

    async def hard_delete(self, record_id: int, username: str) -> bool:
        """Permanently delete a record (use sparingly)."""
        record = await self.get(record_id)
        if not record:
            return False

        entity_info = f"{self.entity_name} id={record_id}"
        await self.db.delete(record)
        await safe_commit(self.db, action=f"mazání {self.entity_name}")
        logger.info(f"Hard deleted {entity_info}", extra={"user": username})
        return True
