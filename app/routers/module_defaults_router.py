"""GESTIMA - Module Defaults API router (ADR-031)

Refactored to use ModuleDefaultsService.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.module_defaults import (
    ModuleDefaultsCreate,
    ModuleDefaultsUpdate,
    ModuleDefaultsResponse,
)
from app.services.module_defaults_service import ModuleDefaultsService

router = APIRouter()


@router.get("/module-defaults/{module_type}", response_model=ModuleDefaultsResponse)
async def get_module_defaults(
    module_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ModuleDefaultsService(db)
    defaults = await service.get_by_type(module_type)
    if not defaults:
        raise HTTPException(status_code=404, detail=f"Module defaults not found for type: {module_type}")
    return defaults


@router.post("/module-defaults", response_model=ModuleDefaultsResponse, status_code=201)
async def create_or_update_module_defaults(
    data: ModuleDefaultsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ModuleDefaultsService(db)
    return await service.upsert(data, current_user.username)


@router.put("/module-defaults/{module_type}", response_model=ModuleDefaultsResponse)
async def update_module_defaults(
    module_type: str,
    data: ModuleDefaultsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ModuleDefaultsService(db)
    try:
        return await service.update(module_type, data, current_user.username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/module-defaults/{module_type}", status_code=204)
async def delete_module_defaults(
    module_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ModuleDefaultsService(db)
    deleted = await service.delete(module_type, current_user.username)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Module defaults not found for type: {module_type}")
