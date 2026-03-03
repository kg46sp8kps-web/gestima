"""Industream TSD — Router.

Clean START/END pairing with machine transactions (2.har verified).

Endpoints:
  POST /start-setup   — Infor WrapperSp(TT=1) + local SETUP_START tx
  POST /end-setup     — Infor WrapperSp(TT=2) + auto start_work
  POST /start-work    — Infor ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx
  POST /end-work      — Infor InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx
  GET  /diag/dcsfc    — diagnostic read of DcSfc + Mchtrx records
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.industream_tsd import (
    TsdEndWorkRequest,
    TsdResponse,
    TsdStartRequest,
)
from app.services import industream_tsd_service as tsd
from app.services.industream_tsd_service import TsdError
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/industream-tsd", tags=["industream-tsd"])


def _get_infor_client() -> InforAPIClient:
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


# ---------------------------------------------------------------------------
# Endpoints — each calls service function (which handles Infor + local tx)
# ---------------------------------------------------------------------------

@router.post("/start-setup", response_model=TsdResponse)
async def start_setup(
    req: TsdStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """Start Setup — WrapperSp(TT=1) + local SETUP_START tx."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await tsd.start_setup(
            infor_client, db, user.username, emp_num,
            req.job, req.suffix, req.oper_num,
            item=req.item, whse=req.whse,
        )
        return TsdResponse(**result)
    except TsdError as exc:
        logger.error("start-setup failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/end-setup", response_model=TsdResponse)
async def end_setup(
    req: TsdStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """End Setup — WrapperSp(TT=2) + auto start_work."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await tsd.end_setup(
            infor_client, db, user.username, emp_num,
            req.job, req.suffix, req.oper_num,
            item=req.item, whse=req.whse,
        )
        return TsdResponse(**result)
    except TsdError as exc:
        logger.error("end-setup failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/start-work", response_model=TsdResponse)
async def start_work(
    req: TsdStartRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """Start Work — ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await tsd.start_work(
            infor_client, db, user.username, emp_num,
            req.job, req.suffix, req.oper_num,
            item=req.item, whse=req.whse,
        )
        return TsdResponse(**result)
    except TsdError as exc:
        logger.error("start-work failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/end-work", response_model=TsdResponse)
async def end_work(
    req: TsdEndWorkRequest,
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
    db: AsyncSession = Depends(get_db),
):
    """End Work — InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx."""
    emp_num = _resolve_emp_num(user)
    try:
        result = await tsd.end_work(
            infor_client, db, user.username, emp_num,
            req.job, req.suffix, req.oper_num,
            item=req.item, whse=req.whse,
            qty_complete=req.qty_complete,
            qty_scrapped=req.qty_scrapped,
            oper_complete=req.oper_complete,
            job_complete=req.job_complete,
        )
        return TsdResponse(**result)
    except TsdError as exc:
        logger.error("end-work failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


# ---------------------------------------------------------------------------
# Diagnostic endpoints (kept for debugging)
# ---------------------------------------------------------------------------

@router.get("/diag/dcsfc")
async def diag_dcsfc(
    job: str = Query(...),
    suffix: str = Query(default="0"),
    oper_num: str = Query(default=""),
    user: User = Depends(get_current_user),
    infor_client: InforAPIClient = Depends(_get_infor_client),
) -> Dict[str, Any]:
    """Diagnostic: read DcSfc + Mchtrx records from Infor for a given job."""
    flt = f"Job = '{job}' AND Suffix = {suffix}"
    if oper_num:
        flt += f" AND OperNum = {oper_num}"

    try:
        dcsfc = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=[
                "TransNum", "TransType", "TransDate", "EmpNum", "Job",
                "Suffix", "OperNum", "PostDate",
                "StartTime", "EndTime", "RunHrsT", "SetupHrsT",
                "QtyComplete", "QtyScrapped", "WC",
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
                    "RunHrsT",
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

    return {
        "job": job,
        "suffix": suffix,
        "oper_num": oper_num,
        "dcsfc": dcsfc,
        "mchtrx": mchtrx,
    }
