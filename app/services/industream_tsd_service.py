"""Industream TSD — SP + Gestima time tracking.

SPs create DcSfc/Mchtrx records (direct IDO INSERT doesn't work on SLDcsfcs).
Gestima tracks start times locally. After SP creates record with stale
timestamps, we UPDATE both StartTime+EndTime together to prevent overwrite bug.

Flow:
  start_setup: init → WrapperSp(TT=1) → fix StartTime → local tx
  end_setup:   init → WrapperSp(TT=2) → fix timestamps → local tx → auto start_work
  start_work:  init → ValidateMachine → WrapperSp(TT=3) → fix StartTime → MchtrxSp → local tx
  end_work:    init → InsWrapperSp(TT=4) → fix timestamps → MachineVal → DcSfcMchtrx → local tx
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import set_audit, safe_commit
from app.models.workshop_transaction import WorkshopTransaction
from app.models.enums import WorkshopTransType, WorkshopTxStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_IDO = "IteCzTsdStd"
_IDO_DCSFC = "SLDcsfcs"

# Init SPs
_SP_VALIDATE_EMP = "IteCzTsdValidateEmpNumDcSfcSp"
_SP_INIT_PARMS = "IteCzTsdInitParmsSp"
_SP_VALIDATE_JOB = "IteCzTsdValidateJobSp"
_SP_VALIDATE_MULTI_JOB = "IteCzTsdValidateMultiJobDcSfcSp"

# Action SPs
_SP_VALIDATE_MACHINE = "IteCzTsdValidateOperNumMachineSp"
_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"
_SP_INS_WRAPPER = "IteCzInsWrapperDcsfcUpdateSp"
_SP_MCHTRX = "IteCzTsdUpdateMchtrxSp"
_SP_MACHINE_VAL = "IteCzTsdMachineValOperNumSp"
_SP_DC_SFC_MCHTRX = "IteCzTsdUpdateDcSfcMchtrxSp"


class TsdError(Exception):
    def __init__(self, message: str, step: str = ""):
        self.step = step
        super().__init__(f"[{step}] {message}" if step else message)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
_CET = timezone(timedelta(hours=1))


def _now_cet() -> datetime:
    return datetime.now(_CET)


def _secs(dt: datetime) -> int:
    """Seconds from midnight."""
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def _now_cet_seconds() -> int:
    return _secs(_now_cet())


def _fmt_emp(num: str) -> str:
    return num.strip().rjust(7)


def _fmt_qty(value: float) -> str:
    return f"{value:.2f}"


def _flag(value: bool) -> str:
    return "1" if value else "0"


# ---------------------------------------------------------------------------
# SP invoke (GET positional — POST returns 405)
# ---------------------------------------------------------------------------

async def _invoke(
    infor_client: Any,
    sp_name: str,
    params: List[str],
    step: str = "",
    infobar_index: int = -1,
) -> Dict[str, Any]:
    """Call Infor SP via GET positional, validate response."""
    logger.info("TSD SP [%s]: %s (%d params)", step, sp_name, len(params))
    logger.debug("TSD SP %s params: %s", sp_name, params)

    resp = await infor_client.invoke_method_positional(
        ido_name=_IDO,
        method_name=sp_name,
        positional_values=params,
    )

    msg_code = resp.get("MessageCode", -1)
    logger.info("TSD SP %s: code=%s params=%s", sp_name, msg_code, resp.get("Parameters", []))

    if msg_code not in (0, 200, 210):
        msg = str(resp.get("Message", "") or resp.get("ReturnValue", "") or "")
        logger.error("TSD SP %s FAILED [%s]: code=%s %s", sp_name, step, msg_code, msg)
        raise TsdError(f"{sp_name}: {msg} (code={msg_code})", step)

    # Check infobar for errors
    pa = resp.get("Parameters") or []
    if infobar_index >= 0 and isinstance(pa, list) and infobar_index < len(pa):
        infobar = str(pa[infobar_index] or "").strip()
        if infobar and "was successful" not in infobar.lower():
            logger.error("TSD SP %s InfoBar [%s]: %s", sp_name, step, infobar)
            raise TsdError(f"{sp_name}: {infobar}", step)

    return resp


# ---------------------------------------------------------------------------
# Init DcSfc context (required before WrapperSp/InsWrapperSp)
# ---------------------------------------------------------------------------

async def _init_context(
    infor_client: Any,
    emp: str,
    job: str, suffix: str,
    whse: str,
    step: str,
) -> None:
    """Init DcSfc context: ValidateEmp → InitParms×2 → ValidateJob → ValidateMultiJob."""
    # ValidateEmpNumDcSfc (7p)
    await _invoke(infor_client, _SP_VALIDATE_EMP,
                  [emp, "", "", "", "", "", ""],
                  step=f"{step}.init_emp")

    # InitParms ×2
    await _invoke(infor_client, _SP_INIT_PARMS,
                  ["00000", "KontrolaPrijAPresunKusuNaOper", "", "1", "Nothing"],
                  step=f"{step}.init_p1")
    await _invoke(infor_client, _SP_INIT_PARMS,
                  ["00000", "VydejDoNadrizeneho", "0", "0", ""],
                  step=f"{step}.init_p2")

    # ValidateJob (8p)
    await _invoke(infor_client, _SP_VALIDATE_JOB,
                  [f"{job}-{suffix}", "", "", "", whse, "", "", ""],
                  step=f"{step}.validate_job")

    # ValidateMultiJob (3p)
    await _invoke(infor_client, _SP_VALIDATE_MULTI_JOB,
                  [emp, "", ""],
                  step=f"{step}.validate_multi_job")

    logger.info("TSD context initialized [%s]", step)


# ---------------------------------------------------------------------------
# Extract TransNum from SP response
# ---------------------------------------------------------------------------

def _extract_trans_num(resp: Dict[str, Any], index: int = 28) -> Optional[str]:
    """Extract TransNum from WrapperSp/InsWrapperSp response parameters."""
    pa = resp.get("Parameters") or []
    if isinstance(pa, list) and index < len(pa):
        val = str(pa[index] or "").strip()
        if val and val.isdigit():
            return val
    return None


# ---------------------------------------------------------------------------
# DcSfc timestamp fix via UPDATE (both fields to prevent overwrite)
# ---------------------------------------------------------------------------

async def _load_dcsfc_record(
    infor_client: Any,
    trans_num: Optional[str],
    job: str, suffix: str, oper_num: str,
    trans_type: int,
    step: str,
) -> Optional[Dict[str, Any]]:
    """Load DcSfc record — try by TransNum first, fallback to Job+Suffix broad query."""
    # Strategy 1: Direct TransNum lookup (fastest, most reliable)
    if trans_num:
        resp = await infor_client.load_collection(
            ido_name=_IDO_DCSFC,
            properties=["TransNum", "TransType", "OperNum",
                         "StartTime", "EndTime", "RunHrsT", "SetupHrsT", "_ItemId"],
            filter=f"TransNum = {trans_num}",
            record_cap=1,
        )
        rows = resp.get("data", [])
        if rows:
            logger.info("TSD fix [%s]: found TN=%s via direct lookup", step, trans_num)
            return rows[0]
        logger.warning("TSD fix [%s]: TransNum=%s not found, trying broad query", step, trans_num)

    # Strategy 2: Broad Job+Suffix query + Python filter
    resp = await infor_client.load_collection(
        ido_name=_IDO_DCSFC,
        properties=["TransNum", "TransType", "OperNum",
                     "StartTime", "EndTime", "RunHrsT", "SetupHrsT", "_ItemId"],
        filter=f"Job = '{job}' AND Suffix = {suffix}",
        order_by="TransNum DESC",
        record_cap=20,
    )
    all_rows = resp.get("data", [])
    tt_str = str(trans_type)
    rows = [r for r in all_rows
            if str(r.get("OperNum", "")).strip() == str(oper_num).strip()
            and str(r.get("TransType", "")).strip() == tt_str]
    logger.info("TSD fix [%s]: broad=%d matched=%d (TT=%s oper=%s)",
                 step, len(all_rows), len(rows), tt_str, oper_num)
    if rows:
        return rows[0]
    if all_rows:
        logger.warning("TSD fix [%s]: broad has %d but none match TT=%s oper=%s (sample: %s)",
                       step, len(all_rows), tt_str, oper_num,
                       [(r.get("TransNum"), r.get("TransType"), r.get("OperNum")) for r in all_rows[:5]])
    return None


async def _fix_dcsfc_timestamps(
    infor_client: Any,
    job: str, suffix: str, oper_num: str,
    trans_type: int,
    start_seconds: int,
    end_seconds: Optional[int] = None,
    hours: Optional[float] = None,
    step: str = "",
    trans_num: Optional[str] = None,
) -> None:
    """Fix StartTime, EndTime and RunHrsT/SetupHrsT on DcSfc record.

    Uses TransNum from SP response for targeted lookup.
    Falls back to broad Job+Suffix query if TransNum lookup fails.
    Retries once after 2s delay if record not found (Infor commit delay).
    """
    try:
        # Wait for Infor to commit the SP transaction
        await asyncio.sleep(1.0)

        row = await _load_dcsfc_record(
            infor_client, trans_num, job, suffix, oper_num, trans_type, step)

        # Retry once after delay if not found
        if not row:
            logger.info("TSD fix [%s]: retry after 2s delay...", step)
            await asyncio.sleep(2.0)
            row = await _load_dcsfc_record(
                infor_client, trans_num, job, suffix, oper_num, trans_type, step)

        if not row:
            logger.warning("TSD fix: record not found after retry [%s] TN=%s TT=%s %s/%s/%s",
                           step, trans_num, trans_type, job, suffix, oper_num)
            return

        item_id = row.get("_ItemId", "")
        if not item_id:
            logger.warning("TSD fix: no _ItemId for TN=%s [%s]", row.get("TransNum"), step)
            return

        # Build properties — always set both time fields together
        props = [{"Name": "StartTime", "Value": str(start_seconds), "Modified": True}]
        if end_seconds is not None:
            props.append({"Name": "EndTime", "Value": str(end_seconds), "Modified": True})

        # Set hours field (SP calculates from stale times → wrong value)
        if hours is not None:
            if trans_type in (1, 2):
                props.append({"Name": "SetupHrsT", "Value": f"{hours:.4f}", "Modified": True})
            elif trans_type in (3, 4):
                props.append({"Name": "RunHrsT", "Value": f"{hours:.4f}", "Modified": True})

        logger.info(
            "TSD fix TT=%d TN=%s: Start %s→%d, End %s→%s, Hrs→%s [%s]",
            trans_type, row.get("TransNum"),
            row.get("StartTime"), start_seconds,
            row.get("EndTime"), end_seconds if end_seconds is not None else "(skip)",
            f"{hours:.4f}" if hours is not None else "(skip)",
            step,
        )

        body = {
            "IDOName": _IDO_DCSFC,
            "Changes": [{"Action": 2, "ItemId": item_id, "Properties": props}],
        }
        fix_resp = await infor_client.execute_update_request(body)
        msg_code = fix_resp.get("MessageCode", -1)
        logger.info("TSD fix result [%s]: code=%s msg=%s", step, msg_code, fix_resp.get("Message", ""))

    except Exception as exc:
        logger.warning("TSD fix failed [%s]: %s", step, exc)


# ---------------------------------------------------------------------------
# Machine resolution (read-only SP)
# ---------------------------------------------------------------------------

async def _resolve_machine(
    infor_client: Any,
    job: str, suffix: str, oper_num: str,
    emp: str, tt: str, item: str, whse: str,
) -> Dict[str, str]:
    """Resolve stroj + wc via ValidateOperNumMachineSp."""
    params = [job, suffix, oper_num, emp, tt, item, whse, "", "", "", ""]
    try:
        resp = await infor_client.invoke_method_positional(
            ido_name=_IDO,
            method_name=_SP_VALIDATE_MACHINE,
            positional_values=params,
        )
        if resp.get("MessageCode", -1) not in (0, 200, 210):
            return {"stroj": "", "wc": ""}
        pa = resp.get("Parameters") or []
        stroj = str(pa[8] or "").strip() if len(pa) > 8 else ""
        wc = str(pa[9] or "").strip() if len(pa) > 9 else ""
        logger.info("TSD machine: stroj=%s wc=%s", stroj, wc)
        return {"stroj": stroj, "wc": wc}
    except Exception as exc:
        logger.warning("TSD machine resolve failed: %s", exc)
        return {"stroj": "", "wc": ""}


# ---------------------------------------------------------------------------
# Local DB
# ---------------------------------------------------------------------------

async def _find_start_tx(
    db: AsyncSession,
    username: str,
    job: str, suffix: str, oper_num: str,
    trans_type: WorkshopTransType,
) -> Optional[WorkshopTransaction]:
    """Find the most recent local start tx for time calculation."""
    result = await db.execute(
        select(WorkshopTransaction)
        .where(
            WorkshopTransaction.created_by == username,
            WorkshopTransaction.infor_job == job,
            WorkshopTransaction.infor_suffix == suffix,
            WorkshopTransaction.oper_num == oper_num,
            WorkshopTransaction.trans_type == trans_type,
            WorkshopTransaction.started_at.isnot(None),
        )
        .order_by(desc(WorkshopTransaction.id))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _record_tx(
    db: AsyncSession,
    username: str,
    trans_type: WorkshopTransType,
    job: str, suffix: str, oper_num: str,
    wc: str = "", item: str = "",
    qty_completed: float = 0.0, qty_scrapped: float = 0.0,
    actual_hours: Optional[float] = None,
    start_seconds_cet: Optional[int] = None,
) -> None:
    now = datetime.utcnow()
    tx = WorkshopTransaction(
        infor_job=job, infor_suffix=suffix, infor_item=item,
        oper_num=oper_num, wc=wc,
        trans_type=trans_type,
        status=WorkshopTxStatus.POSTED,
        posted_at=now,
        started_at=now if trans_type in (WorkshopTransType.START, WorkshopTransType.SETUP_START) else None,
        finished_at=now if trans_type in (WorkshopTransType.STOP, WorkshopTransType.SETUP_END) else None,
        qty_completed=qty_completed, qty_scrapped=qty_scrapped,
        actual_hours=actual_hours,
    )
    set_audit(tx, username)
    db.add(tx)
    await safe_commit(db)
    logger.info("TSD local tx: %s %s/%s oper=%s by %s", trans_type.value, job, suffix, oper_num, username)


# ---------------------------------------------------------------------------
# WrapperSp parameter builders
# ---------------------------------------------------------------------------

def _build_wrapper_32p(
    emp: str, tt: str, job: str, suffix: str, oper_num: str,
) -> List[str]:
    """IteCzTsdUpdateDcSfcWrapperSp — 32 params (start: TT=1,2,3)."""
    return [
        "",         # [0]
        emp,        # [1]  gvEmpNum
        "1",        # [2]  vMultiJobFlag
        tt,         # [3]  vTransType
        job,        # [4]  vJob
        suffix,     # [5]  vSuffix
        oper_num,   # [6]  vOperNum
        "",         # [7]  vQtyComplete
        "",         # [8]  vQtyScrapped
        "",         # [9]  vQtyMoved
        "0",        # [10] vOperComplete
        "0",        # [11] vJobComplete
        "0",        # [12] vIssueParent
        "",         # [13] vLoc
        "",         # [14] vLot
        "",         # [15] vReasonCode
        "",         # [16] vSerNumList
        "",         # [17] vWc (SP resolves from jobroute)
        "",         # [18]
        "T",        # [19] vSourceModul
        "",         # [20] gvIdMachine
        "",         # [21] gvResid
        "0",        # [22]
        "",         # [23] vMode
        "",         # [24] RV(vInfoBar) — OUT
        "",         # [25]
        "",         # [26]
        "",         # [27]
        "",         # [28]
        "",         # [29]
        "",         # [30] vDatumTransakce
        "",         # [31]
    ]


def _build_ins_wrapper_29p(
    emp: str, tt: str, job: str, suffix: str, oper_num: str,
    qty_complete: float, qty_scrapped: float, oper_complete: bool,
) -> List[str]:
    """IteCzInsWrapperDcsfcUpdateSp — 29 params (end: TT=2,4).

    [28] = @DcsfcTransNum OUT — returns the updated record's TransNum.
    """
    return [
        "1",                        # [0]  @Connected
        "",                         # [1]  @TTermId
        emp,                        # [2]  @TEmpNum
        "1",                        # [3]  @TMultiJob
        tt,                         # [4]  @TTransType
        job,                        # [5]  @TJobNum
        suffix,                     # [6]  @TJobSuffix
        oper_num,                   # [7]  @TOperNum
        _fmt_qty(qty_complete),     # [8]  @TcQtuQtyComp
        _fmt_qty(qty_scrapped),     # [9]  @TcQtuQtyScrap
        _fmt_qty(qty_complete),     # [10] @TcQtuQtyMove
        _flag(oper_complete),       # [11] @TComplete
        "",                         # [12] @TClose
        "0",                        # [13] @TIssueParent
        "",                         # [14] @TLocation
        "",                         # [15] @TLot
        "",                         # [16] @TReasonCode
        "0",                        # [17] @TCoProductMix
        "",                         # [18] @SerNumList
        "",                         # [19] @TWc
        "",                         # [20] @Note
        "T",                        # [21] @SourceModul
        "",                         # [22] @IdMachine
        "",                         # [23] @ResId
        "0",                        # [24] @AutoPost
        "",                         # [25] @Mode
        "",                         # [26] @Infobar — OUT
        "",                         # [27] @TransDate
        "",                         # [28] @DcsfcTransNum — OUT
    ]


# ---------------------------------------------------------------------------
# Public API — 4 operations
# ---------------------------------------------------------------------------

async def start_setup(
    infor_client: Any,
    db: AsyncSession,
    username: str,
    emp_num: str,
    job: str, suffix: str, oper_num: str,
    item: str = "", whse: str = "MAIN",
) -> Dict[str, Any]:
    """Start Setup — WrapperSp(TT=1) + fix StartTime + local tx."""
    emp = _fmt_emp(emp_num)
    start_secs = _now_cet_seconds()
    logger.info("TSD start_setup: job=%s/%s oper=%s", job, suffix, oper_num)

    # Init context + WrapperSp(TT=1)
    await _init_context(infor_client, emp, job, suffix, whse, "start_setup")
    wrapper_resp = await _invoke(infor_client, _SP_WRAPPER,
                                 _build_wrapper_32p(emp, "1", job, suffix, oper_num),
                                 step="start_setup.wrapper", infobar_index=24)
    trans_num = _extract_trans_num(wrapper_resp, index=28)
    logger.info("TSD start_setup: TransNum=%s from WrapperSp", trans_num)

    # Fix StartTime on new TT=1 record
    await _fix_dcsfc_timestamps(infor_client, job, suffix, oper_num,
                                trans_type=1, start_seconds=start_secs,
                                step="start_setup.fix", trans_num=trans_num)

    # Local tx
    await _record_tx(db, username, WorkshopTransType.SETUP_START, job, suffix, oper_num, item=item)

    return {"status": "ok", "message": "Setup started"}


async def end_setup(
    infor_client: Any,
    db: AsyncSession,
    username: str,
    emp_num: str,
    job: str, suffix: str, oper_num: str,
    item: str = "", whse: str = "MAIN",
) -> Dict[str, Any]:
    """End Setup — WrapperSp(TT=2) + fix timestamps + auto start_work."""
    emp = _fmt_emp(emp_num)
    end_secs = _now_cet_seconds()
    logger.info("TSD end_setup: job=%s/%s oper=%s", job, suffix, oper_num)

    # Get start time from local tx
    start_tx = await _find_start_tx(db, username, job, suffix, oper_num, WorkshopTransType.SETUP_START)
    if start_tx and start_tx.started_at:
        start_cet = start_tx.started_at.replace(tzinfo=timezone.utc).astimezone(_CET)
        start_secs = _secs(start_cet)
        setup_hrs = (datetime.utcnow() - start_tx.started_at).total_seconds() / 3600.0
    else:
        logger.warning("TSD end_setup: no SETUP_START tx")
        start_secs = end_secs
        setup_hrs = 0.0

    # Init context + WrapperSp(TT=2)
    await _init_context(infor_client, emp, job, suffix, whse, "end_setup")
    wrapper_resp = await _invoke(infor_client, _SP_WRAPPER,
                                 _build_wrapper_32p(emp, "2", job, suffix, oper_num),
                                 step="end_setup.wrapper", infobar_index=24)
    trans_num = _extract_trans_num(wrapper_resp, index=28)
    logger.info("TSD end_setup: TransNum=%s from WrapperSp", trans_num)

    # WrapperSp(TT=2) transforms TT=1→TT=2. Only fix TT=2.
    await _fix_dcsfc_timestamps(infor_client, job, suffix, oper_num,
                                trans_type=2, start_seconds=start_secs,
                                end_seconds=end_secs, hours=setup_hrs,
                                step="end_setup.fix_tt2", trans_num=trans_num)

    # Local tx
    await _record_tx(db, username, WorkshopTransType.SETUP_END, job, suffix, oper_num,
                     item=item, actual_hours=setup_hrs)

    # Auto-start work
    result = await start_work(infor_client, db, username, emp_num, job, suffix, oper_num, item, whse)
    result["message"] = f"Setup ended ({setup_hrs * 60:.1f}min), work auto-started"
    return result


async def start_work(
    infor_client: Any,
    db: AsyncSession,
    username: str,
    emp_num: str,
    job: str, suffix: str, oper_num: str,
    item: str = "", whse: str = "MAIN",
) -> Dict[str, Any]:
    """Start Work — ValidateMachine → WrapperSp(TT=3) → fix StartTime → Mchtrx."""
    emp = _fmt_emp(emp_num)
    start_secs = _now_cet_seconds()
    logger.info("TSD start_work: job=%s/%s oper=%s", job, suffix, oper_num)

    # Init context
    await _init_context(infor_client, emp, job, suffix, whse, "start_work")

    # ValidateMachine (TT=H) → resolve stroj + wc
    machine = await _resolve_machine(infor_client, job, suffix, oper_num, emp, "H", item, whse)
    stroj = machine["stroj"]
    wc = machine["wc"]

    # WrapperSp(TT=3) — creates DcSfc start record
    wrapper_resp = await _invoke(infor_client, _SP_WRAPPER,
                                 _build_wrapper_32p(emp, "3", job, suffix, oper_num),
                                 step="start_work.wrapper", infobar_index=24)
    trans_num = _extract_trans_num(wrapper_resp, index=28)
    logger.info("TSD start_work: TransNum=%s from WrapperSp", trans_num)

    # Fix StartTime on new TT=3 record
    await _fix_dcsfc_timestamps(infor_client, job, suffix, oper_num,
                                trans_type=3, start_seconds=start_secs,
                                step="start_work.fix", trans_num=trans_num)

    # Mchtrx (TT=H) — start machine transaction
    if stroj:
        try:
            await _invoke(infor_client, _SP_MCHTRX,
                          [emp, "H", job, suffix, oper_num, wc, stroj, "", ""],
                          step="start_work.mchtrx", infobar_index=7)
        except TsdError as exc:
            logger.warning("TSD Mchtrx start skipped: %s", exc)

    # Local tx
    await _record_tx(db, username, WorkshopTransType.START, job, suffix, oper_num,
                     wc=wc, item=item, start_seconds_cet=start_secs)

    return {
        "status": "ok",
        "message": f"Work started (stroj={stroj or 'none'}, wc={wc})",
        "stroj": stroj or None,
        "wc": wc or None,
    }


async def end_work(
    infor_client: Any,
    db: AsyncSession,
    username: str,
    emp_num: str,
    job: str, suffix: str, oper_num: str,
    item: str = "", whse: str = "MAIN",
    qty_complete: float = 0.0,
    qty_scrapped: float = 0.0,
    oper_complete: bool = False,
    job_complete: bool = False,
) -> Dict[str, Any]:
    """End Work — InsWrapperSp(TT=4) + fix timestamps + MachineVal + DcSfcMchtrx."""
    emp = _fmt_emp(emp_num)
    end_secs = _now_cet_seconds()
    logger.info("TSD end_work: job=%s/%s oper=%s qty=%s scrap=%s", job, suffix, oper_num, qty_complete, qty_scrapped)

    # Get start time from Gestima local tx
    start_tx = await _find_start_tx(db, username, job, suffix, oper_num, WorkshopTransType.START)
    if start_tx and start_tx.started_at:
        start_cet = start_tx.started_at.replace(tzinfo=timezone.utc).astimezone(_CET)
        start_secs = _secs(start_cet)
        run_hrs = (datetime.utcnow() - start_tx.started_at).total_seconds() / 3600.0
    else:
        logger.warning("TSD end_work: no START tx, using 0 hours")
        start_secs = end_secs
        run_hrs = 0.0

    # Init context
    await _init_context(infor_client, emp, job, suffix, whse, "end_work")

    # InsWrapperSp(TT=4) — transforms TT=3→TT=4 (doesn't create new record)
    ins_resp = await _invoke(infor_client, _SP_INS_WRAPPER,
                             _build_ins_wrapper_29p(emp, "4", job, suffix, oper_num,
                                                    qty_complete, qty_scrapped, oper_complete),
                             step="end_work.ins_wrapper", infobar_index=26)
    trans_num = _extract_trans_num(ins_resp, index=28)
    logger.info("TSD end_work: TransNum=%s from InsWrapperSp", trans_num)

    # Fix TT=4 (the converted record). No TT=3 exists anymore.
    # Key fix vs fiddler: StartTime = actual start (from Gestima), NOT end time!
    await _fix_dcsfc_timestamps(infor_client, job, suffix, oper_num,
                                trans_type=4, start_seconds=start_secs,
                                end_seconds=end_secs, hours=run_hrs,
                                step="end_work.fix_tt4", trans_num=trans_num)

    # MachineVal (TT=J) — resolve stroj for end
    machine = await _resolve_machine(infor_client, job, suffix, oper_num, emp, "J", item, whse)
    stroj = machine["stroj"]
    wc = machine["wc"]

    # DcSfcMchtrx (TT=J) — end machine transaction
    if stroj:
        try:
            mchtrx_params = [
                "",             # [0]
                emp,            # [1]  gvEmpNum
                "1",            # [2]  vMultiJobFlag
                "J",            # [3]  vTransType
                job,            # [4]  vJob
                suffix,         # [5]  vSuffix
                oper_num,       # [6]  vOperNum
                item,           # [7]  vItem
                whse,           # [8]  vWhse
                _fmt_qty(qty_complete),     # [9]
                _fmt_qty(qty_scrapped),     # [10]
                _fmt_qty(qty_complete),     # [11] vQtyMoved
                _flag(oper_complete),       # [12]
                "",             # [13] vLoc
                "0",            # [14] vLot
                "",             # [15] vReasonCode
                "",             # [16] vSerNumList
                "",             # [17]
                "",             # [18]
                "",             # [19]
                "1",            # [20] vUkoncitStrojFlag
                "",             # [21] RV(vInfoBar) — OUT
            ]
            await _invoke(infor_client, _SP_DC_SFC_MCHTRX,
                          mchtrx_params, step="end_work.dc_sfc_mchtrx", infobar_index=21)
        except TsdError as exc:
            logger.warning("TSD DcSfcMchtrx end skipped: %s", exc)

    # Local tx
    await _record_tx(db, username, WorkshopTransType.STOP, job, suffix, oper_num,
                     wc=wc, item=item, qty_completed=qty_complete, qty_scrapped=qty_scrapped,
                     actual_hours=run_hrs)

    return {
        "status": "ok",
        "message": f"Work ended ({run_hrs:.2f}h, {qty_complete:.0f} ks, stroj={stroj or 'none'})",
        "stroj": stroj or None,
        "wc": wc or None,
    }
