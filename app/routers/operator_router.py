"""GESTIMA - Operator Terminal Router"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import operator_service
from app.services.norm_performance_service import Period

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
    """Statistiky operátora (dnešní/týdenní/měsíční) včetně plnění norem."""
    return await operator_service.get_operator_stats(
        db, current_user.username, infor_emp_num=current_user.infor_emp_num,
    )


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


@router.get("/norm-summary")
async def get_norm_summary(
    period: Optional[Period] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agregované plnění norem operátora pro dashboard dlaždice.

    Buď period (day/week/month) nebo date_from + date_to pro vlastní interval.
    """
    from app.services.norm_performance_service import get_norm_summary as _get_summary, _EMPTY_SUMMARY

    emp_num = current_user.infor_emp_num
    if not emp_num:
        return dict(_EMPTY_SUMMARY)

    return await _get_summary(db, emp_num, period=period, date_from=date_from, date_to=date_to)


@router.get("/norm-details")
async def get_norm_details(
    period: Optional[Period] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-operace detail plnění norem pro drill-down overlay.

    Buď period (day/week/month) nebo date_from + date_to pro vlastní interval.
    """
    from app.services.norm_performance_service import get_norm_details as _get_details

    emp_num = current_user.infor_emp_num
    if not emp_num:
        return []

    return await _get_details(db, emp_num, period=period, date_from=date_from, date_to=date_to)
