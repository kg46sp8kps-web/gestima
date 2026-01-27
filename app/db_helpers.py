"""GESTIMA - Database helper functions (ADR-001)"""

import logging
from datetime import datetime
from typing import TypeVar, Type, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException

from app.database import Base, AuditMixin

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=Base)


def active_only(query):
    """Filter query to exclude soft-deleted records (deleted_at IS NULL)"""
    return query.filter_by(deleted_at=None)


async def soft_delete(db: AsyncSession, instance: AuditMixin, deleted_by: str = "system") -> None:
    """
    Soft delete: Mark record as deleted without removing from DB (ADR-001)

    Usage:
        part = await db.get(Part, part_id)
        await soft_delete(db, part, deleted_by="user@example.com")

    Raises:
        SQLAlchemyError: If database commit fails
    """
    instance.deleted_at = datetime.utcnow()
    instance.deleted_by = deleted_by

    try:
        await db.commit()
        logger.info(f"Soft deleted {instance.__class__.__name__}", extra={"deleted_by": deleted_by})
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in soft_delete: {e}", exc_info=True)
        raise


async def restore(db: AsyncSession, instance: AuditMixin) -> None:
    """
    Restore soft-deleted record

    Usage:
        part = await db.get(Part, part_id)
        await restore(db, part)

    Raises:
        SQLAlchemyError: If database commit fails
    """
    instance.deleted_at = None
    instance.deleted_by = None

    try:
        await db.commit()
        logger.info(f"Restored {instance.__class__.__name__}")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in restore: {e}", exc_info=True)
        raise


def is_deleted(instance: AuditMixin) -> bool:
    """Check if record is soft-deleted"""
    return instance.deleted_at is not None


# ============================================================================
# AUDIT TRAIL HELPERS
# ============================================================================

def set_audit(instance: AuditMixin, username: str, is_update: bool = False) -> None:
    """
    Set audit trail fields (created_by or updated_by)

    Eliminuje duplikaci L-002: Jeden helper místo manuálního nastavování v každém routeru

    Args:
        instance: Object with AuditMixin (Part, Operation, Feature, Batch, ...)
        username: Current user username (from current_user.username)
        is_update: True for updates (sets updated_by), False for creates (sets created_by)

    Usage:
        # CREATE
        part = Part(**data.model_dump())
        set_audit(part, current_user.username)

        # UPDATE
        set_audit(operation, current_user.username, is_update=True)
    """
    if is_update:
        instance.updated_by = username
    else:
        instance.created_by = username


async def get_active(db: AsyncSession, model: Type[T], id: int) -> Optional[T]:
    """Get single active (non-deleted) record by ID"""
    result = await db.execute(
        select(model).filter(model.id == id, model.deleted_at == None)
    )
    return result.scalar_one_or_none()


async def get_all_active(db: AsyncSession, model: Type[T]) -> list:
    """Get all active (non-deleted) records"""
    result = await db.execute(
        select(model).filter(model.deleted_at == None)
    )
    return result.scalars().all()


# ============================================================================
# TRANSACTION HELPERS (P2 Audit - reduce boilerplate)
# ============================================================================

async def safe_commit(
    db: AsyncSession,
    entity: Any = None,
    action: str = "database operation",
    integrity_error_msg: str = "Konflikt dat (duplicitní záznam nebo neplatné reference)",
    refresh: bool = True
) -> Any:
    """
    Commit with standard error handling.

    Eliminates repetitive try/except blocks in routers (L-008 compliance).

    Args:
        db: Database session
        entity: Entity to refresh after commit (optional)
        action: Description for error messages and logging
        integrity_error_msg: Custom message for IntegrityError (409)
        refresh: Whether to refresh entity after commit (default True)

    Returns:
        Refreshed entity if provided, otherwise None

    Raises:
        HTTPException 409: On IntegrityError (duplicate, FK violation)
        HTTPException 500: On other database errors

    Usage:
        # CREATE
        db.add(part)
        return await safe_commit(db, part, "vytváření dílu")

        # UPDATE
        part.name = new_name
        return await safe_commit(db, part, "aktualizace dílu")

        # DELETE (no entity to refresh)
        await db.delete(part)
        await safe_commit(db, action="mazání dílu")
        return {"message": "Smazáno"}
    """
    try:
        await db.commit()
        if entity and refresh:
            await db.refresh(entity)
        return entity
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error during {action}: {e}")
        raise HTTPException(status_code=409, detail=integrity_error_msg)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error during {action}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba databáze při {action}")
