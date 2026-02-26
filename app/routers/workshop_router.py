"""GESTIMA - Workshop Router

Dílnická aplikace — frontend pro iPadové terminály.

Endpointy:
  GET  /api/workshop/jobs                              — Fronta práce z Inforu (SLJobRoutes)
  GET  /api/workshop/jobs/{job}/operations             — Operace zakázky (SLJobRoutes per-job)
  GET  /api/workshop/jobs/{job}/operations/{oper}/materials — Materiály k operaci (IteCzTsdSLJobMatls)
  POST /api/workshop/transactions                      — Uložit transakci do bufferu (pending)
  POST /api/workshop/transactions/{id}/post            — Odeslat transakci do Inforu
  GET  /api/workshop/transactions                      — Moje transakce
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.workshop_transaction import (
    WorkshopTransactionCreate,
    WorkshopTransactionResponse,
)
from app.services import workshop_service
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_infor_client() -> InforAPIClient:
    """Dependency pro InforAPIClient — stejná konfigurace jako v infor_router."""
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


@router.get("/queue", response_model=List[dict])
async def get_wc_queue(
    wc: Optional[str] = Query(None, description="Filtr pracoviště (WC kód z Inforu)"),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Vrátí frontu práce pro pracoviště — flat seznam operací (Type=J, JobStat=R/F).

    Každý řádek = jedna operace (bez deduplikace, na rozdíl od /jobs).
    Seřazeno dle plánovaného začátku operace (OpDatumSt ASC z JbrDetails).
    """
    try:
        queue = await workshop_service.fetch_wc_queue(
            infor_client=client,
            wc=wc,
            record_cap=limit,
        )
        return queue
    except Exception as exc:
        logger.error(f"fetch_wc_queue failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.get("/jobs", response_model=List[dict])
async def get_open_jobs(
    wc: Optional[str] = Query(None, description="Filtr pracoviště (WC kód z Inforu)"),
    limit: int = Query(500, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Vrátí otevřené výrobní zakázky z Inforu (Type=J, JobStat=R).

    Volitelně filtruje dle pracoviště (wc parametr).
    SLJobRoutes vrací 1 řádek/operaci — deduplikace Python-side.
    """
    try:
        jobs = await workshop_service.fetch_open_jobs(
            infor_client=client,
            wc_filter=wc,
            record_cap=limit,
        )
        return jobs
    except Exception as exc:
        logger.error(f"fetch_open_jobs failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.get("/operations", response_model=List[dict])
async def get_job_operations(
    job: str = Query(..., description="Číslo zakázky (může obsahovat lomítko, proto query param)"),
    suffix: str = Query("0", description="Suffix zakázky"),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Vrátí operace konkrétní zakázky z Inforu (SLJobRoutes per-job).

    Job číslo je query parametr (ne path), protože Infor job čísla
    mohou obsahovat lomítka (např. '22VP10/250') která způsobují 404 v path.

    Poznámka: SLJobOpers IDO neexistuje — operace čteme ze SLJobRoutes.
    """
    try:
        operations = await workshop_service.fetch_job_operations(
            infor_client=client,
            job=job,
            suffix=suffix,
        )
        return operations
    except Exception as exc:
        logger.error(f"fetch_job_operations failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.get("/materials", response_model=List[dict])
async def get_operation_materials(
    job: str = Query(..., description="Číslo zakázky"),
    oper: str = Query(..., description="Číslo operace"),
    suffix: str = Query("0", description="Suffix zakázky"),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Vrátí materiálovou spotřebu k operaci zakázky (IteCzTsdSLJobMatls).

    Pole: Material, Desc, TotCons, Qty, BatchCons
    """
    try:
        materials = await workshop_service.fetch_job_materials(
            infor_client=client,
            job=job,
            suffix=suffix,
            oper_num=oper,
        )
        return materials
    except Exception as exc:
        logger.error(f"fetch_job_materials failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.post("/transactions", response_model=WorkshopTransactionResponse)
async def create_transaction(
    data: WorkshopTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uloží dílnickou transakci do lokálního bufferu (status=pending).

    Transakci je následně třeba odeslat do Inforu přes POST /transactions/{id}/post.
    """
    try:
        tx = await workshop_service.create_transaction(db, data, current_user)
        return WorkshopTransactionResponse.model_validate(tx)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"create_transaction failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


@router.post("/transactions/{tx_id}/post", response_model=WorkshopTransactionResponse)
async def post_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Odešle transakci do Inforu přes IteCzTsdUpdateDcSfc34Sp.

    BEZPEČNOST: Zápis je tvrdě zablokován pokud INFOR_CONFIG=LIVE.
    Nikdy nepište do živé Infor databáze z vývojového prostředí.
    """
    if settings.INFOR_CONFIG.upper() == "LIVE":
        raise HTTPException(
            status_code=403,
            detail=(
                "Zápis do Inforu je zablokován: INFOR_CONFIG=LIVE. "
                "Přepněte na testovací konfiguraci (INFOR_CONFIG=TEST) a restartujte backend."
            )
        )
    try:
        tx = await workshop_service.post_transaction_to_infor(db, tx_id, client, current_user)
        return WorkshopTransactionResponse.model_validate(tx)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"post_transaction failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


@router.get("/transactions", response_model=List[WorkshopTransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Vrátí transakce aktuálně přihlášeného dělníka (seřazené sestupně).
    """
    try:
        txs = await workshop_service.list_my_transactions(db, current_user, skip, limit)
        return [WorkshopTransactionResponse.model_validate(tx) for tx in txs]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"list_transactions failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")
