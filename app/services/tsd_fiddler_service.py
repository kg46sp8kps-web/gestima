"""TSD Fiddler — Fiddler-verified START/END pairing with machine transactions.

Based on verified Fiddler trace from production InduStream client.
Each SP call and its parameters are 1:1 verified against the trace.

Key differences from old industream_tsd_service.py (Presunout flow):
  - Uses START/END pairing (TT=1/2 setup, TT=3/4 work) — NOT Presunout (TT=4 + SFC34)
  - Includes machine transactions (Mchtrx) — stroj tracking
  - SourceModul = "B" (not "TSD")
  - Does NOT call SFC34 — Infor calculates hours server-side from start/end pairing
  - emp_num formatted as 6 chars right-padded with spaces

Flow summary (each flow starts with _init_dcsfc_context):
  _init_dcsfc_context: ValidateEmpDcSfc → InitParms×2 → ValidateJob → ValidateMultiJobDcSfc
  start_work:  init → ValidateMachine(H) → Wrapper(TT=3) → Kapacity → Mchtrx(H)
  end_work:    init → InsWrapper(TT=4) → Kapacity → MachineVal(J) → DcSfcMchtrx(J)
  start_setup: init → Wrapper(TT=1)
  end_setup:   init → Wrapper(TT=2) → then full start_work() flow
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IDO + SP constants (Fiddler-verified names)
# ---------------------------------------------------------------------------
_IDO = "IteCzTsdStd"

# --- Initialization SPs (MUST be called before Wrapper/InsWrapper) ---
_SP_VALIDATE_EMP_NUM_DCSFC = "IteCzTsdValidateEmpNumDcSfcSp"       # 7p  — init DcSfc context for employee
_SP_INIT_PARMS = "IteCzTsdInitParmsSp"                              # 5p  — init session parameters (called 2x)
_SP_VALIDATE_JOB = "IteCzTsdValidateJobSp"                          # 8p  — set current job in DcSfc context
_SP_VALIDATE_MULTI_JOB_DCSFC = "IteCzTsdValidateMultiJobDcSfcSp"   # 3p  — validate multi-job, sets JOB/MJOB

# --- Action SPs ---
_SP_VALIDATE_OPER_NUM_MACHINE = "IteCzTsdValidateOperNumMachineSp"  # 11p — start machine validation
_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"                       # 32p — DcSfc wrapper (start)
_SP_KAPACITY_UPDATE = "IteCzTsdKapacityUpdateSp"                    # 3p  — capacity update
_SP_UPDATE_MCHTRX = "IteCzTsdUpdateMchtrxSp"                       # 9p  — machine transaction (start)
_SP_INS_WRAPPER_DCSFC_UPDATE = "IteCzInsWrapperDcsfcUpdateSp"       # 27p — DcSfc wrapper (end)
_SP_MACHINE_VAL_OPER_NUM = "IteCzTsdMachineValOperNumSp"            # 11p — end machine validation
_SP_UPDATE_DC_SFC_MCHTRX = "IteCzTsdUpdateDcSfcMchtrxSp"           # 22p — machine transaction (end)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TsdFiddlerError(Exception):
    """Base error for TSD Fiddler operations."""

    def __init__(self, sp_name: str, message: str, step: str = ""):
        self.sp_name = sp_name
        self.step = step
        super().__init__(f"[{step}] {sp_name}: {message}" if step else f"{sp_name}: {message}")


class TsdValidationError(TsdFiddlerError):
    """Validation failure (e.g. invalid job/oper) — maps to HTTP 422."""
    pass


class TsdInfoBarError(TsdFiddlerError):
    """InfoBar error from Infor SP — maps to HTTP 502."""
    pass


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _fmt_emp(num: str) -> str:
    """Format employee number: 6 chars, right-aligned with leading spaces.

    Fiddler trace shows emp_num as "     20" (6 chars wide, right-padded).
    """
    return num.strip().rjust(6)


def _fmt_qty(value: float) -> str:
    """Format quantity with 2 decimal places (Fiddler format)."""
    return f"{value:.2f}"


def _flag(value: bool) -> str:
    """Boolean → '1' or '0'."""
    return "1" if value else "0"


def _build_named_params(
    values: List[str],
    output_indices: List[int] = None,
) -> List[Dict[str, Any]]:
    """Build named params array for POST method call (InduStream format).

    Args:
        values: Positional parameter values
        output_indices: Indices of output parameters (get IsOutput=True)
    """
    output_set = set(output_indices or [])
    params = []
    for i, val in enumerate(values):
        p: Dict[str, Any] = {"ParamName": f"P{i}"}
        if i in output_set:
            p["IsOutput"] = True
        if val != "":
            p["Value"] = val
        params.append(p)
    return params


async def _invoke(
    infor_client: Any,
    sp_name: str,
    params: List[str],
    infobar_index: int = -1,
    step: str = "",
    output_indices: List[int] = None,
    use_post: bool = False,
) -> Dict[str, Any]:
    """Call an Infor SP, validate response.

    Uses POST with named params (InduStream-compatible) by default.
    Falls back to GET positional if use_post=False.

    Checks:
      1. MessageCode must be 0, 200, or 210
      2. If infobar_index >= 0, checks InfoBar for error messages

    Raises:
      TsdValidationError — for MessageCode failures
      TsdInfoBarError — for InfoBar error strings
    """
    logger.info(
        "FIDDLER SP call [%s]: %s (%d params) infobar_idx=%d post=%s",
        step, sp_name, len(params), infobar_index, use_post,
    )
    logger.debug("FIDDLER SP %s params: %s", sp_name, params)

    if use_post:
        named = _build_named_params(params, output_indices or [])
        resp = await infor_client.invoke_method_params(
            ido_name=_IDO,
            method_name=sp_name,
            params=named,
        )
    else:
        resp = await infor_client.invoke_method_positional(
            ido_name=_IDO,
            method_name=sp_name,
            positional_values=params,
        )

    msg_code = resp.get("MessageCode", -1)
    ret_val = str(resp.get("ReturnValue", "") or "")
    message = str(resp.get("Message", "") or "")

    logger.info("FIDDLER SP %s response: MessageCode=%s ReturnValue=%s", sp_name, msg_code, ret_val[:200] if ret_val else "")
    logger.info("FIDDLER SP %s Parameters: %s", sp_name, resp.get("Parameters", []))

    if msg_code not in (0, 200, 210):
        error = ret_val or message or f"MessageCode={msg_code}"
        logger.error("FIDDLER SP %s failed (MessageCode=%s): %s", sp_name, msg_code, error)
        raise TsdValidationError(sp_name, error, step)

    # Check InfoBar for error messages
    params_arr = resp.get("Parameters")
    if infobar_index >= 0 and params_arr and isinstance(params_arr, list):
        if infobar_index < len(params_arr):
            infobar = str(params_arr[infobar_index] or "").strip()
            logger.info("FIDDLER SP %s InfoBar[%d]='%s'", sp_name, infobar_index, infobar)
            if infobar and "was successful" not in infobar.lower():
                logger.error("FIDDLER SP %s InfoBar error: %s", sp_name, infobar)
                raise TsdInfoBarError(sp_name, infobar, step)
        else:
            logger.warning(
                "FIDDLER SP %s: infobar_index=%d but Parameters has only %d items",
                sp_name, infobar_index, len(params_arr),
            )

    logger.info("FIDDLER SP %s OK [%s]", sp_name, step)
    return resp


def _extract_outputs(resp: Dict[str, Any], mapping: Dict[str, int]) -> Dict[str, str]:
    """Extract output parameter values from SP response.

    Args:
        resp: Full SP response dict
        mapping: {output_name: parameter_index}

    Returns:
        Dict of {output_name: value_string}
    """
    params_arr = resp.get("Parameters") or []
    result = {}
    for name, idx in mapping.items():
        if isinstance(params_arr, list) and idx < len(params_arr):
            result[name] = str(params_arr[idx] or "").strip()
        else:
            result[name] = ""
    return result


def _now_cet_seconds() -> int:
    """Current time as seconds-from-midnight in CET (UTC+1) for Infor start_time/end_time."""
    cet = timezone(timedelta(hours=1))
    now = datetime.now(cet)
    return now.hour * 3600 + now.minute * 60 + now.second


async def _update_dcsfc_field(
    infor_client: Any,
    item_id: str,
    properties: List[Dict[str, Any]],
    step: str = "",
) -> bool:
    """Update DcSfc record fields via execute_update_request.

    Args:
        item_id: _ItemId from LoadCollection (contains optimistic concurrency DT)
        properties: List of {"Name": "FieldName", "Value": "val", "Modified": True}
        step: Logging context

    Returns True on success, False on failure (non-critical, logged as warning).
    """
    try:
        body = {
            "IDOName": "SLDcsfcs",
            "Changes": [
                {
                    "Action": 2,  # 1=Insert, 2=Update, 3=Delete (Int64!)
                    "ItemId": item_id,
                    "Properties": properties,
                }
            ],
        }
        resp = await infor_client.execute_update_request(body)
        logger.info("FIDDLER _update_dcsfc: %s result: %s", step, resp)
        return True
    except Exception as exc:
        logger.warning("FIDDLER _update_dcsfc failed: %s [%s]", exc, step)
        return False


async def _fix_dcsfc_start(
    infor_client: Any,
    job: str,
    suffix: str,
    oper_num: str,
    trans_type: int = 3,
    step: str = "",
) -> None:
    """Fix StartTime on the most recent MJOB record after WrapperSp.

    REST API (stateless GET) causes IteCzTsdUpdateDcSfcSp to set stale
    start_time (always 77744 = 21:35:44) on MJOB records. JOB records are fine.

    Args:
        trans_type: 3 for work start, 1 for setup start
    """
    seconds = _now_cet_seconds()
    try:
        resp = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=["TransNum", "TransType", "StartTime", "_ItemId"],
            filter=(
                f"Job = '{job}' AND Suffix = {suffix} AND OperNum = {oper_num}"
                f" AND Termid = 'MJOB' AND TransType = {trans_type}"
            ),
            order_by="TransNum DESC",
            record_cap=1,
        )
        rows = resp.get("data", [])
        if not rows:
            logger.warning("FIDDLER _fix_dcsfc_start: no TT=%d MJOB for %s/%s/%s [%s]", trans_type, job, suffix, oper_num, step)
            return

        row = rows[0]
        tn, item_id = row.get("TransNum", ""), row.get("_ItemId", "")
        logger.info("FIDDLER _fix_dcsfc_start: TN=%s TT=%d old=%s new=%d [%s]", tn, trans_type, row.get("StartTime"), seconds, step)

        if item_id:
            await _update_dcsfc_field(infor_client, item_id, [
                {"Name": "StartTime", "Value": str(seconds), "Modified": True},
            ], f"{step}.TT{trans_type}.start")
    except Exception as exc:
        logger.warning("FIDDLER _fix_dcsfc_start failed: %s [%s]", exc, step)


async def _fix_dcsfc_end(
    infor_client: Any,
    job: str,
    suffix: str,
    oper_num: str,
    tt_start: int = 3,
    tt_end: int = 4,
    step: str = "",
) -> None:
    """Fix timestamps after WrapperSp/InsWrapperSp end — fixes BOTH start and end records.

    WrapperSp/InsWrapperSp creates/converts an end record and closes the start record.
    Both get stale timestamps. Infor calculates hours from end.StartTime - start.StartTime,
    so both must have correct times.

    Args:
        tt_start: TransType of the start record (3 for work, 1 for setup)
        tt_end: TransType of the end record (4 for work, 2 for setup)

    Fix:
      1. Start record (latest): set EndTime to now
      2. End record (latest): set StartTime AND EndTime to now
    """
    seconds = _now_cet_seconds()
    try:
        # Fix start record EndTime
        resp3 = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=["TransNum", "EndTime", "_ItemId"],
            filter=(
                f"Job = '{job}' AND Suffix = {suffix} AND OperNum = {oper_num}"
                f" AND Termid = 'MJOB' AND TransType = {tt_start}"
            ),
            order_by="TransNum DESC",
            record_cap=1,
        )
        rows3 = resp3.get("data", [])
        if rows3:
            row3 = rows3[0]
            tn3, item_id3 = row3.get("TransNum", ""), row3.get("_ItemId", "")
            logger.info("FIDDLER _fix_dcsfc_end TT=%d: TN=%s EndTime old=%s new=%d [%s]", tt_start, tn3, row3.get("EndTime"), seconds, step)
            if item_id3:
                await _update_dcsfc_field(infor_client, item_id3, [
                    {"Name": "EndTime", "Value": str(seconds), "Modified": True},
                ], f"{step}.TT{tt_start}.end")

        # Fix end record Start+End (Infor uses this for hour calculation!)
        resp4 = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=["TransNum", "StartTime", "EndTime", "_ItemId"],
            filter=(
                f"Job = '{job}' AND Suffix = {suffix} AND OperNum = {oper_num}"
                f" AND Termid = 'MJOB' AND TransType = {tt_end}"
            ),
            order_by="TransNum DESC",
            record_cap=1,
        )
        rows4 = resp4.get("data", [])
        if rows4:
            row4 = rows4[0]
            tn4, item_id4 = row4.get("TransNum", ""), row4.get("_ItemId", "")
            logger.info(
                "FIDDLER _fix_dcsfc_end TT=%d: TN=%s Start old=%s End old=%s new=%d [%s]",
                tt_end, tn4, row4.get("StartTime"), row4.get("EndTime"), seconds, step,
            )
            if item_id4:
                await _update_dcsfc_field(infor_client, item_id4, [
                    {"Name": "StartTime", "Value": str(seconds), "Modified": True},
                    {"Name": "EndTime", "Value": str(seconds), "Modified": True},
                ], f"{step}.TT{tt_end}.start_end")
        else:
            logger.warning("FIDDLER _fix_dcsfc_end: no TT=%d MJOB for %s/%s/%s [%s]", tt_end, job, suffix, oper_num, step)

    except Exception as exc:
        logger.warning("FIDDLER _fix_dcsfc_end failed: %s [%s]", exc, step)


async def _close_dcsfc_direct(
    infor_client: Any,
    emp: str,
    job: str,
    suffix: str,
    oper_num: str,
    qty_complete: float,
    qty_scrapped: float,
    oper_complete: bool,
    seconds: int,
    step: str = "",
) -> None:
    """Close a DcSfc TT=3 record and create TT=4, bypassing InsWrapperSp.

    InsWrapperSp has a multi-job bug: it finds the oldest open TT=3 MJOB record
    for the employee regardless of job. This function targets the EXACT job/oper.

    Steps:
      1. Find TT=3 MJOB for this job/oper → set EndTime + qty (Update)
      2. Create TT=4 MJOB record with correct times + qty (Insert)
    """
    qty_moved = qty_complete
    # TransDate format matching Infor: "YYYYMMDD HH:MM:SS.000"
    cet = timezone(timedelta(hours=1))
    now_cet = datetime.now(cet)
    trans_date = now_cet.strftime("%Y%m%d %H:%M:%S.000")
    try:
        # --- Step 1: Update TT=3 (set EndTime + qty) ---
        resp = await infor_client.load_collection(
            ido_name="SLDcsfcs",
            properties=["TransNum", "StartTime", "EndTime", "Wc", "_ItemId"],
            filter=(
                f"Job = '{job}' AND Suffix = {suffix} AND OperNum = {oper_num}"
                f" AND Termid = 'MJOB' AND TransType = 3"
            ),
            order_by="TransNum DESC",
            record_cap=1,
        )
        rows = resp.get("data", [])
        if not rows:
            logger.warning(
                "FIDDLER _close_dcsfc_direct: no open TT=3 MJOB for %s/%s/%s [%s]",
                job, suffix, oper_num, step,
            )
            return

        row = rows[0]
        tn = row.get("TransNum", "")
        item_id = row.get("_ItemId", "")
        tt3_wc = row.get("Wc") or ""
        logger.info(
            "FIDDLER _close_dcsfc_direct: closing TN=%s EndTime→%d qty=%.2f scrap=%.2f wc=%s [%s]",
            tn, seconds, qty_complete, qty_scrapped, tt3_wc, step,
        )

        if not item_id:
            logger.warning("FIDDLER _close_dcsfc_direct: no _ItemId for TN=%s", tn)
            return

        props_tt3 = [
            {"Name": "EndTime", "Value": str(seconds), "Modified": True},
            {"Name": "QtyComplete", "Value": _fmt_qty(qty_complete), "Modified": True},
            {"Name": "QtyScrapped", "Value": _fmt_qty(qty_scrapped), "Modified": True},
        ]
        await _update_dcsfc_field(infor_client, item_id, props_tt3, f"{step}.close_tt3")

        # --- Step 2: Insert TT=4 record (End Run) ---
        # TT=4 carries qty + end timestamp. Infor uses TT=4 for hour calculation.
        # Must include TransDate, Wc, SourceModule — otherwise Infor UI won't display it.
        tt4_props = [
            {"Name": "TransType", "Value": "4", "Modified": True},
            {"Name": "TransDate", "Value": trans_date, "Modified": True},
            {"Name": "EmpNum", "Value": emp.rjust(7), "Modified": True},
            {"Name": "Job", "Value": job, "Modified": True},
            {"Name": "Suffix", "Value": suffix, "Modified": True},
            {"Name": "OperNum", "Value": oper_num, "Modified": True},
            {"Name": "Wc", "Value": tt3_wc, "Modified": True},
            {"Name": "StartTime", "Value": str(seconds), "Modified": True},
            {"Name": "EndTime", "Value": str(seconds), "Modified": True},
            {"Name": "QtyComplete", "Value": _fmt_qty(qty_complete), "Modified": True},
            {"Name": "QtyScrapped", "Value": _fmt_qty(qty_scrapped), "Modified": True},
            {"Name": "QtyMoved", "Value": _fmt_qty(qty_moved), "Modified": True},
            {"Name": "Termid", "Value": "MJOB", "Modified": True},
            {"Name": "Source", "Value": "M", "Modified": True},
            {"Name": "dcsfcuf_ite_cz_ins_dcsfc_src_module", "Value": "B", "Modified": True},
        ]
        try:
            body_tt4 = {
                "IDOName": "SLDcsfcs",
                "Changes": [
                    {
                        "Action": 1,  # 1=Insert
                        "Properties": tt4_props,
                    }
                ],
            }
            tt4_resp = await infor_client.execute_update_request(body_tt4)
            logger.info("FIDDLER _close_dcsfc_direct: TT=4 insert result: %s [%s]", tt4_resp, step)
        except Exception as exc:
            logger.warning("FIDDLER _close_dcsfc_direct: TT=4 insert failed: %s [%s]", exc, step)

    except Exception as exc:
        logger.warning("FIDDLER _close_dcsfc_direct failed: %s [%s]", exc, step)


# ---------------------------------------------------------------------------
# Initialization — MUST be called before every WrapperSp / InsWrapperSp
# ---------------------------------------------------------------------------

def _build_validate_emp_num_dcsfc_7p(emp: str) -> List[str]:
    """IteCzTsdValidateEmpNumDcSfcSp — 7 params.

    Initializes DcSfc context for employee. MUST be called first.
    HAR Entry 3/40/66: P0=emp, P1-P6 are outputs.
    """
    return [
        emp,    # [0]  gvEmpNum (INPUT)
        "",     # [1]  RV — employee count/validation
        "",     # [2]  RV — validation status (0/1)
        "",     # [3]  RV — work center / job context
        "",     # [4]  RV — additional flag
        "",     # [5]  RV — capacity/hours
        "",     # [6]  RV — error message
    ]


def _build_init_parms_kontrola_5p() -> List[str]:
    """IteCzTsdInitParmsSp — 5 params (call #1 of 2).

    Sets parameter "KontrolaPrijAPresunKusuNaOper".
    HAR Entry 41/67.
    """
    return [
        "00000",                                # [0]  config ID
        "KontrolaPrijAPresunKusuNaOper",        # [1]  parameter name
        "",                                     # [2]  RV — config value
        "1",                                    # [3]  input flag
        "Nothing",                              # [4]  literal "Nothing"
    ]


def _build_init_parms_vydej_5p() -> List[str]:
    """IteCzTsdInitParmsSp — 5 params (call #2 of 2).

    Sets parameter "VydejDoNadrizeneho".
    HAR Entry 42/68.
    """
    return [
        "00000",                    # [0]  config ID
        "VydejDoNadrizeneho",       # [1]  parameter name
        "0",                        # [2]  RV — config value
        "0",                        # [3]  input flag
        "",                         # [4]  empty
    ]


def _build_validate_job_8p(job: str, suffix: str, whse: str) -> List[str]:
    """IteCzTsdValidateJobSp — 8 params.

    Sets current job in DcSfc context. CRITICAL for correct timestamps!
    HAR Entry 4/43: P0="25VP11/073-0" (job-suffix), P4="MAIN", rest empty/output.
    """
    return [
        f"{job}-{suffix}",     # [0]  vJob-vSuffix (combined!)
        "",                     # [1]  RV — output
        "",                     # [2]  RV — output
        "",                     # [3]  RV — output
        whse,                   # [4]  vWhse ("MAIN")
        "",                     # [5]  RV — output
        "",                     # [6]  empty input
        "",                     # [7]  RV — output
    ]


def _build_validate_multi_job_dcsfc_3p(emp: str) -> List[str]:
    """IteCzTsdValidateMultiJobDcSfcSp — 3 params.

    Validates multi-job mode. Returns P1=1 for MJOB, P1=0 for JOB.
    HAR Entry 11/29/39/58/65: P0=emp, P1=output(multi-job flag), P2=output.
    """
    return [
        emp,    # [0]  gvEmpNum (INPUT)
        "",     # [1]  RV — multi-job flag (1=MJOB, 0=JOB)
        "",     # [2]  RV — additional info
    ]


async def _init_dcsfc_context(
    infor_client: Any,
    emp: str,
    job: str,
    suffix: str,
    whse: str,
    step_prefix: str,
) -> None:
    """Initialize DcSfc context — MUST be called before every WrapperSp/InsWrapperSp.

    InduStream calls these SPs in order before any DcSfc write.
    Without them, WrapperSp creates empty records or uses stale timestamps.

    Sequence (HAR verified):
      1. ValidateEmpNumDcSfcSp — init employee context
      2. InitParmsSp x2 — init session parameters
      3. ValidateJobSp — set CURRENT JOB in DcSfc context (CRITICAL for timestamps!)
      4. ValidateMultiJobDcSfcSp — set JOB/MJOB mode
    """
    # Step 1: Validate employee for DcSfc
    # HAR: P1-P6 are IsOutput=true
    await _invoke(
        infor_client, _SP_VALIDATE_EMP_NUM_DCSFC,
        _build_validate_emp_num_dcsfc_7p(emp),
        infobar_index=-1, step=f"{step_prefix}.init_emp",
        output_indices=[1, 2, 3, 4, 5, 6],
    )

    # Step 2: Init session parameters (2 calls, always as a pair)
    # HAR: P2 is IsOutput=true (returns config value)
    await _invoke(
        infor_client, _SP_INIT_PARMS,
        _build_init_parms_kontrola_5p(),
        infobar_index=-1, step=f"{step_prefix}.init_parms_1",
        output_indices=[2],
    )
    await _invoke(
        infor_client, _SP_INIT_PARMS,
        _build_init_parms_vydej_5p(),
        infobar_index=-1, step=f"{step_prefix}.init_parms_2",
        output_indices=[2],
    )

    # Step 3: Validate job — sets CURRENT JOB in DcSfc context
    # HAR: P0-P5,P7 are IsOutput=true
    await _invoke(
        infor_client, _SP_VALIDATE_JOB,
        _build_validate_job_8p(job, suffix, whse),
        infobar_index=-1, step=f"{step_prefix}.validate_job",
        output_indices=[0, 1, 2, 3, 4, 5, 7],
    )

    # Step 4: Validate multi-job mode (sets JOB/MJOB context)
    # HAR: P1,P2 are IsOutput=true
    await _invoke(
        infor_client, _SP_VALIDATE_MULTI_JOB_DCSFC,
        _build_validate_multi_job_dcsfc_3p(emp),
        infobar_index=-1, step=f"{step_prefix}.validate_multi_job",
        output_indices=[1, 2],
    )

    logger.info("FIDDLER DcSfc context initialized for %s job=%s/%s [%s]", emp, job, suffix, step_prefix)


# ---------------------------------------------------------------------------
# Parameter builders (one per SP, Fiddler-verified)
# ---------------------------------------------------------------------------

def _build_validate_oper_num_machine_11p(
    job: str, suffix: str, oper_num: str, emp: str,
    tt: str, item: str, whse: str,
) -> List[str]:
    """IteCzTsdValidateOperNumMachineSp — 11 params.

    Used at START to validate job/oper and resolve stroj + wc.
    TT="H" for start_work validation.
    """
    return [
        job,        # [0]  vJob
        suffix,     # [1]  vSuffix
        oper_num,   # [2]  vOperNum
        emp,        # [3]  gvEmpNum
        tt,         # [4]  vTransType (H=start)
        item,       # [5]  vItem (DerJobItem)
        whse,       # [6]  vWhse
        "",         # [7]  RV(vStroj) — OUT
        "",         # [8]  RV(vWc) — OUT
        "",         # [9]  RV(vInfoBar) — OUT
        "",         # [10] RV(vResid) — OUT
    ]


def _build_wrapper_32p(
    emp: str, multi_job: str, tt: str,
    job: str, suffix: str, oper_num: str,
) -> List[str]:
    """IteCzTsdUpdateDcSfcWrapperSp — 32 params.

    START wrapper: creates DcSfc record with start_time.
    TT=1 (setup start), TT=3 (work start).
    Key: P19=SourceModul="B", P17=wc="" (SP resolves from jobroute).
    P30=empty (Infor uses server clock — HAR verified, InduStream never sends timestamp).
    P31=no value (HAR verified).
    """
    return [
        "",             # [0]
        emp,            # [1]  gvEmpNum
        multi_job,      # [2]  vMultiJobFlag ("1" always)
        tt,             # [3]  vTransType
        job,            # [4]  vJob
        suffix,         # [5]  vSuffix
        oper_num,       # [6]  vOperNum
        "",             # [7]  vQtyComplete
        "",             # [8]  vQtyScrapped
        "",             # [9]  vQtyMoved
        "0",            # [10] vOperCompleteFlag (HAR: "0")
        "0",            # [11] vJobCompleteFlag (HAR: "0")
        "0",            # [12] vIssueParentFlag (HAR: "0")
        "",             # [13] vLoc
        "",             # [14] vLot
        "",             # [15] vReasonCode
        "",             # [16] vSerNumList
        "",             # [17] vWc (empty — SP resolves from jobroute)
        "",             # [18]
        "B",            # [19] vSourceModul ("B" per HAR, NOT "TSD")
        "",             # [20] gvIdMachine (no Value in HAR)
        "",             # [21] gvResid (no Value in HAR)
        "0",            # [22]
        "",             # [23] vMode (no Value in HAR)
        "",             # [24] RV(vInfoBar) — OUT
        "",             # [25]
        "",             # [26]
        "",             # [27]
        "",             # [28]
        "",             # [29]
        "",             # [30] vDatumTransakce — EMPTY (HAR verified!)
        "",             # [31] (no Value in HAR)
    ]


def _build_kapacity_3p(guid: str = "0") -> List[str]:
    """IteCzTsdKapacityUpdateSp — 3 params.

    Best-effort capacity update. Non-critical for flow.
    """
    return [
        "J",    # [0]  vMode
        guid,   # [1]  vPtrKapacity
        "",     # [2]  RV(vInfoBar)
    ]


def _build_update_mchtrx_9p(
    emp: str, tt: str, job: str, suffix: str,
    oper_num: str, wc: str, stroj: str,
) -> List[str]:
    """IteCzTsdUpdateMchtrxSp — 9 params.

    Machine transaction for START — creates Mchtrx record with start_time.
    TT="H" for start.
    """
    return [
        emp,        # [0]  gvEmpNum
        tt,         # [1]  vTransType (H=start)
        job,        # [2]  vJob
        suffix,     # [3]  vSuffix
        oper_num,   # [4]  vOperNum
        wc,         # [5]  vWc
        stroj,      # [6]  vStroj
        "",         # [7]  RV(vInfoBar)
        "",         # [8]  RV(vMchtrxTransNum)
    ]


def _build_ins_wrapper_dcsfc_update_27p(
    emp: str, multi_job: str, tt: str,
    job: str, suffix: str, oper_num: str,
    qty_complete: float, qty_scrapped: float,
    oper_complete: bool,
) -> List[str]:
    """IteCzInsWrapperDcsfcUpdateSp — 27 params.

    END wrapper: updates DcSfc record with end_time + quantities.
    TT=2 (setup end), TT=4 (work end).
    Layout verified from HAR trace Entry 56 (f2.har).
    Key: P0="1", P1="", P2=emp (shifted vs WrapperSp!), P21=SourceModul="B".
    """
    qty_moved = qty_complete
    return [
        "1",                            # [0]  @Connected (HAR verified — NOT empty!)
        "",                             # [1]  @TTermId (HAR: empty)
        emp,                            # [2]  @TEmpNum
        multi_job,                      # [3]  @TMultiJob ("1")
        tt,                             # [4]  @TTransType
        job,                            # [5]  @TJobNum
        suffix,                         # [6]  @TJobSuffix
        oper_num,                       # [7]  @TOperNum
        _fmt_qty(qty_complete),         # [8]  @TcQtuQtyComp
        _fmt_qty(qty_scrapped),         # [9]  @TcQtuQtyScrap
        _fmt_qty(qty_moved),            # [10] @TcQtuQtyMove
        _flag(oper_complete),           # [11] @TComplete
        "",                             # [12] @TClose (HAR: no Value)
        "0",                            # [13] @TIssueParent (HAR: 0)
        "",                             # [14] @TLocation
        "",                             # [15] @TLot
        "",                             # [16] @TReasonCode
        "0",                            # [17] @TCoProductMix (HAR: "0")
        "",                             # [18] @SerNumList
        "",                             # [19] @TWc
        "",                             # [20] @Note
        "B",                            # [21] @SourceModul ("B")
        "",                             # [22] @IdMachine
        "",                             # [23] @ResId
        "0",                            # [24] @AutoPost (HAR: "0")
        "",                             # [25] @Mode
        "",                             # [26] @Infobar — OUT
        "",                             # [27] @TransDate (optional, null)
        "",                             # [28] @DcsfcTransNum — OUT (returns updated record's TransNum)
    ]


def _build_machine_val_oper_num_11p(
    job: str, suffix: str, oper_num: str, emp: str,
    tt: str, item: str, whse: str,
) -> List[str]:
    """IteCzTsdMachineValOperNumSp — 11 params.

    Used at END to validate machine end. Different SP than start validation!
    TT="J" for end machine validation.
    """
    return [
        job,        # [0]  vJob
        suffix,     # [1]  vSuffix
        oper_num,   # [2]  vOperNum
        emp,        # [3]  gvEmpNum
        tt,         # [4]  vTransType (J=end)
        item,       # [5]  vItem
        whse,       # [6]  vWhse
        "",         # [7]  RV(vStroj) — OUT
        "",         # [8]  RV(vWc) — OUT
        "",         # [9]  RV(vInfoBar) — OUT
        "",         # [10] RV(vResid) — OUT
    ]


def _build_update_dc_sfc_mchtrx_22p(
    emp: str, multi_job: str, tt: str,
    job: str, suffix: str, oper_num: str,
    item: str, whse: str,
    qty_complete: float, qty_scrapped: float,
    oper_complete: bool,
) -> List[str]:
    """IteCzTsdUpdateDcSfcMchtrxSp — 22 params.

    Machine transaction for END — updates Mchtrx with end_time + quantities.
    Layout verified from HAR trace Entry 59 (f2.har).
    P[0]="" (empty!), P[1]=emp, P[2]=multi(Byte), P[3]="J" (letter trans type).
    P[7]=item, P[8]=whse (right after oper, NOT at P16/P17!).
    P[20]="1" (ukoncit_stroj_flag), P[21]=InfoBar OUT.
    """
    qty_moved = qty_complete
    return [
        "",                             # [0]  empty (HAR verified!)
        emp,                            # [1]  gvEmpNum
        multi_job,                      # [2]  vMultiJobFlag ("1") — Byte type
        tt,                             # [3]  vTransType ("J" for end machine)
        job,                            # [4]  vJob
        suffix,                         # [5]  vSuffix
        oper_num,                       # [6]  vOperNum
        item,                           # [7]  vItem (HAR: "46287507")
        whse,                           # [8]  vWhse (HAR: "MAIN")
        _fmt_qty(qty_complete),         # [9]  vQtyComplete
        _fmt_qty(qty_scrapped),         # [10] vQtyScrapped
        _fmt_qty(qty_moved),            # [11] vQtyMoved
        _flag(oper_complete),           # [12] vOperCompleteFlag
        "",                             # [13] vLoc
        "0",                            # [14] vLot (HAR shows "0")
        "",                             # [15] vReasonCode
        "",                             # [16] vSerNumList
        "",                             # [17]
        "",                             # [18]
        "",                             # [19]
        "1",                            # [20] vUkoncitStrojFlag
        "",                             # [21] RV(vInfoBar) — OUT
    ]


# ---------------------------------------------------------------------------
# Flow functions (4 public operations)
# ---------------------------------------------------------------------------

async def start_work(
    infor_client: Any,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    item: str = "",
    whse: str = "MAIN",
    kapacity_guid: str = "0",
) -> Dict[str, Any]:
    """Start Work — ValidateMachine(H) → Wrapper(TT=3) → Kapacity → Mchtrx(H).

    Returns dict with stroj, wc from ValidateMachine output.
    """
    emp = _fmt_emp(emp_num)
    logger.info(
        "FIDDLER start_work: job=%s/%s oper=%s emp=%s",
        job, suffix, oper_num, emp_num,
    )

    # Step 1: ValidateMachine (TT=H) — resolve stroj + wc
    # No InfoBar check (-1): output positions [7-10] contain data values, not messages
    validate_params = _build_validate_oper_num_machine_11p(
        job, suffix, oper_num, emp, "H", item, whse,
    )
    validate_resp = await _invoke(
        infor_client, _SP_VALIDATE_OPER_NUM_MACHINE,
        validate_params, infobar_index=-1, step="start_work.validate",
        output_indices=[7, 8, 9, 10],
    )
    # Output mapping (verified from Fiddler dump data[10]):
    #   p07 = emp echo (empty at start, "     20" at end) — NOT stroj!
    #   p08 = stroj (machine ID, e.g. "4-MT32", "1-STG240A")
    #   p09 = wc (work center, e.g. "SH2", "PS", "BK")
    #   p10 = resid/error message
    outputs = _extract_outputs(validate_resp, {
        "p7": 7, "stroj": 8, "wc": 9, "resid": 10,
    })
    logger.info(
        "FIDDLER start_work validate outputs: p7=%s stroj=%s wc=%s resid=%s",
        outputs.get("p7"), outputs.get("stroj"), outputs.get("wc"), outputs.get("resid"),
    )
    stroj = outputs["stroj"]
    wc = outputs["wc"]

    # Step 2: Init DcSfc context (REQUIRED before WrapperSp)
    await _init_dcsfc_context(infor_client, emp, job, suffix, whse, "start_work")

    # Step 3: Wrapper (TT=3) — create DcSfc start record
    wrapper_params = _build_wrapper_32p(emp, "1", "3", job, suffix, oper_num)
    await _invoke(
        infor_client, _SP_WRAPPER,
        wrapper_params, infobar_index=24, step="start_work.wrapper",
        output_indices=[24],
    )
    # Fix MJOB start_time (REST API bug: IteCzTsdUpdateDcSfcSp sets stale 77744=21:35:44)
    await _fix_dcsfc_start(infor_client, job, suffix, oper_num, trans_type=3, step="start_work")

    # Step 4: KapacityUpdate (best-effort)
    try:
        kapacity_params = _build_kapacity_3p(kapacity_guid)
        await _invoke(
            infor_client, _SP_KAPACITY_UPDATE,
            kapacity_params, infobar_index=2, step="start_work.kapacity",
            output_indices=[2],
        )
    except Exception as exc:
        logger.warning("FIDDLER start_work KapacityUpdate skipped: %s", exc)

    # Step 5: Mchtrx (TT=H) — create machine transaction start (only if stroj exists)
    if stroj:
        mchtrx_params = _build_update_mchtrx_9p(emp, "H", job, suffix, oper_num, wc, stroj)
        await _invoke(
            infor_client, _SP_UPDATE_MCHTRX,
            mchtrx_params, infobar_index=7, step="start_work.mchtrx",
            output_indices=[8],
        )
    else:
        logger.info("FIDDLER start_work: no stroj — skipping Mchtrx(H)")

    return {
        "status": "ok",
        "message": f"Work started (stroj={stroj or 'none'}, wc={wc})",
        "stroj": stroj or None,
        "wc": wc,
    }


async def end_work(
    infor_client: Any,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    item: str = "",
    whse: str = "MAIN",
    qty_complete: float = 0.0,
    qty_scrapped: float = 0.0,
    oper_complete: bool = False,
    kapacity_guid: str = "0",
) -> Dict[str, Any]:
    """End Work — direct DcSfc update (bypasses InsWrapperSp for multi-job safety).

    InsWrapperSp has a multi-job bug: it finds the oldest open TT=3 MJOB record
    for the employee regardless of job, so ending Job B would close Job A's record.
    In InduStream this works because the session proxy maintains job context,
    but our stateless REST API has no session.

    Solution: directly update the correct TT=3 record and create TT=4 via UpdateRequest.
    Then continue with MachineVal + DcSfcMchtrx for machine transaction end.
    """
    emp = _fmt_emp(emp_num)
    seconds = _now_cet_seconds()
    logger.info(
        "FIDDLER end_work: job=%s/%s oper=%s emp=%s qty=%s scrap=%s",
        job, suffix, oper_num, emp_num, qty_complete, qty_scrapped,
    )

    # Step 1: Init DcSfc context (REQUIRED for MachineVal + DcSfcMchtrx below)
    await _init_dcsfc_context(infor_client, emp, job, suffix, whse, "end_work")

    # Step 2: Close TT=3 + create TT=4 (bypasses InsWrapperSp for multi-job safety)
    await _close_dcsfc_direct(
        infor_client, emp, job, suffix, oper_num,
        qty_complete, qty_scrapped, oper_complete,
        seconds, "end_work",
    )

    # Step 3: KapacityUpdate (best-effort)
    try:
        kapacity_params = _build_kapacity_3p(kapacity_guid)
        await _invoke(
            infor_client, _SP_KAPACITY_UPDATE,
            kapacity_params, infobar_index=2, step="end_work.kapacity",
            output_indices=[2],
        )
    except Exception as exc:
        logger.warning("FIDDLER end_work KapacityUpdate skipped: %s", exc)

    # Step 4: MachineVal (TT=J) — validate machine end (different SP than start!)
    # No InfoBar check (-1): output positions [7-10] contain data values, not messages
    machine_val_params = _build_machine_val_oper_num_11p(
        job, suffix, oper_num, emp, "J", item, whse,
    )
    machine_val_resp = await _invoke(
        infor_client, _SP_MACHINE_VAL_OPER_NUM,
        machine_val_params, infobar_index=-1, step="end_work.machine_val",
        output_indices=[7, 8, 9, 10],
    )
    # Output mapping (verified from Fiddler dump data[41]/[51]):
    #   p07 = emp echo ("     20")
    #   p08 = stroj (machine ID)
    #   p09 = wc (work center)
    #   p10 = resid/error message
    mv_outputs = _extract_outputs(machine_val_resp, {
        "p7": 7, "stroj": 8, "wc": 9, "resid": 10,
    })
    logger.info(
        "FIDDLER end_work machine_val outputs: p7=%s stroj=%s wc=%s resid=%s",
        mv_outputs.get("p7"), mv_outputs.get("stroj"),
        mv_outputs.get("wc"), mv_outputs.get("resid"),
    )

    # Step 5: DcSfcMchtrx (TT="J" letter) — end machine transaction (only if stroj exists)
    mv_stroj = mv_outputs.get("stroj", "")
    if mv_stroj:
        mchtrx_end_params = _build_update_dc_sfc_mchtrx_22p(
            emp, "1", "J", job, suffix, oper_num,
            item, whse, qty_complete, qty_scrapped, oper_complete,
        )
        await _invoke(
            infor_client, _SP_UPDATE_DC_SFC_MCHTRX,
            mchtrx_end_params, infobar_index=21, step="end_work.dc_sfc_mchtrx",
            output_indices=[21],
        )
    else:
        logger.info("FIDDLER end_work: no stroj — skipping DcSfcMchtrx")

    return {
        "status": "ok",
        "message": "Work ended (hours calculated by Infor from START/END pairing)",
    }


async def start_setup(
    infor_client: Any,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
) -> Dict[str, Any]:
    """Start Setup — Wrapper(TT=1) only, no machine transaction."""
    emp = _fmt_emp(emp_num)
    logger.info(
        "FIDDLER start_setup: job=%s/%s oper=%s emp=%s",
        job, suffix, oper_num, emp_num,
    )

    # Init DcSfc context (REQUIRED before WrapperSp)
    await _init_dcsfc_context(infor_client, emp, job, suffix, "MAIN", "start_setup")

    # WrapperSp (TT=1) — no machine transaction for setup
    wrapper_params = _build_wrapper_32p(emp, "1", "1", job, suffix, oper_num)
    await _invoke(
        infor_client, _SP_WRAPPER,
        wrapper_params, infobar_index=24, step="start_setup.wrapper",
        output_indices=[24],
    )
    # Fix MJOB start_time (REST API bug: stale timestamp) — TT=1 for setup
    await _fix_dcsfc_start(infor_client, job, suffix, oper_num, trans_type=1, step="start_setup")

    return {
        "status": "ok",
        "message": "Setup started",
    }


async def end_setup(
    infor_client: Any,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    item: str = "",
    whse: str = "MAIN",
    kapacity_guid: str = "0",
) -> Dict[str, Any]:
    """End Setup — WrapperSp(TT=2) → then full start_work() flow.

    HAR verified: setup end uses WrapperSp (same as start), NOT InsWrapperDcsfcUpdateSp!
    HAR Entries 91(TT=1) and 103(TT=2) both use WrapperSp with 25 params (P0-P24).
    After ending setup, automatically starts production (work).
    """
    emp = _fmt_emp(emp_num)
    logger.info(
        "FIDDLER end_setup: job=%s/%s oper=%s emp=%s",
        job, suffix, oper_num, emp_num,
    )

    # Step 1: Init DcSfc context (REQUIRED before WrapperSp)
    await _init_dcsfc_context(infor_client, emp, job, suffix, whse, "end_setup")

    # Step 2: WrapperSp (TT=2) — end setup
    # HAR Entry 103: same SP as start_setup, just TT=2
    wrapper_params = _build_wrapper_32p(emp, "1", "2", job, suffix, oper_num)
    await _invoke(
        infor_client, _SP_WRAPPER,
        wrapper_params, infobar_index=24, step="end_setup.wrapper",
        output_indices=[24],
    )
    # Fix MJOB end_time (REST API bug: stale timestamp) — TT=1/TT=2 for setup
    await _fix_dcsfc_end(infor_client, job, suffix, oper_num, tt_start=1, tt_end=2, step="end_setup")

    # Step 3: Auto-start work (full start_work flow — includes its own init_dcsfc_context)
    logger.info("FIDDLER end_setup: auto-starting work...")
    work_result = await start_work(
        infor_client, emp_num, job, suffix, oper_num, item, whse, kapacity_guid,
    )

    return {
        "status": "ok",
        "message": f"Setup ended, work auto-started (stroj={work_result.get('stroj')}, wc={work_result.get('wc')})",
        "stroj": work_result.get("stroj"),
        "wc": work_result.get("wc"),
    }
