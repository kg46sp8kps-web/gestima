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

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
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
from app.services.workshop_cache_service import workshop_cache

logger = logging.getLogger(__name__)
router = APIRouter()


class WorkshopMaterialIssueCreate(BaseModel):
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)
    material: str = Field(..., min_length=1, max_length=60)
    um: Optional[str] = Field(None, max_length=20)
    qty: float = Field(..., gt=0)
    wc: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=30)
    lot: Optional[str] = Field(None, max_length=30)


class WorkshopOrderOperationCell(BaseModel):
    oper_num: str
    wc: str
    status: str
    state_text: Optional[str] = None


class WorkshopOrderMaterialCell(BaseModel):
    material: str
    status: str  # 'done' | 'idle'


class WorkshopOrderVpCandidate(BaseModel):
    job: str
    suffix: str
    job_stat: Optional[str] = None
    qty_released: Optional[float] = None
    qty_complete: Optional[float] = None
    qty_scrapped: Optional[float] = None
    item: Optional[str] = None
    customer_name: Optional[str] = None
    due_date: Optional[str] = None
    operations: List[WorkshopOrderOperationCell] = Field(default_factory=list)


class WorkshopOrderOverviewRow(BaseModel):
    row_id: str
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    delivery_code: Optional[str] = None
    delivery_name: Optional[str] = None
    co_num: str
    co_line: str
    co_release: str
    item: Optional[str] = None
    description: Optional[str] = None
    material_ready: bool = False
    qty_ordered: Optional[float] = None
    qty_shipped: Optional[float] = None
    qty_wip: Optional[float] = None
    due_date: Optional[str] = None
    promise_date: Optional[str] = None
    confirm_date: Optional[str] = None
    vp_candidates: List[WorkshopOrderVpCandidate] = Field(default_factory=list)
    selected_vp_job: Optional[str] = None
    operations: List[WorkshopOrderOperationCell] = Field(default_factory=list)
    materials: List[WorkshopOrderMaterialCell] = Field(default_factory=list)
    record_date: Optional[str] = None


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


