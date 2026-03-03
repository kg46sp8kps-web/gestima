"""TSD Mongoose — Router.

Stateful session-based TSD reporting via Mongoose/IPS protocol.
SP flow via Mongoose, post-SP timestamp fix via REST (architectural pattern
shared by ALL Infor TSD implementations — SPs write stale timestamps).

Endpoints:
  POST /start-setup   → WrapperSp(TT=1) + local TX
  POST /end-setup     → WrapperSp(TT=2) + auto start_work + local TX
  POST /start-work    → Wrapper(TT=3) + Kapacity + Mchtrx(H) + local TX
  POST /end-work      → InsWrapper(TT=4) + close session + REST fix + local TX
  GET  /status        → Session status + connectivity check
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User
from app.models.workshop_transaction import WorkshopTransaction
from app.models.enums import WorkshopTransType, WorkshopTxStatus
from app.schemas.tsd_fiddler import (
    TsdFiddlerEndWorkRequest,
    TsdFiddlerResponse,
    TsdFiddlerStartRequest,
)
from app.services import tsd_mongoose_service as tsd
from app.services.tsd_mongoose_service import TsdMongooseError
from app.services.mongoose_session import MongooseSession, MongooseSessionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tsd", tags=["TSD Mongoose"])

# Default emp_num for testing (from HAR: employee 20)
_DEFAULT_EMP = "20"

# CET timezone for timestamp fixes
_CET = timezone(timedelta(hours=1))


def _get_infor_client():
    """Factory: create InforAPIClient for post-SP timestamp fix.

    Uses IPS_CONFIG (not INFOR_CONFIG) — the Mongoose session creates records
    in the IPS database (Live), so fixes must query the same DB.
    """
    from app.services.infor_api_client import InforAPIClient
    if not settings.INFOR_API_URL:
        return None
    return InforAPIClient(
        base_url=settings.INFOR_API_URL,
        config=settings.IPS_CONFIG,
        username=settings.INFOR_USERNAME,
        password=settings.INFOR_PASSWORD,
        verify_ssl=False,
    )


# ---------------------------------------------------------------------------
# Singleton session management
# ---------------------------------------------------------------------------

_session: MongooseSession | None = None


async def _get_session() -> MongooseSession:
    """Get or create the shared Mongoose session (lazy singleton)."""
    global _session

    if _session and _session.connected:
        return _session

    if not settings.IPS_HOST:
        raise HTTPException(
            status_code=501,
            detail="IPS not configured (set IPS_HOST, IPS_USER, IPS_PASSWORD in .env)",
        )

    logger.info("TSD_MONGOOSE: creating new IPS session to %s", settings.IPS_HOST)
    _session = MongooseSession(base_url=settings.IPS_HOST)
    try:
        await _session.connect(
            user=settings.IPS_USER,
            password=settings.IPS_PASSWORD,
            config=settings.IPS_CONFIG,
            pwd_is_hash=True,
        )
    except Exception as exc:
        _session = None
        logger.error("TSD_MONGOOSE: failed to connect to IPS: %s", exc)
        raise HTTPException(status_code=502, detail=f"IPS connection failed: {exc}")

    return _session


async def _get_session_with_reconnect() -> MongooseSession:
    """Get session, retry once on error (handles stale sessions)."""
    global _session
    try:
        return await _get_session()
    except HTTPException:
        if _session:
            try:
                await _session.close()
            except Exception:
                pass
            _session = None
        return await _get_session()


async def _force_close_session() -> None:
    """Force close the Mongoose session to commit IPS transaction.

    After InsWrapperSp + machine SPs, the IPS session holds a transaction lock.
    REST API cannot see the records until the session releases the lock.
    Closing the session forces a commit. Session will be re-created on next request.
    """
    global _session
    if _session:
        try:
            await _session.close()
        except Exception as exc:
            logger.warning("TSD_MONGOOSE: session close error (ignored): %s", exc)
        _session = None
    logger.info("TSD_MONGOOSE: session closed (IPS transaction committed)")


# ---------------------------------------------------------------------------
# REST timestamp fix (post-SP)
# ---------------------------------------------------------------------------

async def _fix_dcsfc_timestamps(
    job: str,
    suffix: str,
    oper_num: str,
    trans_type: int,
    start_secs: int,
    end_secs: Optional[int] = None,
    run_hrs: Optional[float] = None,
    trans_num: str = "",
) -> None:
    """Fix timestamps on DcSfc MJOB record via REST API.

    WrapperSp/InsWrapperSp ALWAYS write stale timestamps regardless of protocol.
    ALL Infor TSD implementations fix timestamps via REST after SP calls.

    For start (TT=3): fixes StartTime + TransDate. WrapperSp commits immediately,
    so REST can see the record even with an active Mongoose session.

    For end (TT=4): fixes StartTime + EndTime + RunHrsT + TransDate.
    Must be called AFTER Mongoose session is closed (IPS transaction committed).
    """
    infor_client = _get_infor_client()
    if not infor_client:
        logger.warning("TSD_MONGOOSE fix: no REST API configured, skipping")
        return

    # TransDate format matching Infor (fiddler format)
    now_cet = datetime.now(_CET)
    trans_date = now_cet.strftime("%Y%m%d %H:%M:%S.000")

    try:
        # Find the record — by TransNum or by job/oper/TT
        row = None
        if trans_num:
            resp = await infor_client.load_collection(
                ido_name="SLDcsfcs",
                properties=["TransNum", "TransType", "StartTime", "EndTime",
                             "RunHrsT", "TransDate", "_ItemId"],
                filter=f"TransNum = {trans_num} AND Termid = 'MJOB'",
                record_cap=1,
            )
            rows = resp.get("data", [])
            if rows:
                row = rows[0]

        if not row:
            resp = await infor_client.load_collection(
                ido_name="SLDcsfcs",
                properties=["TransNum", "TransType", "StartTime", "EndTime",
                             "RunHrsT", "TransDate", "_ItemId"],
                filter=(
                    f"Job = '{job}' AND Suffix = {suffix} AND OperNum = {oper_num}"
                    f" AND Termid = 'MJOB' AND TransType = {trans_type}"
                ),
                order_by="TransNum DESC",
                record_cap=1,
            )
            rows = resp.get("data", [])
            if rows:
                row = rows[0]

        if not row:
            logger.warning(
                "TSD_MONGOOSE fix: TT=%d MJOB not found TN=%s %s/%s/%s",
                trans_type, trans_num, job, suffix, oper_num,
            )
            return

        item_id = row.get("_ItemId", "")
        if not item_id:
            logger.warning("TSD_MONGOOSE fix: no _ItemId for TN=%s", row.get("TransNum"))
            return

        # Build properties to fix
        props = [
            {"Name": "StartTime", "Value": str(start_secs), "Modified": True},
            {"Name": "TransDate", "Value": trans_date, "Modified": True},
        ]
        if end_secs is not None:
            props.append({"Name": "EndTime", "Value": str(end_secs), "Modified": True})
        if run_hrs is not None:
            hrs_field = "SetupHrsT" if trans_type in (1, 2) else "RunHrsT"
            props.append({"Name": hrs_field, "Value": f"{run_hrs:.4f}", "Modified": True})

        logger.info(
            "TSD_MONGOOSE fix TT=%d TN=%s: Start=%s→%d End=%s→%s Hrs→%s TransDate→%s",
            trans_type, row.get("TransNum"),
            row.get("StartTime"), start_secs,
            row.get("EndTime"), end_secs if end_secs is not None else "(skip)",
            f"{run_hrs:.4f}" if run_hrs is not None else "(skip)",
            trans_date,
        )

        body = {
            "IDOName": "SLDcsfcs",
            "Changes": [{
                "Action": 2,
                "ItemId": item_id,
                "Properties": props,
            }],
        }
        await infor_client.execute_update_request(body)
        logger.info("TSD_MONGOOSE fix TT=%d: timestamps updated OK", trans_type)

    except Exception as exc:
        logger.warning("TSD_MONGOOSE fix TT=%d failed (non-fatal): %s", trans_type, exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_emp_num(user: Optional[User]) -> str:
    """Resolve Infor employee number. Falls back to default for testing."""
    if user:
        for attr in ("infor_emp_num", "username"):
            val = getattr(user, attr, None)
            if val and str(val).strip().isdigit():
                return str(val).strip()
    return _DEFAULT_EMP


def _now_cet_seconds() -> int:
    """Current time as seconds-from-midnight in CET."""
    now = datetime.now(_CET)
    return now.hour * 3600 + now.minute * 60 + now.second


async def _record_tx(
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


def _handle_error(exc: Exception) -> HTTPException:
    """Convert TSD errors to HTTPException."""
    if isinstance(exc, TsdMongooseError):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, MongooseSessionError):
        return HTTPException(status_code=502, detail=f"IPS session error: {exc}")
    return HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Endpoints (auth optional — falls back to default emp for testing)
# ---------------------------------------------------------------------------

@router.post("/start-setup", response_model=TsdFiddlerResponse)
async def start_setup(
    req: TsdFiddlerStartRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Start Setup — WrapperSp(TT=1) via Mongoose session."""
    emp_num = _resolve_emp_num(user)
    username = user.username if user else "tsd"
    try:
        session = await _get_session_with_reconnect()
        result = await tsd.start_setup(
            session, emp_num, req.job, req.suffix, req.oper_num, req.whse,
        )
        await _record_tx(
            db, username, WorkshopTransType.SETUP_START,
            req.job, req.suffix, req.oper_num, item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except (TsdMongooseError, MongooseSessionError) as exc:
        logger.error("TSD start-setup failed: %s", exc)
        raise _handle_error(exc)


@router.post("/end-setup", response_model=TsdFiddlerResponse)
async def end_setup(
    req: TsdFiddlerStartRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """End Setup — WrapperSp(TT=2) + auto start_work via Mongoose session."""
    emp_num = _resolve_emp_num(user)
    username = user.username if user else "tsd"
    try:
        session = await _get_session_with_reconnect()
        result = await tsd.end_setup(
            session, emp_num, req.job, req.suffix, req.oper_num,
            req.item, req.whse, req.kapacity_guid,
        )
        await _record_tx(
            db, username, WorkshopTransType.SETUP_END,
            req.job, req.suffix, req.oper_num, item=req.item,
        )
        await _record_tx(
            db, username, WorkshopTransType.START,
            req.job, req.suffix, req.oper_num,
            wc=result.get("wc", ""), item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except (TsdMongooseError, MongooseSessionError) as exc:
        logger.error("TSD end-setup failed: %s", exc)
        raise _handle_error(exc)


@router.post("/start-work", response_model=TsdFiddlerResponse)
async def start_work(
    req: TsdFiddlerStartRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Start Work — Mongoose SPs + REST fix for StartTime + TransDate.

    WrapperSp(TT=3) commits immediately, so REST can see the record
    even with an active Mongoose session (no need to close/reconnect).
    """
    emp_num = _resolve_emp_num(user)
    username = user.username if user else "tsd"
    start_secs = _now_cet_seconds()
    try:
        session = await _get_session_with_reconnect()
        result = await tsd.start_work(
            session, emp_num, req.job, req.suffix, req.oper_num,
            req.item, req.whse, req.kapacity_guid,
        )

        # REST fix: StartTime + TransDate on TT=3 record
        # WrapperSp commits immediately → REST can see it without closing session
        await _fix_dcsfc_timestamps(
            req.job, req.suffix, req.oper_num,
            trans_type=3, start_secs=start_secs,
        )

        await _record_tx(
            db, username, WorkshopTransType.START,
            req.job, req.suffix, req.oper_num,
            wc=result.get("wc", ""), item=req.item,
        )
        return TsdFiddlerResponse(**result)
    except (TsdMongooseError, MongooseSessionError) as exc:
        logger.error("TSD start-work failed: %s", exc)
        raise _handle_error(exc)


@router.post("/end-work", response_model=TsdFiddlerResponse)
async def end_work(
    req: TsdFiddlerEndWorkRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """End Work — Mongoose SPs → close session (commit) → REST timestamp fix.

    InsWrapperSp always writes stale timestamps. ALL Infor TSD implementations
    (InduStream, Fiddler, workshop ASD) fix timestamps via REST after SP calls.
    Closing the Mongoose session commits the IPS transaction, making records
    visible to REST API for the fix.
    """
    emp_num = _resolve_emp_num(user)
    username = user.username if user else "tsd"

    # Capture start time BEFORE the Mongoose flow
    start_secs = _now_cet_seconds()

    try:
        # Phase 1: Full Mongoose SP flow
        session = await _get_session_with_reconnect()
        result = await tsd.end_work(
            session, emp_num, req.job, req.suffix, req.oper_num,
            req.item, req.whse,
            req.qty_complete, req.qty_scrapped, req.oper_complete,
            req.kapacity_guid,
        )

        # Phase 2: Close Mongoose session → commits IPS transaction
        await _force_close_session()

        # Phase 3: REST timestamp fix (StartTime + EndTime + TransDate + RunHrsT)
        end_secs = _now_cet_seconds()
        elapsed = end_secs - start_secs
        if elapsed < 0:
            elapsed += 86400
        run_hrs = elapsed / 3600.0
        trans_num = result.get("trans_num", "")
        await _fix_dcsfc_timestamps(
            req.job, req.suffix, req.oper_num,
            trans_type=4, start_secs=start_secs, end_secs=end_secs,
            run_hrs=run_hrs, trans_num=trans_num,
        )

        # Phase 4: Local transaction record
        await _record_tx(
            db, username, WorkshopTransType.STOP,
            req.job, req.suffix, req.oper_num,
            item=req.item,
            qty_completed=req.qty_complete,
            qty_scrapped=req.qty_scrapped,
        )
        return TsdFiddlerResponse(**result)
    except (TsdMongooseError, MongooseSessionError) as exc:
        logger.error("TSD end-work failed: %s", exc)
        raise _handle_error(exc)


# ---------------------------------------------------------------------------
# Status / diagnostics
# ---------------------------------------------------------------------------

@router.get("/status")
async def session_status(user: User = Depends(get_current_user)):
    """Check IPS session status."""
    global _session
    return {
        "ips_host": settings.IPS_HOST or "(not configured)",
        "ips_user": settings.IPS_USER,
        "ips_config": settings.IPS_CONFIG,
        "session_connected": _session.connected if _session else False,
        "session_token": _session.token[:20] + "..." if _session and _session.token else None,
    }


@router.post("/reconnect")
async def reconnect_session(user: User = Depends(get_current_user)):
    """Force reconnect the IPS session."""
    global _session
    if _session:
        await _session.close()
        _session = None
    session = await _get_session()
    return {"status": "reconnected", "token": session.token[:20] + "..."}


@router.post("/cleanup-hanging")
async def cleanup_hanging_transactions(
    emp_num: str = Query(default="20", description="Employee number to clean up"),
    user: User = Depends(get_current_user),
):
    """Find and delete hanging MJOB DcSfc records (open TT=3 without matching TT=4).

    This cleans up garbage from failed test runs that would confuse InsWrapperSp.
    Also force-reconnects the IPS session to clear stale session state.
    """
    infor_client = _get_infor_client()
    if not infor_client:
        raise HTTPException(status_code=501, detail="Infor REST API not configured")

    results = {"deleted": [], "errors": [], "session_reconnected": False}

    # 1. Find all open TT=3 MJOB records for this employee
    try:
        resp = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=["TransNum", "TransType", "Job", "Suffix", "OperNum",
                         "StartTime", "EndTime", "EmpNum", "_ItemId"],
            filter=f"EmpNum LIKE '%{emp_num.strip()}' AND Termid = 'MJOB' AND TransType = 3",
            order_by="TransNum DESC",
            record_cap=50,
        )
        rows = resp.get("data", [])
        logger.info("CLEANUP: found %d open TT=3 MJOB records for emp %s", len(rows), emp_num)

        for row in rows:
            tn = row.get("TransNum", "")
            item_id = row.get("_ItemId", "")
            job = row.get("Job", "")
            oper = row.get("OperNum", "")
            if not item_id:
                continue
            try:
                body = {
                    "IDOName": "SLDcsfcs",
                    "Changes": [{"Action": 4, "ItemId": item_id}],  # 4 = Delete
                }
                await infor_client.execute_update_request(body)
                results["deleted"].append(f"TN={tn} Job={job} Oper={oper}")
                logger.info("CLEANUP: deleted TN=%s Job=%s Oper=%s", tn, job, oper)
            except Exception as exc:
                results["errors"].append(f"TN={tn}: {exc}")
                logger.warning("CLEANUP: failed to delete TN=%s: %s", tn, exc)

    except Exception as exc:
        results["errors"].append(f"Query failed: {exc}")
        logger.error("CLEANUP: query failed: %s", exc)

    # 2. Force reconnect IPS session to clear stale state
    global _session
    if _session:
        try:
            await _session.close()
        except Exception:
            pass
        _session = None
    try:
        await _get_session()
        results["session_reconnected"] = True
    except Exception as exc:
        results["errors"].append(f"Reconnect failed: {exc}")

    return results
