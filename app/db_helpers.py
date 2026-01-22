"""GESTIMA - Database helper functions (ADR-001)"""

from datetime import datetime
from typing import TypeVar, Type, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from app.database import Base, AuditMixin

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
    """
    instance.deleted_at = datetime.utcnow()
    instance.deleted_by = deleted_by
    await db.commit()


async def restore(db: AsyncSession, instance: AuditMixin) -> None:
    """
    Restore soft-deleted record
    
    Usage:
        part = await db.get(Part, part_id)
        await restore(db, part)
    """
    instance.deleted_at = None
    instance.deleted_by = None
    await db.commit()


def is_deleted(instance: AuditMixin) -> bool:
    """Check if record is soft-deleted"""
    return instance.deleted_at is not None


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
