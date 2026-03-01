"""GESTIMA - Operator Terminal Router"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import operator_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/active-jobs")
async def get_active_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aktivní práce operátora (rozběhnuté, nezastavené)."""
    return await operator_service.get_active_jobs(db, current_user.username)


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Statistiky operátora (dnešní/týdenní)."""
    return await operator_service.get_operator_stats(db, current_user.username)


@router.get("/workcenters")
async def get_workcenters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dostupná pracoviště s počtem operací."""
    return await operator_service.get_available_workcenters(db)


@router.get("/transaction-alerts")
async def get_transaction_alerts(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nevyřešené transakce operátora (pending/posting/failed) pro rychlé dořešení."""
    return await operator_service.get_transaction_alerts(db, current_user.username, limit=limit)
