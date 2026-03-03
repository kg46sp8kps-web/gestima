"""TSD Fiddler — Router.

Fiddler-verified START/END pairing with machine transactions.
Coexists with old /api/industream-tsd (Presunout flow).

Endpoints:
  POST /start-setup   — Infor WrapperSp(TT=1) + local TX
  POST /end-setup     — Infor InsWrapper(TT=2) + Kapacity + auto start_work + local TX
  POST /start-work    — Infor ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx(H) + local TX
  POST /end-work      — Infor InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx(J) + local TX
  GET  /diag/dcsfc    — Debug: read DcSfc + Mchtrx from Infor
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user
from app.models import User
from app.models.workshop_transaction import WorkshopTransaction
from app.models.enums import WorkshopTransType, WorkshopTxStatus
from app.schemas.tsd_fiddler import (
    TsdFiddlerEndWorkRequest,
    TsdFiddlerResponse,
    TsdFiddlerStartRequest,
)
from app.services import tsd_fiddler_service as fiddler
from app.services.tsd_fiddler_service import (
    TsdFiddlerError,
    TsdInfoBarError,
    TsdValidationError,
)
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tsd-fiddler", tags=["TSD Fiddler"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_infor_client() -> InforAPIClient:
    """Factory: create InforAPIClient from settings."""
    if not settings.INFOR_API_URL:
        raise HTTPException(
            status_code=501,
            detail="Infor API not configured (INFOR_API_URL)",
        )
    return InforAPIClient(
        base_url=settings.INFOR_API_URL,
        config=settings.INFOR_CONFIG,
        username=settings.INFOR_USERNAME,
        password=settings.INFOR_PASSWORD,
        verify_ssl=False,
    )


def _resolve_emp_num(user: Any) -> str:
    """Resolve Infor employee number from user object."""
    for attr in ("infor_emp_num", "username"):
        val = getattr(user, attr, None)
        if val and str(val).strip().isdigit():
            return str(val).strip()
    return "1"


async def _record_tsd_tx(
    db: AsyncSession,
    username: str,
    trans_type: WorkshopTransType,
    job: str,
    suffix: str,
    oper_num: str,
    wc: str = "",
    item: str = "",
    qty_completed: float = 0.0,
    qty_scrapped: float = 0.0,
) -> None:
    """Create a local WorkshopTransaction record."""
    now = datetime.utcnow()
    tx = WorkshopTransaction(
        infor_job=job,
        infor_suffix=suffix,
        infor_item=item,
        oper_num=oper_num,
        wc=wc,
        trans_type=trans_type,
        status=WorkshopTxStatus.POSTED,
        posted_at=now,
        started_at=now if trans_type in (WorkshopTransType.START, WorkshopTransType.SETUP_START) else None,
        finished_at=now if trans_type in (WorkshopTransType.STOP, WorkshopTransType.SETUP_END) else None,
        qty_completed=qty_completed,
        qty_scrapped=qty_scrapped,
    )
    set_audit(tx, username)
    db.add(tx)
    await safe_commit(db)
    logger.info(
        "FIDDLER local tx: %s %s/%s oper=%s by %s",
        trans_type.value, job, suffix, oper_num, username,
    )


def _handle_fiddler_error(exc: TsdFiddlerError) -> HTTPException:
    """Convert TsdFiddlerError to appropriate HTTPException."""
    if isinstance(exc, TsdValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, TsdInfoBarError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start-setup", response_model=TsdFiddlerResponse)
async def start_setup(
    req: TsdFiddlerStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """Start Setup — Infor WrapperSp(TT=1) + local TX."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await fiddler.start_setup(
            infor_client=infor_client,
            emp_num=emp_num,
            job=req.job,
            suffix=req.suffix,
            oper_num=req.oper_num,
        )
        await _record_tsd_tx(
            db, user.username, WorkshopTransType.SETUP_START,
            req.job, req.suffix, req.oper_num,
            item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except TsdFiddlerError as exc:
        logger.error("FIDDLER start-setup failed: %s", exc)
        raise _handle_fiddler_error(exc)


@router.post("/end-setup", response_model=TsdFiddlerResponse)
async def end_setup(
    req: TsdFiddlerStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """End Setup — Infor InsWrapper(TT=2) + Kapacity + auto start_work + local TX."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await fiddler.end_setup(
            infor_client=infor_client,
            emp_num=emp_num,
            job=req.job,
            suffix=req.suffix,
            oper_num=req.oper_num,
            item=req.item,
            whse=req.whse,
            kapacity_guid=req.kapacity_guid,
        )
        # Record SETUP_END
        await _record_tsd_tx(
            db, user.username, WorkshopTransType.SETUP_END,
            req.job, req.suffix, req.oper_num,
            item=req.item,
        )
        # Record auto START (work started after setup)
        await _record_tsd_tx(
            db, user.username, WorkshopTransType.START,
            req.job, req.suffix, req.oper_num,
            wc=result.get("wc", ""),
            item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except TsdFiddlerError as exc:
        logger.error("FIDDLER end-setup failed: %s", exc)
        raise _handle_fiddler_error(exc)


@router.post("/start-work", response_model=TsdFiddlerResponse)
async def start_work(
    req: TsdFiddlerStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """Start Work — Infor ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx(H) + local TX."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await fiddler.start_work(
            infor_client=infor_client,
            emp_num=emp_num,
            job=req.job,
            suffix=req.suffix,
            oper_num=req.oper_num,
            item=req.item,
            whse=req.whse,
            kapacity_guid=req.kapacity_guid,
        )
        await _record_tsd_tx(
            db, user.username, WorkshopTransType.START,
            req.job, req.suffix, req.oper_num,
            wc=result.get("wc", ""),
            item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except TsdFiddlerError as exc:
        logger.error("FIDDLER start-work failed: %s", exc)
        raise _handle_fiddler_error(exc)


@router.post("/end-work", response_model=TsdFiddlerResponse)
async def end_work(
    req: TsdFiddlerEndWorkRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """End Work — Infor InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx(J) + local TX."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await fiddler.end_work(
            infor_client=infor_client,
            emp_num=emp_num,
            job=req.job,
            suffix=req.suffix,
            oper_num=req.oper_num,
            item=req.item,
            whse=req.whse,
            qty_complete=req.qty_complete,
            qty_scrapped=req.qty_scrapped,
            oper_complete=req.oper_complete,
            kapacity_guid=req.kapacity_guid,
        )
        await _record_tsd_tx(
            db, user.username, WorkshopTransType.STOP,
            req.job, req.suffix, req.oper_num,
            item=req.item,
            qty_completed=req.qty_complete,
            qty_scrapped=req.qty_scrapped,
        )
        return TsdFiddlerResponse(**result)
    except TsdFiddlerError as exc:
        logger.error("FIDDLER end-work failed: %s", exc)
        raise _handle_fiddler_error(exc)


# ---------------------------------------------------------------------------
# Diagnostic endpoint
# ---------------------------------------------------------------------------

@router.get("/diag/dcsfc")
async def diag_dcsfc(
    job: str = Query(default=""),
    suffix: str = Query(default="0"),
    oper_num: str = Query(default=""),
    emp_num: str = Query(default=""),
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
) -> Dict[str, Any]:
    """Diagnostic: read DcSfc + Mchtrx records from Infor for a given job."""
    filters = []
    if job:
        filters.append(f"Job = '{job}'")
    filters.append(f"Suffix = {suffix}")
    if oper_num:
        filters.append(f"OperNum = {oper_num}")
    if emp_num:
        filters.append(f"EmpNum = '{emp_num}'")
    flt = " AND ".join(filters) if filters else None

    try:
        dcsfc = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=[
                "TransNum", "TransType", "TransDate", "EmpNum", "Job",
                "Suffix", "OperNum",
                "StartTime", "EndTime", "DerStartTime", "DerEndTime",
                "QtyComplete", "QtyScrapped",
                "Termid", "Source", "Wc",
                "dcsfcuf_ite_cz_ins_dcsfc_src_module",
            ],
            filter=flt,
            order_by="TransNum DESC",
            record_cap=20,
        )
    except Exception as exc:
        dcsfc = {"error": str(exc)}

    mchtrx = None
    mchtrx_ido_tried = []
    for mchtrx_ido in ["SLMchtrxs", "SLMchtrx", "Mchtrxs", "Mchtrx"]:
        try:
            mchtrx = await infor_client.load_collection(
                ido_name=mchtrx_ido,
                properties=[
                    "TransNum", "TransDate", "EmpNum", "Job", "Suffix",
                    "OperNum", "WC", "StartTime", "EndTime",
                ],
                filter=flt,
                order_by="TransNum DESC",
                record_cap=20,
            )
            mchtrx_ido_tried.append(f"{mchtrx_ido}: OK")
            break
        except Exception as exc:
            mchtrx_ido_tried.append(f"{mchtrx_ido}: {exc}")
    if mchtrx is None:
        mchtrx = {"error": "No working IDO found", "tried": mchtrx_ido_tried}

    # Also try IDO info to discover available properties
    ido_info = None
    try:
        ido_info = await infor_client.get_ido_info("SLDcsfcs")
    except Exception as exc:
        ido_info = {"error": str(exc)}

    return {
        "job": job,
        "suffix": suffix,
        "oper_num": oper_num,
        "dcsfc": dcsfc,
        "mchtrx": mchtrx,
        "ido_info": ido_info,
    }
