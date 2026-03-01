"""GESTIMA - Production Planner Router

Endpointy pro vizualni Gantt dispečink VP.

Endpointy:
  GET  /data      — VP-centrické Gantt data
  PUT  /priority  — Nastavit prioritu VP
  PUT  /fire      — Toggle hot flag
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.production_priority import (
    ProductionPrioritySetRequest,
    ProductionPriorityFireRequest,
    ProductionPriorityTierRequest,
)
from app.services import production_planner_service
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_infor_client() -> InforAPIClient:
    if not settings.INFOR_API_URL:
        raise HTTPException(
            status_code=501,
            detail="Infor API integration not configured. Set INFOR_API_URL in .env"
        )
    return InforAPIClient(
        base_url=settings.INFOR_API_URL,
        config=settings.INFOR_CONFIG,
        username=settings.INFOR_USERNAME,
        password=settings.INFOR_PASSWORD,
        verify_ssl=False,
    )


@router.get("/data")
async def get_planner_data(
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: InforAPIClient = Depends(get_infor_client),
):
    """VP-centrické Gantt data pro Production Planner."""
    try:
        data = await production_planner_service.fetch_planner_data(
            db=db,
            infor_client=client,
            record_cap=limit,
        )
        return data
    except Exception as exc:
        logger.error("production_planner fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba při načítání dat plánovače: {exc}")


@router.put("/priority")
async def set_priority(
    body: ProductionPrioritySetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nastavit prioritu VP."""
    entry = await production_planner_service.set_priority(
        db=db,
        job=body.job,
        suffix=body.suffix,
        priority=body.priority,
        username=current_user.username,
    )
    return {
        "job": entry.infor_job,
        "suffix": entry.infor_suffix,
        "priority": entry.priority,
        "is_hot": entry.is_hot,
    }


@router.put("/fire")
async def set_fire(
    body: ProductionPriorityFireRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle hot flag na VP."""
    entry = await production_planner_service.set_hot(
        db=db,
        job=body.job,
        suffix=body.suffix,
        is_hot=body.is_hot,
        username=current_user.username,
    )
    return {
        "job": entry.infor_job,
        "suffix": entry.infor_suffix,
        "priority": entry.priority,
        "is_hot": entry.is_hot,
    }


@router.put("/tier")
async def set_tier(
    body: ProductionPriorityTierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nastavit tier (hot/urgent/normal) na VP."""
    entry = await production_planner_service.set_tier(
        db=db,
        job=body.job,
        suffix=body.suffix,
        tier=body.tier,
        username=current_user.username,
    )
    return {
        "job": entry.infor_job,
        "suffix": entry.infor_suffix,
        "priority": entry.priority,
        "is_hot": entry.is_hot,
    }


