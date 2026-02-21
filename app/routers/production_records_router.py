"""GESTIMA - Production Records API router

CRUD for production records (actual manufacturing data from Infor or manual entry).
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.production_record import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordResponse,
)
from app.services.production_record_service import ProductionRecordService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/part/{part_id}", response_model=List[ProductionRecordResponse])
async def get_production_records(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all production records for a part."""
    service = ProductionRecordService(db)
    return await service.list_by_part(part_id)


@router.get("/part/{part_id}/summary", response_model=dict)
async def get_production_summary(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get production summary for a part (avg times, batch counts)."""
    service = ProductionRecordService(db)
    return await service.get_summary_by_part(part_id)


@router.get("/{record_id}", response_model=ProductionRecordResponse)
async def get_production_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single production record by ID."""
    service = ProductionRecordService(db)
    record = await service.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Production record nenalezen")
    return ProductionRecordResponse.model_validate(record)


@router.post("/", response_model=ProductionRecordResponse, status_code=201)
async def create_production_record(
    data: ProductionRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Create a new production record."""
    service = ProductionRecordService(db)
    record = await service.create(data, current_user.username)
    return ProductionRecordResponse.model_validate(record)


@router.post("/bulk", response_model=List[ProductionRecordResponse], status_code=201)
async def bulk_create_production_records(
    records: List[ProductionRecordCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Bulk create production records (for Infor import)."""
    if len(records) > 1000:
        raise HTTPException(status_code=400, detail="Max 1000 records per bulk operation")

    service = ProductionRecordService(db)
    created = await service.bulk_create(records, current_user.username)
    return [ProductionRecordResponse.model_validate(r) for r in created]


@router.put("/{record_id}", response_model=ProductionRecordResponse)
async def update_production_record(
    record_id: int,
    data: ProductionRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Update a production record."""
    service = ProductionRecordService(db)
    try:
        record = await service.update(record_id, data, current_user.username)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc))
        if "Version conflict" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    return ProductionRecordResponse.model_validate(record)


@router.delete("/{record_id}", status_code=204)
async def delete_production_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Soft-delete a production record."""
    service = ProductionRecordService(db)
    deleted = await service.delete(record_id, current_user.username)
    if not deleted:
        raise HTTPException(status_code=404, detail="Production record nenalezen")
