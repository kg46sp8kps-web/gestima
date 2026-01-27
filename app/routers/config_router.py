"""GESTIMA - System Configuration API router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.config import SystemConfig, SystemConfigResponse, SystemConfigUpdate
from app.models import User
from app.models.enums import UserRole
from app.dependencies import get_current_user, require_role
from app.db_helpers import set_audit

router = APIRouter()


@router.get("/", response_model=List[SystemConfigResponse])
async def get_all_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get all system configuration (admin only)"""
    result = await db.execute(
        select(SystemConfig).order_by(SystemConfig.key)
    )
    configs = result.scalars().all()
    return configs


@router.get("/{key}", response_model=SystemConfigResponse)
async def get_config_by_key(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get specific config by key (admin only)"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    return config


@router.put("/{key}", response_model=SystemConfigResponse)
async def update_config(
    key: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Update system configuration (admin only)"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    # Optimistic locking
    if config.version != data.version:
        raise HTTPException(
            status_code=409,
            detail="Configuration was modified by another user. Please refresh and try again."
        )

    # Update fields
    if data.value_float is not None:
        config.value_float = data.value_float
    if data.description is not None:
        config.description = data.description

    set_audit(config, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(config)
        return config
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
