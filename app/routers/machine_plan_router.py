"""GESTIMA - Machine Plan DnD Router

Endpointy pro mistrovske planovani operaci na pracovisti (DnD).

Endpointy:
  GET    /plan?wc=...    — Merged plan (lokalni poradi + Infor data)
  PATCH  /reorder        — Bulk prerazeni pozic
  POST   /entries        — Pridat operaci do planu
  DELETE /entries        — Odebrat operaci z planu
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.machine_plan import (
    MachinePlanReorderRequest,
    MachinePlanAddRequest,
    MachinePlanRemoveRequest,
)
from app.services import machine_plan_service
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


@router.get("/plan")
async def get_plan(
    wc: str = Query(..., min_length=1, description="Kod pracoviste (WC)"),
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: InforAPIClient = Depends(get_infor_client),
):
    """Vrati merged plan: lokalni poradi + cerstva Infor data."""
    try:
        plan = await machine_plan_service.get_plan(
            db=db,
            wc=wc,
            infor_client=client,
            record_cap=limit,
        )
        return plan
    except Exception as exc:
        logger.error("machine_plan get_plan failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba pri nacitani planu: {exc}")


@router.patch("/reorder")
async def reorder_plan(
    body: MachinePlanReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk prerazeni pozic — mistr pretahl DnD."""
    count = await machine_plan_service.reorder(
        db=db,
        wc=body.wc,
        ordered_keys=[k.model_dump() for k in body.ordered_keys],
        username=current_user.username,
    )
    return {"updated": count}


@router.post("/entries")
async def add_entry(
    body: MachinePlanAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pridat operaci do planu."""
    entry = await machine_plan_service.add_to_plan(
        db=db,
        wc=body.wc,
        job=body.job,
        suffix=body.suffix,
        oper_num=body.oper_num,
        username=current_user.username,
        position=body.position,
    )
    return {
        "id": entry.id,
        "wc": entry.wc,
        "job": entry.infor_job,
        "suffix": entry.infor_suffix,
        "oper_num": entry.oper_num,
        "position": entry.position,
    }


@router.delete("/entries")
async def remove_entry(
    body: MachinePlanRemoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Odebrat operaci z planu (soft-delete)."""
    removed = await machine_plan_service.remove_from_plan(
        db=db,
        wc=body.wc,
        job=body.job,
        suffix=body.suffix,
        oper_num=body.oper_num,
        username=current_user.username,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Zaznam nenalezen")
    return {"removed": True}