@router.get("/queue")
async def get_wc_queue(
    wc: Optional[str] = Query(None, description="Filtr pracoviště (WC kód z Inforu)"),
    job: Optional[str] = Query(None, description="Filtr VP (substring čísla zakázky)"),
    sort_by: str = Query("OpDatumSt", description="Řazení: OpDatumSt|OpDatumSp|Job|OperNum|Wc|DerJobItem|JobDescription|QtyComplete|JobQtyReleased"),
    sort_dir: str = Query("asc", description="Směr řazení: asc|desc"),
    limit: int = Query(200, ge=1, le=1000),
    if_none_match: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Vrátí frontu práce pro pracoviště — flat seznam operací (Type=J, JobStat=R/F).

    Každý řádek = jedna operace (bez deduplikace, na rozdíl od /jobs).
    Seřazeno dle plánovaného začátku operace (OpDatumSt ASC z JbrDetails).
    """
    # Cache-first: pokud je cache warm, vrátit z ní
    if workshop_cache.is_warm("wc_queue"):
        etag = workshop_cache.get_etag("wc_queue")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        data = workshop_cache.get_wc_queue(
            wc=wc, job_filter=job, sort_by=sort_by, sort_dir=sort_dir, limit=limit,
        )
        return JSONResponse(
            content=data,
            headers={
                "ETag": etag,
                "X-Cache": "HIT",
                "X-Cache-Updated": (workshop_cache.get_updated_at("wc_queue") or "").isoformat() if workshop_cache.get_updated_at("wc_queue") else "",
            },
        )

    # Fallback: live fetch z Inforu
    try:
        queue = await workshop_service.fetch_wc_queue(
            infor_client=client,
            wc=wc,
            record_cap=limit,
            job_filter=job,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return JSONResponse(content=queue, headers={"X-Cache": "MISS"})
    except Exception as exc:
        logger.error(f"fetch_wc_queue failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.get("/orders-overview")
async def get_orders_overview(
    customer: Optional[str] = Query(None, description="Zákazník (kód)"),
    due_from: Optional[str] = Query(None, description="Termín od (YYYY-MM-DD)"),
    due_to: Optional[str] = Query(None, description="Termín do (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Hledání: zakázka/díl/popis"),
    limit: int = Query(2000, ge=1, le=5000),
    if_none_match: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """Přehled zakázek pro dispečink (zakázka + VP kandidáti + operace)."""
    # Cache-first
    if workshop_cache.is_warm("orders_overview"):
        etag = workshop_cache.get_etag("orders_overview")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        data = workshop_cache.get_orders_overview(
            customer=customer, due_from=due_from, due_to=due_to,
            search=search, limit=limit,
        )
        return JSONResponse(
            content=data,
            headers={
                "ETag": etag,
                "X-Cache": "HIT",
                "X-Cache-Updated": (workshop_cache.get_updated_at("orders_overview") or "").isoformat() if workshop_cache.get_updated_at("orders_overview") else "",
            },
        )

    # Fallback: live fetch
    try:
        rows = await workshop_service.fetch_orders_overview(
            infor_client=client,
            customer=customer,
            due_from=due_from,
            due_to=due_to,
            search=search,
            limit=limit,
        )
        return JSONResponse(content=rows, headers={"X-Cache": "MISS"})
    except Exception as exc:
        logger.error("fetch_orders_overview failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.get("/machine-plan")
async def get_machine_plan(
    wc: Optional[str] = Query(None, description="Filtr pracoviště (WC kód z Inforu)"),
    job: Optional[str] = Query(None, description="Filtr VP (substring čísla zakázky)"),
    sort_by: str = Query("OpDatumSt", description="Řazení: OpDatumSt|OpDatumSp|Job|OperNum|Wc|DerJobItem|JobDescription|QtyComplete|JobQtyReleased"),
    sort_dir: str = Query("asc", description="Směr řazení: asc|desc"),
    limit: int = Query(500, ge=1, le=2000),
    if_none_match: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Plán stroje — fronta operací včetně zásobníku (R/F/S/W) ze SLJobRoutes.

    Každý řádek obsahuje `JobStat` (R=Released, F=Firm, S=Scheduled, W=Waiting).
    """
    # Cache-first
    if workshop_cache.is_warm("machine_plan"):
        etag = workshop_cache.get_etag("machine_plan")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        data = workshop_cache.get_machine_plan(
            wc=wc, job_filter=job, sort_by=sort_by, sort_dir=sort_dir, limit=limit,
        )
        return JSONResponse(
            content=data,
            headers={
                "ETag": etag,
                "X-Cache": "HIT",
                "X-Cache-Updated": (workshop_cache.get_updated_at("machine_plan") or "").isoformat() if workshop_cache.get_updated_at("machine_plan") else "",
            },
        )

    # Fallback: live fetch
    try:
        rows = await workshop_service.fetch_machine_plan(
            infor_client=client,
            wc=wc,
            job_filter=job,
            sort_by=sort_by,
            sort_dir=sort_dir,
            record_cap=limit,
        )
        return JSONResponse(content=rows, headers={"X-Cache": "MISS"})
    except Exception as exc:
        logger.error("fetch_machine_plan failed: %s", exc, exc_info=True)
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
    sort_by: str = Query("OpDatumSt", description="Řazení: OpDatumSt|OpDatumSp|OperNum|Wc|QtyReleased|QtyComplete|ScrapQty"),
    sort_dir: str = Query("asc", description="Směr řazení: asc|desc"),
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
            sort_by=sort_by,
            sort_dir=sort_dir,
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
    sort_by: str = Query("Material", description="Řazení: Material|Desc|TotCons|Qty|BatchCons"),
    sort_dir: str = Query("asc", description="Směr řazení: asc|desc"),
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
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return materials
    except Exception as exc:
        logger.error(f"fetch_job_materials failed: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chyba komunikace s Inforem: {exc}")


@router.post("/material-issues", response_model=dict)
async def post_material_issue(
    data: WorkshopMaterialIssueCreate,
    current_user: User = Depends(get_current_user),
    client: InforAPIClient = Depends(get_infor_client),
):
    """
    Provede materiálový odvod pro konkrétní operaci VP.
    """
    try:
        emp_num = getattr(current_user, "infor_emp_num", None) or current_user.username
        result = await workshop_service.post_material_issue(
            infor_client=client,
            emp_num=emp_num,
            job=data.job,
            suffix=data.suffix,
            oper_num=data.oper_num,
            material=data.material,
            um=data.um,
            qty=data.qty,
            wc=data.wc,
            location=data.location,
            lot=data.lot,
        )
        # Invalidate cache after successful write
        workshop_cache.invalidate("wc_queue")
        workshop_cache.invalidate("machine_plan")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"post_material_issue failed: {exc}", exc_info=True)
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
        # Invalidate cache after successful Infor write
        workshop_cache.invalidate("wc_queue")
        workshop_cache.invalidate("machine_plan")
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
