"""TSD Mongoose — work reporting via stateful IPS session (pure Mongoose).

Uses MongooseSession for ALL operations — no REST API involvement.
Replicates the exact InduStream TSD flow as captured in 2.har.

Flow (from HAR trace 2.har, verified against InduStream):
  start_setup: EmpDcSfc → Job → OperNum(1) → MultiJob → Wrapper(TT=1)
  end_setup:   EmpDcSfc → Job → OperNum(2) → MultiJob → Wrapper(TT=2) → auto start_work()
  start_work:  EmpDcSfc → Job → OperNum(3) → MultiJob → AvailQty → NormH →
               OperMachine(H) → Wrapper(TT=3) → Kapacity → Mchtrx(H)
  end_work:    EmpDcSfc → InitParms×2 → Job → OperNum(4) → AvailQty → NormH →
               OperMachine(J) → EmpMchtrx → MultiJob → InsWrapper(TT=4) →
               Kapacity → MachineVal(J) → DcSfcMchtrx(J)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.services.mongoose_session import MongooseSession, MongooseSessionError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IDO + SP constants (HAR-verified names)
# ---------------------------------------------------------------------------
_IDO = "IteCzTsdStd"

# Init SPs (called before every action to set session context)
_SP_VALIDATE_EMP_DCSFC = "IteCzTsdValidateEmpNumDcSfcSp"
_SP_INIT_PARMS = "IteCzTsdInitParmsSp"
_SP_VALIDATE_JOB = "IteCzTsdValidateJobSp"
_SP_VALIDATE_OPER_NUM = "IteCzTsdValidateOperNumSp"
_SP_VALIDATE_MULTI_JOB = "IteCzTsdValidateMultiJobDcSfcSp"

# Qty + norm validation (HAR: called before WrapperSp/InsWrapperSp)
_SP_JOB_AVAILABLE_QTY = "IteCzTsdJobAvailableQtySp"
_SP_NORM_H = "IteCzTsdNormHSp"

# Machine validation SPs
_SP_VALIDATE_OPER_MACHINE = "IteCzTsdValidateOperNumMachineSp"
_SP_VALIDATE_EMP_MCHTRX = "IteCzTsdValidateEmpNumMchtrxSp"
_SP_MACHINE_VAL = "IteCzTsdMachineValOperNumSp"

# Action SPs
_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"
_SP_KAPACITY = "IteCzTsdKapacityUpdateSp"
_SP_MCHTRX = "IteCzTsdUpdateMchtrxSp"
_SP_INS_WRAPPER = "IteCzInsWrapperDcsfcUpdateSp"
_SP_DC_SFC_MCHTRX = "IteCzTsdUpdateDcSfcMchtrxSp"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TsdMongooseError(Exception):
    """Error from TSD Mongoose operations."""
    def __init__(self, sp_name: str, message: str, step: str = "", severity: str = ""):
        self.sp_name = sp_name
        self.step = step
        self.severity = severity
        super().__init__(f"[{step}] {sp_name} (sev={severity}): {message}" if step else f"{sp_name}: {message}")


# ---------------------------------------------------------------------------
# Parameter helpers
# ---------------------------------------------------------------------------

def _p(name: str, value: Any = None, is_output: bool = False) -> Dict[str, Any]:
    """Build a single Param dict for Mongoose invoke_method."""
    d: Dict[str, Any] = {"ParamName": name}
    if is_output:
        d["IsOutput"] = True
    if value is not None:
        d["Value"] = value
    return d


def _fmt_emp(num: str) -> str:
    """Format employee number: 7 chars, right-aligned with leading spaces."""
    return num.strip().rjust(7)


def _fmt_qty(value: float) -> str:
    return f"{value:.2f}"


def _flag(value: bool) -> str:
    return "1" if value else "0"


def _now_cet_datetime() -> str:
    """Current CET datetime formatted for Infor SP vDatumTransakce / @TransDate.

    Format: "YYYY-MM-DD HH:MM:SS" — matches workshop_service._format_infor_datetime.
    Mongoose binary protocol doesn't trigger getdate() in SPs like REST does,
    so we must pass the transaction datetime explicitly.
    """
    cet = timezone(timedelta(hours=1))
    now = datetime.now(cet)
    return now.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Low-level invoke with error checking
# ---------------------------------------------------------------------------

async def _invoke(
    session: MongooseSession,
    sp_name: str,
    params: List[Dict[str, Any]],
    infobar_param: Optional[str] = None,
    step: str = "",
    warn_only: bool = False,
) -> Dict[str, Any]:
    """Call an SP, check severity, optionally check infobar."""
    logger.info("MONGOOSE SP [%s]: %s (%d params)", step, sp_name, len(params))

    resp = await session.invoke_method(_IDO, sp_name, params)

    severity = str(resp.get("Severity", "0"))
    if severity not in ("0",):
        error_msg = ""
        for p in resp.get("Params", []):
            if p.get("IsOutput") and p.get("Value"):
                error_msg = str(p["Value"])
                break
        if warn_only:
            logger.warning("MONGOOSE SP %s sev=%s (warn_only): %s [%s]", sp_name, severity, error_msg, step)
        else:
            logger.error("MONGOOSE SP %s FAILED sev=%s: %s [%s]", sp_name, severity, error_msg, step)
            raise TsdMongooseError(sp_name, error_msg or f"Severity={severity}", step, severity)

    # Check InfoBar for error messages
    if infobar_param and not warn_only:
        for p in resp.get("Params", []):
            if p.get("ParamName", "").lower() == infobar_param.lower() and p.get("Value"):
                infobar = str(p["Value"]).strip()
                if infobar and "spěšné" not in infobar.lower() and "successful" not in infobar.lower():
                    logger.error("MONGOOSE SP %s InfoBar error: %s [%s]", sp_name, infobar, step)
                    raise TsdMongooseError(sp_name, infobar, step, severity)
                break

    logger.info("MONGOOSE SP %s OK [%s]", sp_name, step)
    return resp


def _get_param_value(resp: Dict[str, Any], param_name: str) -> str:
    """Extract a named output parameter value from SP response."""
    for p in resp.get("Params", []):
        if p.get("ParamName", "").lower() == param_name.lower():
            return str(p.get("Value", "") or "").strip()
    return ""


# ---------------------------------------------------------------------------
# Init sub-steps (shared building blocks)
# ---------------------------------------------------------------------------

async def _step_validate_emp(
    session: MongooseSession, emp: str, step: str,
) -> Dict[str, str]:
    """ValidateEmpNumDcSfcSp (7p) → returns emp context dict.

    HAR: P0=emp (input), P1-P6 are outputs.
    P1=seq/count, P2=has_running, P3=running_job, P4=running_suffix, P5=running_oper.
    """
    resp = await _invoke(session, _SP_VALIDATE_EMP_DCSFC, [
        _p("P0", emp),
        _p("P1", is_output=True),
        _p("P2", "", is_output=True),
        _p("P3", is_output=True),
        _p("P4", is_output=True),
        _p("P5", is_output=True),
        _p("P6", is_output=True),
    ], step=f"{step}.emp_dcsfc")

    ctx = {
        "seq": _get_param_value(resp, "p01"),
        "has_running": _get_param_value(resp, "p02"),
        "running_job": _get_param_value(resp, "p03"),
        "running_suffix": _get_param_value(resp, "p04"),
        "running_oper": _get_param_value(resp, "p05"),
    }
    logger.info(
        "MONGOOSE emp context: seq=%s has_running=%s running=%s/%s/%s [%s]",
        ctx["seq"], ctx["has_running"], ctx["running_job"],
        ctx["running_suffix"], ctx["running_oper"], step,
    )
    return ctx


async def _step_init_parms(session: MongooseSession, step: str) -> None:
    """InitParmsSp × 2 — only needed for end_work (Report screen in InduStream)."""
    await _invoke(session, _SP_INIT_PARMS, [
        _p("P0", "00000"),
        _p("P1", "KontrolaPrijAPresunKusuNaOper"),
        _p("P2", "", is_output=True),
        _p("P3", "1"),
        _p("P4", "Nothing"),
    ], step=f"{step}.init_parms_1")

    await _invoke(session, _SP_INIT_PARMS, [
        _p("P0", "00000"),
        _p("P1", "VydejDoNadrizeneho"),
        _p("P2", "0", is_output=True),
        _p("P3", "0"),
        _p("P4", ""),
    ], step=f"{step}.init_parms_2")


async def _step_validate_job(
    session: MongooseSession, job: str, suffix: str, whse: str, step: str,
) -> None:
    """ValidateJobSp (8p) — sets CURRENT JOB in session context."""
    await _invoke(session, _SP_VALIDATE_JOB, [
        _p("P0", f"{job}-{suffix}", is_output=True),
        _p("P1", is_output=True),
        _p("P2", is_output=True),
        _p("P3", is_output=True),
        _p("P4", whse, is_output=True),
        _p("P5", is_output=True),
        _p("P6", ""),
        _p("P7", is_output=True),
    ], step=f"{step}.validate_job", warn_only=True)


async def _step_validate_oper_num(
    session: MongooseSession,
    emp: str, job: str, suffix: str, oper_num: str,
    step_type: str, item: str, whse: str,
    emp_ctx: Dict[str, str],
    step: str,
) -> None:
    """ValidateOperNumSp (22p) — sets operation + step type context in session.

    step_type: "1"=setup-start, "2"=setup-end, "3"=work-start, "4"=work-end.
    P7-P12 carry running-job context from ValidateEmpNumDcSfcSp.
    """
    is_end_work = step_type == "4"

    # P7-P12: running job context
    if is_end_work and emp_ctx.get("running_job"):
        p7 = emp_ctx.get("has_running", "0")
        p8 = emp_ctx.get("running_job", "")
        p9 = emp_ctx.get("running_suffix", "0")
        p10 = emp_ctx.get("running_oper", "0")
        p11 = emp_ctx.get("seq", "0")
        p12 = "1"  # multi-job flag
    else:
        p7 = "0"
        p8 = ""
        p9 = "0"
        p10 = "0"
        p11 = emp_ctx.get("seq", "0")
        p12 = "0"

    params = [
        _p("P0", emp),
        _p("P1", job),
        _p("P2", suffix),
        _p("P3", oper_num),
        _p("P4", step_type),
        _p("P5", item),
        _p("P6", whse),
        _p("P7", p7),
        _p("P8", p8),
        _p("P9", p9),
        _p("P10", p10),
        _p("P11", p11),
        _p("P12", p12),
    ]

    # P13-P19: empty inputs for start, outputs for end_work
    for i in range(13, 20):
        if is_end_work:
            params.append(_p(f"P{i}", is_output=True))
        else:
            params.append(_p(f"P{i}", ""))

    # P20-P21: always outputs
    params.append(_p("P20", is_output=True))
    params.append(_p("P21", is_output=True))

    await _invoke(session, _SP_VALIDATE_OPER_NUM, params,
                  step=f"{step}.validate_oper_num", warn_only=True)


async def _step_validate_multi_job(
    session: MongooseSession, emp: str, step: str,
) -> int:
    """ValidateMultiJobDcSfcSp (3p) — set multi-job mode in session.

    Always uses MJOB mode (P1=1 input) to allow concurrent jobs.
    Returns 1 always (MJOB mode).
    """
    await _invoke(session, _SP_VALIDATE_MULTI_JOB, [
        _p("P0", emp),
        _p("P1", "1", is_output=True),  # input=1 to force MJOB mode
        _p("P2", is_output=True),
    ], step=f"{step}.validate_multi_job", warn_only=True)

    logger.info("MONGOOSE mjob_seq=1 (forced MJOB) [%s]", step)
    return 1


async def _step_job_available_qty(
    session: MongooseSession,
    job: str, suffix: str, oper_num: str,
    is_end_work: bool,
    step: str,
) -> None:
    """IteCzTsdJobAvailableQtySp (15p) — check available qty for operation.

    HAR: Called in both start_work and end_work, before WrapperSp/InsWrapperSp.
    Difference: start_work passes P4/P5/P6 as empty, end_work passes them as 0.
    """
    if is_end_work:
        params = [
            _p("P0", job),
            _p("P1", suffix),
            _p("P2", int(oper_num)),
            _p("P3", 0),
            _p("P4", 0),
            _p("P5", 0),
            _p("P6", 0),
        ]
    else:
        params = [
            _p("P0", job),
            _p("P1", suffix),
            _p("P2", oper_num),
            _p("P3", 0),
            _p("P4"),
            _p("P5"),
            _p("P6"),
        ]

    params.extend([
        _p("P7", is_output=True),
        _p("P8", is_output=True),
        _p("P9", is_output=True),
        _p("P10", is_output=True),
        _p("P11", is_output=True),
        _p("P12", is_output=True),
        _p("P13", ""),
        _p("P14", is_output=True),
    ])

    await _invoke(session, _SP_JOB_AVAILABLE_QTY, params,
                  step=f"{step}.avail_qty", warn_only=True)


async def _step_norm_h(
    session: MongooseSession,
    job: str, suffix: str, oper_num: str,
    is_end_work: bool,
    step: str,
) -> None:
    """IteCzTsdNormHSp (8p) — norm hours check.

    HAR: Called in both start_work and end_work, before WrapperSp/InsWrapperSp.
    Difference: start_work passes P3/P4/P5 as empty strings, end_work marks them as IsOutput.
    """
    params = [
        _p("P0", job),
        _p("P1", suffix),
        _p("P2", int(oper_num) if is_end_work else oper_num),
    ]

    if is_end_work:
        params.extend([
            _p("P3", is_output=True),
            _p("P4", is_output=True),
            _p("P5", is_output=True),
        ])
    else:
        params.extend([
            _p("P3", ""),
            _p("P4", ""),
            _p("P5", ""),
        ])

    params.extend([
        _p("P6", is_output=True),
        _p("P7", is_output=True),
    ])

    await _invoke(session, _SP_NORM_H, params,
                  step=f"{step}.norm_h", warn_only=True)


async def _step_validate_oper_machine(
    session: MongooseSession,
    job: str, suffix: str, oper_num: str, emp: str,
    mode: str, item: str, whse: str,
    step: str,
) -> Dict[str, str]:
    """ValidateOperNumMachineSp (11p) — resolve stroj + wc.

    mode='H' for start (hlásit), 'J' for end (konec).
    MUST be called to set machine context in session.
    """
    resp = await _invoke(session, _SP_VALIDATE_OPER_MACHINE, [
        _p("P0", job),
        _p("P1", suffix),
        _p("P2", oper_num),
        _p("P3", emp),
        _p("P4", mode),
        _p("P5", item),
        _p("P6", whse),
        _p("P7", is_output=True),   # emp echo
        _p("P8", is_output=True),   # stroj
        _p("P9", is_output=True),   # wc
        _p("P10", is_output=True),  # warning/resid
    ], step=f"{step}.oper_machine_{mode}", warn_only=True)

    stroj = _get_param_value(resp, "p08")
    wc = _get_param_value(resp, "p09")
    logger.info("MONGOOSE machine resolved: stroj=%s wc=%s mode=%s [%s]", stroj, wc, mode, step)
    return {"stroj": stroj, "wc": wc}


async def _step_validate_emp_mchtrx(
    session: MongooseSession,
    wc: str, emp: str, stroj: str,
    step: str,
) -> None:
    """ValidateEmpNumMchtrxSp (5p) — validate employee for machine transaction."""
    await _invoke(session, _SP_VALIDATE_EMP_MCHTRX, [
        _p("P0", wc),
        _p("P1", emp),
        _p("P2", stroj),
        _p("P3", is_output=True),   # mch_type
        _p("P4", is_output=True),   # error_msg
    ], step=f"{step}.emp_mchtrx", warn_only=True)


# ---------------------------------------------------------------------------
# start_work: EmpDcSfc → Job → OperNum(3) → MultiJob → AvailQty → NormH →
#             OperMachine(H) → Wrapper(TT=3) → Kapacity → Mchtrx(H)
# ---------------------------------------------------------------------------

async def start_work(
    session: MongooseSession,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    item: str = "",
    whse: str = "MAIN",
    kapacity_guid: str = "0",
) -> Dict[str, Any]:
    """Start Work — pure Mongoose, exact HAR 2.har flow."""
    emp = _fmt_emp(emp_num)

    # 1. Validate employee
    emp_ctx = await _step_validate_emp(session, emp, "start_work")

    # 2. Validate job
    await _step_validate_job(session, job, suffix, whse, "start_work")

    # 3. Validate operation (step=3 = work start)
    await _step_validate_oper_num(
        session, emp, job, suffix, oper_num, "3", item, whse, emp_ctx, "start_work",
    )

    # 4. Validate multi-job → mjob_seq
    mjob_seq = await _step_validate_multi_job(session, emp, "start_work")

    # 5. Job available qty check (HAR: before WrapperSp)
    await _step_job_available_qty(session, job, suffix, oper_num, is_end_work=False, step="start_work")

    # 6. Norm hours check (HAR: before WrapperSp)
    await _step_norm_h(session, job, suffix, oper_num, is_end_work=False, step="start_work")

    # 7. Validate machine (H=start) — resolves stroj + wc
    machine = await _step_validate_oper_machine(
        session, job, suffix, oper_num, emp, "H", item, whse, "start_work",
    )
    stroj = machine["stroj"]
    wc = machine["wc"]

    # 8. WrapperSp (TT=3) — create DcSfc start record
    #    P30 = vDatumTransakce — must pass explicit CET datetime,
    #    Mongoose binary protocol doesn't trigger getdate() like REST does.
    trans_dt = _now_cet_datetime()
    await _invoke(session, _SP_WRAPPER, [
        _p("P0", ""),
        _p("P1", emp),
        _p("P2", mjob_seq),         # multi-job sequence
        _p("P3", "3"),               # TransType = Start Work
        _p("P4", job),
        _p("P5", suffix),
        _p("P6", oper_num),
        _p("P7", ""),                # qty fields empty for start
        _p("P8", ""),
        _p("P9", ""),
        _p("P10", "0"),              # oper complete
        _p("P11", "0"),              # job complete
        _p("P12", "0"),              # issue parent
        _p("P13", ""),               # loc
        _p("P14", ""),               # lot
        _p("P15", ""),               # reason
        _p("P16", ""),               # sernum
        _p("P17", ""),               # wc (SP resolves)
        _p("P18", ""),
        _p("P19", "T"),              # SourceModul (HAR: "T")
        _p("P20"),                   # no value
        _p("P21"),                   # no value
        _p("P22", "0"),
        _p("P23"),                   # no value
        _p("P24", is_output=True),   # InfoBar
        _p("P25", ""),
        _p("P26", ""),
        _p("P27", ""),
        _p("P28", ""),
        _p("P29", ""),
        _p("P30", trans_dt),         # vDatumTransakce — explicit CET datetime
        _p("P31"),                   # no value
    ], infobar_param="p24", step="start_work.wrapper")

    # 9. KapacityUpdate (best-effort)
    try:
        await _invoke(session, _SP_KAPACITY, [
            _p("P0", "J"),
            _p("P1"),
            _p("P2", is_output=True),
        ], step="start_work.kapacity")
    except Exception as exc:
        logger.warning("MONGOOSE start_work kapacity skipped: %s", exc)

    # 10. Mchtrx (TT=H) — start machine transaction
    if stroj:
        await _invoke(session, _SP_MCHTRX, [
            _p("P0", emp),
            _p("P1", "H"),            # Start
            _p("P2", job),
            _p("P3", suffix),
            _p("P4", oper_num),
            _p("P5", wc),
            _p("P6", stroj),
            _p("P7", is_output=True),  # InfoBar
            _p("P8", is_output=True),  # TransNum
        ], infobar_param="p07", step="start_work.mchtrx")
    else:
        logger.info("MONGOOSE start_work: no stroj, skipping Mchtrx(H)")

    logger.info("MONGOOSE start_work OK: stroj=%s wc=%s mjob_seq=%d", stroj, wc, mjob_seq)
    return {"status": "ok", "stroj": stroj or None, "wc": wc}


# ---------------------------------------------------------------------------
# end_work: EmpDcSfc → InitParms×2 → Job → OperNum(4) → AvailQty → NormH →
#           OperMachine(J) → EmpMchtrx → MultiJob → InsWrapper(TT=4) →
#           Kapacity → MachineVal(J) → DcSfcMchtrx(J)
# ---------------------------------------------------------------------------

async def end_work(
    session: MongooseSession,
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
    """End Work — pure Mongoose, exact HAR 2.har flow."""
    emp = _fmt_emp(emp_num)

    # 1. Validate employee (returns running job context for step 4)
    emp_ctx = await _step_validate_emp(session, emp, "end_work")

    # 2. InitParmsSp × 2 (only for end_work — Report screen in InduStream)
    await _step_init_parms(session, "end_work")

    # 3. Validate job
    await _step_validate_job(session, job, suffix, whse, "end_work")

    # 4. Validate operation (step=4 = work end, with running job context)
    await _step_validate_oper_num(
        session, emp, job, suffix, oper_num, "4", item, whse, emp_ctx, "end_work",
    )

    # 5. Job available qty check (HAR: before InsWrapperSp)
    await _step_job_available_qty(session, job, suffix, oper_num, is_end_work=True, step="end_work")

    # 6. Norm hours check (HAR: before InsWrapperSp, end variant with outputs)
    await _step_norm_h(session, job, suffix, oper_num, is_end_work=True, step="end_work")

    # 7. Validate machine for end (J) — resolves stroj + wc, sets machine context
    machine = await _step_validate_oper_machine(
        session, job, suffix, oper_num, emp, "J", item, whse, "end_work",
    )
    stroj = machine["stroj"]
    wc = machine["wc"]

    # 8. Validate employee for machine transaction
    if stroj and wc:
        await _step_validate_emp_mchtrx(session, wc, emp, stroj, "end_work")

    # 9. Validate multi-job → mjob_seq (comes AFTER machine validation in HAR)
    mjob_seq = await _step_validate_multi_job(session, emp, "end_work")

    # 10. InsWrapperSp (TT=4) — end work record
    #     29 params (P0-P28) matching industream_tsd_service._build_ins_wrapper_29p.
    #     P27 = @TransDate, P28 = @DcsfcTransNum (output → returns TransNum for REST fix).
    trans_dt = _now_cet_datetime()
    ins_resp = await _invoke(session, _SP_INS_WRAPPER, [
        _p("P0", "1"),
        _p("P1", ""),
        _p("P2", emp),
        _p("P3", mjob_seq),
        _p("P4", "4"),
        _p("P5", job),
        _p("P6", suffix),
        _p("P7", int(oper_num)),
        _p("P8", float(qty_complete)),
        _p("P9", float(qty_scrapped)),
        _p("P10", float(qty_complete)),
        _p("P11", 0),
        _p("P12"),
        _p("P13", 0),
        _p("P14"),
        _p("P15"),
        _p("P16"),
        _p("P17", "0"),
        _p("P18"),
        _p("P19", ""),
        _p("P20", ""),
        _p("P21", "T"),
        _p("P22"),
        _p("P23"),
        _p("P24", "0"),
        _p("P25"),
        _p("P26", "", is_output=True),       # @Infobar
        _p("P27", trans_dt),                  # @TransDate
        _p("P28", "", is_output=True),        # @DcsfcTransNum — output
    ], infobar_param="p26", step="end_work.ins_wrapper")

    # Extract TransNum from InsWrapperSp output (P28) — needed for REST timestamp fix
    ins_trans_num = _get_param_value(ins_resp, "p28")
    logger.info("MONGOOSE InsWrapperSp TransNum=%s [end_work]", ins_trans_num)

    # 11. KapacityUpdate (best-effort)
    try:
        await _invoke(session, _SP_KAPACITY, [
            _p("P0", "J"),
            _p("P1"),
            _p("P2", is_output=True),
        ], step="end_work.kapacity")
    except Exception as exc:
        logger.warning("MONGOOSE end_work kapacity skipped: %s", exc)

    # 12. MachineValOperNumSp (TT=J) — validate machine end
    machine_val_resp = await _invoke(session, _SP_MACHINE_VAL, [
        _p("P0", job),
        _p("P1", suffix),
        _p("P2", oper_num),
        _p("P3", emp),
        _p("P4", "J"),           # End machine
        _p("P5", item),
        _p("P6", whse),
        _p("P7", is_output=True),   # emp echo
        _p("P8", is_output=True),   # stroj
        _p("P9", is_output=True),   # wc
        _p("P10", is_output=True),  # resid
    ], step="end_work.machine_val", warn_only=True)

    mv_stroj = _get_param_value(machine_val_resp, "p08")

    # 13. DcSfcMchtrx (TT=J) — end machine transaction
    if mv_stroj:
        await _invoke(session, _SP_DC_SFC_MCHTRX, [
            _p("P0", ""),
            _p("P1", emp),
            _p("P2", mjob_seq),                  # multi-job sequence
            _p("P3", "J"),                         # End Machine
            _p("P4", job),
            _p("P5", suffix),
            _p("P6", int(oper_num)),
            _p("P7", item),                        # item
            _p("P8", whse),                        # whse ("MAIN")
            _p("P9", float(qty_complete)),
            _p("P10", float(qty_scrapped)),
            _p("P11", float(qty_complete)),         # qty moved
            _p("P12", 0),                          # oper complete
            _p("P13"),                              # loc
            _p("P14", 0),                           # lot
            _p("P15"),                              # reason
            _p("P16"),                              # sernum
            _p("P17"),
            _p("P18"),
            _p("P19", ""),
            _p("P20", 1),                           # ukoncit_stroj flag
            _p("P21", is_output=True),              # InfoBar
        ], infobar_param="p21", step="end_work.dc_sfc_mchtrx")
    else:
        logger.info("MONGOOSE end_work: no stroj from MachineVal, skipping DcSfcMchtrx(J)")

    logger.info("MONGOOSE end_work OK: mjob_seq=%d trans_num=%s", mjob_seq, ins_trans_num)
    return {
        "status": "ok",
        "message": "Work ended",
        "trans_num": ins_trans_num,  # For REST timestamp fix
    }


# ---------------------------------------------------------------------------
# start_setup: EmpDcSfc → Job → OperNum(1) → MultiJob → Wrapper(TT=1)
# ---------------------------------------------------------------------------

async def start_setup(
    session: MongooseSession,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    whse: str = "MAIN",
) -> Dict[str, Any]:
    """Start Setup — WrapperSp(TT=1), no machine transaction."""
    emp = _fmt_emp(emp_num)

    # 1. Validate employee
    emp_ctx = await _step_validate_emp(session, emp, "start_setup")

    # 2. Validate job
    await _step_validate_job(session, job, suffix, whse, "start_setup")

    # 3. Validate operation (step=1 = setup start)
    await _step_validate_oper_num(
        session, emp, job, suffix, oper_num, "1", "", whse, emp_ctx, "start_setup",
    )

    # 4. Validate multi-job
    mjob_seq = await _step_validate_multi_job(session, emp, "start_setup")

    # 5. WrapperSp (TT=1)
    await _invoke(session, _SP_WRAPPER, [
        _p("P0", ""),
        _p("P1", emp),
        _p("P2", mjob_seq),
        _p("P3", "1"),               # TransType = Start Setup
        _p("P4", job),
        _p("P5", suffix),
        _p("P6", oper_num),
        _p("P7", ""),
        _p("P8", ""),
        _p("P9", ""),
        _p("P10", "0"),
        _p("P11", "0"),
        _p("P12", "0"),
        _p("P13", ""),
        _p("P14", ""),
        _p("P15", ""),
        _p("P16", ""),
        _p("P17", ""),
        _p("P18", ""),
        _p("P19", "T"),              # SourceModul
        _p("P20"),
        _p("P21"),
        _p("P22", "0"),
        _p("P23"),
        _p("P24", is_output=True),   # InfoBar
    ], infobar_param="p24", step="start_setup.wrapper")

    return {"status": "ok", "message": "Setup started"}


# ---------------------------------------------------------------------------
# end_setup: EmpDcSfc → Job → OperNum(2) → MultiJob → Wrapper(TT=2) →
#            auto start_work()
# ---------------------------------------------------------------------------

async def end_setup(
    session: MongooseSession,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    item: str = "",
    whse: str = "MAIN",
    kapacity_guid: str = "0",
) -> Dict[str, Any]:
    """End Setup — WrapperSp(TT=2), then auto-start work."""
    emp = _fmt_emp(emp_num)

    # 1. Validate employee
    emp_ctx = await _step_validate_emp(session, emp, "end_setup")

    # 2. Validate job
    await _step_validate_job(session, job, suffix, whse, "end_setup")

    # 3. Validate operation (step=2 = setup end)
    await _step_validate_oper_num(
        session, emp, job, suffix, oper_num, "2", item, whse, emp_ctx, "end_setup",
    )

    # 4. Validate multi-job
    mjob_seq = await _step_validate_multi_job(session, emp, "end_setup")

    # 5. WrapperSp (TT=2)
    await _invoke(session, _SP_WRAPPER, [
        _p("P0", ""),
        _p("P1", emp),
        _p("P2", mjob_seq),
        _p("P3", "2"),               # TransType = End Setup
        _p("P4", job),
        _p("P5", suffix),
        _p("P6", oper_num),
        _p("P7", ""),
        _p("P8", ""),
        _p("P9", ""),
        _p("P10", "0"),
        _p("P11", "0"),
        _p("P12", "0"),
        _p("P13", ""),
        _p("P14", ""),
        _p("P15", ""),
        _p("P16", ""),
        _p("P17", ""),
        _p("P18", ""),
        _p("P19", "T"),
        _p("P20"),
        _p("P21"),
        _p("P22", "0"),
        _p("P23"),
        _p("P24", is_output=True),
    ], infobar_param="p24", step="end_setup.wrapper")

    # Auto-start work (HAR verified: end_setup chains into full start_work)
    logger.info("MONGOOSE end_setup: auto-starting work...")
    work_result = await start_work(
        session, emp_num, job, suffix, oper_num, item, whse, kapacity_guid,
    )

    return {
        "status": "ok",
        "message": f"Setup ended, work auto-started (stroj={work_result.get('stroj')})",
        "stroj": work_result.get("stroj"),
        "wc": work_result.get("wc"),
    }
