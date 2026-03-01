"""GESTIMA - Workshop Service

Dílenská aplikace napojená na Infor CloudSuite Industrial.

Tento modul implementuje RE flow z InduStream:
- fronta práce z IteCzTsdJbrDetails (rozvrh operací)
- kompatibilita: při detail-only JBR schema se fronta bere ze SLJobRoutes
- start/setup přes IteCzTsdUpdateDcSfcWrapperSp + IteCzTsdUpdateMchtrxSp
- stop přes IteCzTsdUpdateDcSfcWrapperSp + IteCzTsdUpdateMchtrxSp (fallback DCSFC_MCHTRX)
- manuální odvody přes IteCzTsdUpdateDcSfc34Sp (20 params)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import safe_commit, set_audit
from app.models.enums import WorkshopTxStatus, WorkshopTransType
from app.models.user import User
from app.models.workshop_transaction import WorkshopTransaction, WorkshopTransactionCreate

logger = logging.getLogger(__name__)

# Infor write IDO/SP
_WRITE_IDO = "IteCzTsdStd"
_WRITE_SP_SFC34 = "IteCzTsdUpdateDcSfc34Sp"
_WRITE_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"
_WRITE_SP_MCHTRX = "IteCzTsdUpdateMchtrxSp"
_WRITE_SP_DCSFC_MCHTRX = "IteCzTsdUpdateDcSfcMchtrxSp"
_WRITE_SP_INS_WRAPPER_DCSFC_UPDATE = "IteCzInsWrapperDcsfcUpdateSp"
_WRITE_SP_KAPACITY_UPDATE = "IteCzTsdKapacityUpdateSp"
_WRITE_SP_INIT_PARMS = "IteCzTsdInitParmsSp"
_WRITE_SP_VALIDATE_EMP_MCHTRX = "IteCzTsdValidateEmpNumMchtrxSp"
_WRITE_SP_VALIDATE_MULTI_JOB = "IteCzTsdValidateMultiJobDcSfcSp"
_WRITE_SP_VALIDATE_OPER_MACHINE = "IteCzTsdValidateOperNumMachineSp"
_WRITE_SP_CLM_GET_JOB_MATERIAL = "IteCzTsdCLMGetJobMaterialSp"
_WRITE_SP_CONTROL_BF_JOBMATL_ITEM = "IteCzTsdControlBFJobmatlItemSp"
_WRITE_SP_VALIDATE_ITEM_DCJMC = "IteCzTsdValidateItemDcJmcSp"
_WRITE_SP_VALIDATE_QTY_DCJMC = "IteCzTsdValidateQtyDcJmcSp"
_WRITE_SP_VALIDATE_LOT_DCJMC = "IteCzTsdValidateLotDcJmcSp"
_WRITE_SP_PROCESS_JOB_MATL_TRANS = "IteCzTsdProcessJobMatlTransDcSp"
_WRITE_SP_INS_VALID_VYDEJ_MAT = "IteCzInsValidVydejMatNaVpLotOrScSp"
_WRITE_SP_UPDATE_DCJMC = "IteCzTsdUpdateDcJmcSp"
_WORKSHOP_DEFAULT_WHSE = "MAIN"
_WORKSHOP_DEFAULT_LOC = "PRIJEM"
_COOP_WC_PREFIX = "KOO"
_WORKSHOP_TIMEZONE = ZoneInfo("Europe/Prague")
_WORKSHOP_DEFAULT_MULTI_JOB_FLAG = (
    "1"
    if (str(os.getenv("WORKSHOP_DEFAULT_MULTI_JOB_FLAG", "1")).strip().lower()
        in {"1", "true", "t", "yes", "y"})
    else "0"
)

_WRAPPER_TYPES = {"setup_start", "setup_end", "start", "stop"}
_QTY_EPSILON = 1e-6
_SAW_WC_PREFIXES = ("PS", "PILA", "SAW")
_DONE_STATE_MARKERS = ("DOKON", "COMPLET", "CLOSED", "FINISH", "DONE", "UZAVR")
_IN_PROGRESS_STATE_TOKENS = ("B", "RUN", "RUNNING", "PRAC", "WORK")


class _NonRecoverablePostError(RuntimeError):
    """Business-level write failure that must not be auto-recovered to POSTED."""


# Queue properties from RE documentation (JbrDetails), with fallbacks for older aliases.
_QUEUE_PROP_SETS: List[List[str]] = [
    [
        "colJob",
        "colSuffix",
        "colOper",
        "colWc",
        "colDil",
        "colNazev",
        "colVpMnoz",
        "colKusy",
        "colOpDatumSt",
        "colOpDatumSp",
        "colState",
        "colStateAsd",
        "colLzeDokoncit",
        "colPlanFlag",
    ],
    ["colJob", "colSuffix", "colOper", "colWc", "colOpDatumSt", "colOpDatumSp"],
    ["colJob", "colJobSuffix", "colOper", "colWc", "colOpDatumSt", "colOpDatumSp"],
    ["vJobSuffixOperNum", "colWc", "colOpDatumSt", "colOpDatumSp", "colKusy", "colVpMnoz"],
    ["JobSuffixOperNum", "Wc", "OpDatumSt", "OpDatumSp", "QtyComplete", "JobQtyReleased"],
    [
        "Job",
        "Suffix",
        "OperNum",
        "Wc",
        "Dil",
        "Nazev",
        "VpMnoz",
        "Kusy",
        "OpDatumSt",
        "OpDatumSp",
        "DerZbyva",
        "State",
        "StateAsd",
        "LzeDokoncit",
        "PlanFlag",
    ],
    [
        "Job",
        "Suffix",
        "OperNum",
        "Wc",
        "DerJobItem",
        "JobDescription",
        "JobQtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "JshSetupHrs",
        "DerRunMchHrs",
        "OpDatumSt",
        "OpDatumSp",
    ],
    ["Job", "Suffix", "OperNum", "Wc", "OpDatumSt", "OpDatumSp"],
]

_JOB_ROUTE_PROPS = [
    "Job",
    "Suffix",
    "Type",
    "Wc",
    "OperNum",
    "DerJobItem",
    "JobDescription",
    "JobStat",
    "JobQtyReleased",
    "QtyComplete",
    "QtyScrapped",
    "JshSetupHrs",
    "DerRunMchHrs",
    "DerStartDate",
    "DerEndDate",
    "JshStartDate",
    "JshEndDate",
]
_JOB_ROUTE_PROP_SETS: List[List[str]] = [
    _JOB_ROUTE_PROPS,
    [
        "Job",
        "Suffix",
        "Type",
        "Wc",
        "OperNum",
        "DerJobItem",
        "JobDescription",
        "JobStat",
        "JobQtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "DerStartDate",
        "DerEndDate",
    ],
    [
        "Job",
        "Suffix",
        "Type",
        "Wc",
        "OperNum",
        "DerJobItem",
        "JobDescription",
        "JobStat",
        "JobQtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "JshStartDate",
        "JshEndDate",
    ],
]

_MATERIAL_PROP_SETS: List[List[str]] = [
    [
        "MaterialBd",
        "DescriptionBd",
        "TotalConsumptionBd",
        "QtyPerPcBd",
        "BatchConsumptionBd",
        "Item",
        "DerItemDescription",
        "MatlQty",
        "QtyIssued",
        "DerQty",
    ],
    ["Item", "DerItemDescription", "TotCons", "Qty", "BatchCons"],
    ["Material", "Desc", "TotCons", "Qty", "BatchCons"],
]
_SLJOBMATLS_UOM_PROP_SETS: List[List[str]] = [
    [
        "Job",
        "Suffix",
        "OperNum",
        "Item",
        "UM",
        "MatlQtyConv",
        "DerMatlTransQty",
        "DerQtyToPick",
        "DerMatlQtyRequired",
        "DerQtyIssuedConv",
        "QtyIssued",
    ],
    [
        "ItmJob",
        "ItmSuffix",
        "OperNum",
        "ItmItem",
        "UM",
        "MatlQtyConv",
        "DerMatlTransQty",
        "DerQtyToPick",
        "DerMatlQtyRequired",
        "DerQtyIssuedConv",
        "QtyIssued",
    ],
    [
        "Job",
        "Suffix",
        "OperNum",
        "ItmItem",
        "UM",
        "MatlQtyConv",
        "DerMatlTransQty",
        "DerQtyToPick",
        "DerMatlQtyRequired",
        "DerQtyIssuedConv",
        "QtyIssued",
    ],
]
_SLUMCONVS_PROP_SETS: List[List[str]] = [
    ["Item", "FromUM", "ToUM", "ConvFactor"],
    ["Item", "FromUM", "ToUM"],
]

_ORDER_OVERVIEW_STATUS_DEFAULT = ("O",)
_ORDER_OVERVIEW_MAX_VP_CANDIDATES = 8
_ORDER_OVERVIEW_ACTIVE_JOB_STATUSES = ("R", "S", "F")
_ORDER_OVERVIEW_COITEMS_PROP_SETS: List[List[str]] = [
    [
        "CoNum",
        "CoLine",
        "CoRelease",
        "CustNum",
        "CoCustNum",
        "CoCustSeq",
        "CoType",
        "CoStat",
        "Item",
        "Description",
        "QtyOrdered",
        "QtyShipped",
        "IteRybQtyWip",
        "DueDate",
        "PromiseDate",
        "RybDatumSlibRadZak",
        "RybDatumPotvrRadZak",
        "RybConfirmDate",
        "RybChangeDate",
        "Stat",
        "DerRybStavCNCItem",
        "DerRybStavKPItem",
        "DerRybStavSLItem",
        "DerRybStavTPVPol",
        "CoOrderDate",
        "ReleaseDate",
        "ProjectedDate",
        "ShipDate",
        "RecordDate",
        "CustPo",
    ],
    [
        "CoNum",
        "CoLine",
        "CoRelease",
        "CoCustNum",
        "CoCustSeq",
        "CoType",
        "CoStat",
        "Item",
        "Description",
        "QtyOrdered",
        "QtyShipped",
        "IteRybQtyWip",
        "DueDate",
        "PromiseDate",
        "RybDatumSlibRadZak",
        "RybDatumPotvrRadZak",
        "RybConfirmDate",
        "RybChangeDate",
        "Stat",
        "DerRybStavCNCItem",
        "DerRybStavKPItem",
        "DerRybStavSLItem",
        "DerRybStavTPVPol",
        "CoOrderDate",
        "ReleaseDate",
        "ProjectedDate",
        "ShipDate",
        "RecordDate",
        "CustPo",
    ],
    [
        "CoNum",
        "CoLine",
        "CoRelease",
        "CustNum",
        "CoCustNum",
        "CoCustSeq",
        "CoType",
        "Item",
        "Description",
        "QtyOrdered",
        "QtyShipped",
        "DueDate",
        "PromiseDate",
        "Stat",
        "RecordDate",
    ],
    [
        "CoNum",
        "CoLine",
        "CoRelease",
        "CoCustNum",
        "CoCustSeq",
        "CoType",
        "Item",
        "Description",
        "QtyOrdered",
        "QtyShipped",
        "DueDate",
        "PromiseDate",
        "Stat",
        "RecordDate",
    ],
]
_ORDER_OVERVIEW_JOBS_PROP_SETS: List[List[str]] = [
    [
        "Job",
        "Suffix",
        "Item",
        "Stat",
        "QtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "JschEndDate",
        "DerDueDate",
        "RecordDate",
    ],
    [
        "Job",
        "Suffix",
        "Item",
        "Stat",
        "QtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "JschEndDate",
        "RecordDate",
    ],
]
_ORDER_OVERVIEW_JOBROUTES_PROP_SETS: List[List[str]] = [
    [
        "Job",
        "Suffix",
        "OperNum",
        "Wc",
        "Type",
        "JobStat",
        "JobQtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "DerStartDate",
        "DerEndDate",
        "DerRybStavOper",
        "DerRybStavCNCOper",
        "DerRybStavKPOper",
        "DerRybStavSLOper",
        "Complete",
    ],
    [
        "Job",
        "Suffix",
        "OperNum",
        "Wc",
        "Type",
        "JobStat",
        "JobQtyReleased",
        "QtyComplete",
        "QtyScrapped",
        "DerStartDate",
        "DerEndDate",
        "Complete",
    ],
]
_ORDER_OVERVIEW_CUSTOMERS_PROP_SETS: List[List[str]] = [
    ["CustNum", "CustSeq", "Name", "Country", "CurrCode"],
    ["CustNum", "CustSeq", "Name"],
    ["CustNum", "Name"],
]
_ORDER_OVERVIEW_COS_PROP_SETS: List[List[str]] = [
    ["CoNum", "CustNum", "CustSeq", "RecordDate"],
    ["CoNum", "CustNum", "CustSeq"],
    ["CoNum", "CustNum"],
]


def _as_clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


def _first_value(row: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip().replace("\u00a0", "")
        if not raw:
            return None
        try:
            return round(float(raw.replace(",", ".")), 4)
        except (TypeError, ValueError):
            return None
    return None


def _format_decimal(value: Optional[float]) -> str:
    # Infor quantity fields are commonly represented with 8 decimal digits.
    # STOP payloads can legitimately omit qty fields -> send explicit zero.
    parsed = _parse_float(value)
    return f"{(parsed if parsed is not None else 0.0):.8f}"


def _oper_sort_key(value: Optional[str]) -> tuple[int, int, str]:
    text = (value or "").strip()
    if not text:
        return (2, 0, "")
    try:
        return (0, int(text), text)
    except (TypeError, ValueError):
        return (1, 0, text)


def _same_oper_num(left: Optional[str], right: Optional[str]) -> bool:
    return (left or "").strip() == (right or "").strip()


def _is_saw_wc(wc: Optional[str]) -> bool:
    text = (wc or "").strip().upper()
    if not text:
        return False
    return any(text.startswith(prefix) for prefix in _SAW_WC_PREFIXES)


def _is_coop_wc(wc: Optional[str]) -> bool:
    text = (wc or "").strip().upper()
    if not text:
        return False
    return text.startswith(_COOP_WC_PREFIX)


def _is_first_operation(oper_num: str, route_rows: Sequence[Dict[str, Any]]) -> bool:
    if not route_rows:
        return False
    first_row = min(route_rows, key=lambda row: _oper_sort_key(_as_clean_str(row.get("OperNum"))))
    return _same_oper_num(_as_clean_str(first_row.get("OperNum")), oper_num)


def _trans_type_value(trans_type: Any) -> str:
    return trans_type.value if hasattr(trans_type, "value") else str(trans_type)


def _requires_qty_validation(tx: WorkshopTransaction) -> bool:
    value = _trans_type_value(tx.trans_type)
    return value in {"stop", "qty_complete"}


def _overrun_block_error(remaining_qty: float, requested_qty: float) -> str:
    return (
        "Nelze odvést více kusů než zbývá pro tuto operaci "
        f"(zbývá {remaining_qty:.3f} ks, zadáno {requested_qty:.3f} ks). "
        "Přeodvod je povolen pouze na první pile."
    )


def _operation_done_error(released_qty: float, completed_qty: float, scrapped_qty: float) -> str:
    return (
        "Operace je již dokončena a nelze do ní vykazovat další pohyby "
        f"(VP {released_qty:.3f} ks, hotovo {completed_qty:.3f} ks, zmetky {scrapped_qty:.3f} ks)."
    )


def _bool_to_flag(value: bool) -> str:
    return "1" if value else "0"


def _normalize_multi_job_flag(value: Any) -> str:
    text = (_as_clean_str(value) or "").lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return "1"
    return "0"


def _normalize_bool_flag(value: Any, *, default: str = "0") -> str:
    text = (_as_clean_str(value) or "").strip().lower()
    if not text:
        return "1" if default == "1" else "0"
    if text in {"1", "true", "t", "yes", "y"}:
        return "1"
    if text in {"0", "false", "f", "no", "n"}:
        return "0"
    return "1" if default == "1" else "0"


def _normalize_emp_num(value: Any) -> Optional[str]:
    text = _as_clean_str(value)
    if not text:
        return None
    return text if text.isdigit() else None


def resolve_infor_emp_num(user: Any) -> str:
    for candidate in (
        getattr(user, "infor_emp_num", None),
        getattr(user, "username", None),
    ):
        normalized = _normalize_emp_num(candidate)
        if normalized:
            return normalized
    return "1"


def _format_infor_datetime(value: Optional[datetime]) -> str:
    if not value:
        return ""
    dt = _to_workshop_local_naive(value)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _to_workshop_local_naive(value: datetime) -> datetime:
    dt = value
    if dt.tzinfo is not None:
        dt = dt.astimezone(_WORKSHOP_TIMEZONE).replace(tzinfo=None)
    else:
        # Naive datetime from DB is UTC (frontend sends .toISOString()) — convert to CET.
        dt = dt.replace(tzinfo=timezone.utc).astimezone(_WORKSHOP_TIMEZONE).replace(tzinfo=None)
    return dt


def _sort_key_for_date(value: Optional[str]) -> tuple:
    if not value:
        return (1, "")

    text = value.strip()
    if not text:
        return (1, "")

    # Prefer real datetime sort if parseable, otherwise lexical fallback.
    for candidate in (
        text,
        text.replace("Z", "+00:00"),
        text.replace("T", " "),
    ):
        try:
            parsed = datetime.fromisoformat(candidate)
            return (0, parsed.isoformat())
        except ValueError:
            continue

    return (0, text)


def _sort_direction(sort_dir: str) -> bool:
    return (sort_dir or "").strip().lower() == "desc"


def _sort_key_for_text(value: Any) -> tuple[int, str]:
    text = _as_clean_str(value)
    if not text:
        return (1, "")
    return (0, text.upper())


def _sort_key_for_number(value: Any) -> tuple[int, float]:
    parsed = _parse_float(value)
    if parsed is None:
        return (1, 0.0)
    return (0, parsed)


def _safe_eq_filter(field: str, value: str) -> Optional[str]:
    text = _as_clean_str(value)
    if not text:
        return None
    safe_value = text.replace("'", "''")
    return f"{field} = '{safe_value}'"


def _status_in_filter(field: str, statuses: Sequence[str]) -> Optional[str]:
    cleaned = [(_as_clean_str(status) or "").upper() for status in statuses]
    normalized = [status for status in cleaned if status]
    if not normalized:
        return None
    quoted = ", ".join("'" + status.replace("'", "''") + "'" for status in normalized)
    return f"{field} IN ({quoted})"


def _infor_date_from_iso(date_value: Optional[str], *, end_of_day: bool = False) -> Optional[str]:
    text = (date_value or "").strip()
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None
    if end_of_day:
        return parsed.strftime("%Y%m%d 23:59:59.999")
    return parsed.strftime("%Y%m%d 00:00:00.000")


def _build_date_range_filter(
    field_name: str,
    *,
    date_from: Optional[str],
    date_to: Optional[str],
) -> List[str]:
    clauses: List[str] = []
    from_value = _infor_date_from_iso(date_from, end_of_day=False)
    to_value = _infor_date_from_iso(date_to, end_of_day=True)
    if from_value:
        clauses.append(f"{field_name} >= '{from_value}'")
    if to_value:
        clauses.append(f"{field_name} <= '{to_value}'")
    return clauses


def _normalize_suffix_for_key(value: Any) -> str:
    raw = _as_clean_str(value) or "0"
    try:
        return str(int(raw))
    except ValueError:
        return raw


def _normalize_job_for_key(value: Any) -> Optional[str]:
    text = _as_clean_str(value)
    if not text:
        return None
    return text.replace("\u00a0", " ").strip()


def _job_key(job: Any, suffix: Any) -> Optional[str]:
    normalized_job = _normalize_job_for_key(job)
    if not normalized_job:
        return None
    return f"{normalized_job}|{_normalize_suffix_for_key(suffix)}"


def _status_state_text(row: Dict[str, Any]) -> str:
    return " ".join(
        [
            (_as_clean_str(row.get("DerRybStavOper")) or ""),
            (_as_clean_str(row.get("DerRybStavCNCOper")) or ""),
            (_as_clean_str(row.get("DerRybStavKPOper")) or ""),
            (_as_clean_str(row.get("DerRybStavSLOper")) or ""),
        ]
    ).upper()


def _operation_status(row: Dict[str, Any]) -> str:
    released_qty = _parse_float(row.get("JobQtyReleased")) or 0.0
    completed_qty = _parse_float(row.get("QtyComplete")) or 0.0
    scrapped_qty = _parse_float(row.get("QtyScrapped")) or 0.0
    if _operation_completed_by_qty(released_qty, completed_qty, scrapped_qty):
        return "done"

    complete_flag = (_as_clean_str(row.get("Complete")) or "").strip()
    if complete_flag in {"1", "Y", "T", "True", "true"}:
        return "done"

    state_text = _status_state_text(row)
    if state_text and any(marker in state_text for marker in _DONE_STATE_MARKERS):
        return "done"

    state_tokens = [token for token in re.split(r"[^A-Z0-9]+", state_text) if token]
    if any(token in _IN_PROGRESS_STATE_TOKENS for token in state_tokens):
        return "in_progress"

    return "idle"


def _coitem_sort_key(row: Dict[str, Any]) -> tuple:
    due_value = _as_clean_str(_first_value(row, ("RybDatumSlibRadZak", "PromiseDate", "DueDate")))
    record_value = _as_clean_str(_first_value(row, ("RecordDate", "CoOrderDate", "RybChangeDate")))
    return (
        _sort_key_for_date(due_value),
        _sort_key_for_date(record_value),
        _sort_key_for_text(row.get("CoNum")),
        _sort_key_for_number(row.get("CoLine")),
    )


def sort_queue(
    rows: Sequence[Dict[str, Any]],
    sort_by: str,
    sort_dir: str,
) -> List[Dict[str, Any]]:
    normalized = (sort_by or "OpDatumSt").strip()
    reverse = _sort_direction(sort_dir)

    sorters = {
        "Job": lambda item: _sort_key_for_text(item.get("Job")),
        "OperNum": lambda item: _oper_sort_key(_as_clean_str(item.get("OperNum"))),
        "Wc": lambda item: _sort_key_for_text(item.get("Wc")),
        "DerJobItem": lambda item: _sort_key_for_text(item.get("DerJobItem")),
        "JobDescription": lambda item: _sort_key_for_text(item.get("JobDescription")),
        "QtyComplete": lambda item: _sort_key_for_number(item.get("QtyComplete")),
        "JobQtyReleased": lambda item: _sort_key_for_number(item.get("JobQtyReleased")),
        "OpDatumSp": lambda item: _sort_key_for_date(_as_clean_str(item.get("OpDatumSp"))),
        "OpDatumSt": lambda item: _sort_key_for_date(_as_clean_str(item.get("OpDatumSt"))),
    }
    primary = sorters.get(normalized, sorters["OpDatumSt"])
    return sorted(
        rows,
        key=lambda item: (
            primary(item),
            _sort_key_for_text(item.get("Job")),
            _oper_sort_key(_as_clean_str(item.get("OperNum"))),
        ),
        reverse=reverse,
    )


def _sort_operations(
    rows: Sequence[Dict[str, Any]],
    sort_by: str,
    sort_dir: str,
) -> List[Dict[str, Any]]:
    normalized = (sort_by or "OpDatumSt").strip()
    reverse = _sort_direction(sort_dir)

    sorters = {
        "OperNum": lambda item: _oper_sort_key(_as_clean_str(item.get("OperNum"))),
        "Wc": lambda item: _sort_key_for_text(item.get("Wc")),
        "QtyReleased": lambda item: _sort_key_for_number(item.get("QtyReleased")),
        "QtyComplete": lambda item: _sort_key_for_number(item.get("QtyComplete")),
        "ScrapQty": lambda item: _sort_key_for_number(item.get("ScrapQty")),
        "OpDatumSp": lambda item: _sort_key_for_date(_as_clean_str(item.get("OpDatumSp"))),
        "OpDatumSt": lambda item: _sort_key_for_date(_as_clean_str(item.get("OpDatumSt"))),
    }
    primary = sorters.get(normalized, sorters["OpDatumSt"])
    return sorted(
        rows,
        key=lambda item: (
            primary(item),
            _oper_sort_key(_as_clean_str(item.get("OperNum"))),
        ),
        reverse=reverse,
    )


def _sort_materials(
    rows: Sequence[Dict[str, Any]],
    sort_by: str,
    sort_dir: str,
) -> List[Dict[str, Any]]:
    normalized = (sort_by or "Material").strip()
    reverse = _sort_direction(sort_dir)

    sorters = {
        "Material": lambda item: _sort_key_for_text(item.get("Material")),
        "Desc": lambda item: _sort_key_for_text(item.get("Desc")),
        "TotCons": lambda item: _sort_key_for_number(item.get("TotCons")),
        "Qty": lambda item: _sort_key_for_number(item.get("Qty")),
        "BatchCons": lambda item: _sort_key_for_number(item.get("BatchCons")),
    }
    primary = sorters.get(normalized, sorters["Material"])
    return sorted(
        rows,
        key=lambda item: (
            primary(item),
            _sort_key_for_text(item.get("Material")),
        ),
        reverse=reverse,
    )


def _normalize_suffix(value: Optional[str]) -> str:
    text = (value or "").strip()
    if not text:
        return "0"
    try:
        return str(int(text))
    except ValueError:
        return text


def _operation_completed_by_qty(
    released_qty: float,
    completed_qty: float,
    scrapped_qty: float,
) -> bool:
    if released_qty <= _QTY_EPSILON:
        return False
    return (completed_qty + scrapped_qty) >= (released_qty - _QTY_EPSILON)


def _operation_completed_by_state(row: Dict[str, Any]) -> bool:
    state_text = " ".join(
        [
            (_as_clean_str(row.get("State")) or ""),
            (_as_clean_str(row.get("StateAsd")) or ""),
        ]
    ).upper()
    if not state_text:
        return False
    return any(marker in state_text for marker in _DONE_STATE_MARKERS)


def _is_operation_completed_row(row: Dict[str, Any]) -> bool:
    released_qty = _parse_float(row.get("JobQtyReleased")) or 0.0
    completed_qty = _parse_float(row.get("QtyComplete")) or 0.0
    scrapped_qty = _parse_float(row.get("QtyScrapped")) or 0.0
    return _operation_completed_by_state(row) or _operation_completed_by_qty(
        released_qty,
        completed_qty,
        scrapped_qty,
    )


def _normalize_queue_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    job = _as_clean_str(_first_value(row, ("Job", "JobNum", "colJob")))
    oper_num = _as_clean_str(_first_value(row, ("OperNum", "Oper", "colOper", "colOperNum")))
    suffix = _as_clean_str(
        _first_value(row, ("Suffix", "JobSuffix", "colSuffix", "colJobSuffix", "vSuffix"))
    ) or "0"

    if not job or not oper_num:
        parsed = _parse_job_suffix_oper(
            _first_value(row, ("JobSuffixOperNum", "vJobSuffixOperNum", "colJobSuffixOperNum"))
        )
        if parsed:
            parsed_job, parsed_suffix, parsed_oper = parsed
            if not job:
                job = parsed_job
            if suffix in ("", "0") and parsed_suffix:
                suffix = parsed_suffix
            if not oper_num:
                oper_num = parsed_oper

    if not job or not oper_num:
        return None

    wc = _as_clean_str(_first_value(row, ("Wc", "WC", "colWc")))

    return {
        "Job": job,
        "Suffix": suffix,
        "OperNum": oper_num,
        "Wc": wc,
        "State": _as_clean_str(_first_value(row, ("State", "Status", "colState"))),
        "StateAsd": _as_clean_str(_first_value(row, ("StateAsd", "StatusAsd", "colStateAsd"))),
        "DerJobItem": _as_clean_str(_first_value(row, ("Dil", "DerJobItem", "Item", "colDil", "colJobItem"))),
        "JobDescription": _as_clean_str(
            _first_value(
                row,
                ("Nazev", "JobDescription", "Description", "DerItemDescription", "colNazev", "colJobDescription"),
            )
        ),
        "JobQtyReleased": _parse_float(
            _first_value(row, ("VpMnoz", "JobQtyReleased", "QtyReleased", "colVpMnoz", "colJobQtyReleased"))
        ),
        "QtyComplete": _parse_float(_first_value(row, ("Kusy", "QtyComplete", "JrtQtyComplete", "colKusy"))),
        "QtyScrapped": _parse_float(_first_value(row, ("QtyScrapped", "JrtQtyScrapped", "colQtyScrapped"))),
        "JshSetupHrs": _parse_float(_first_value(row, ("JshSetupHrs", "SetupHrs", "colSetupHrs"))),
        "DerRunMchHrs": _parse_float(_first_value(row, ("DerRunMchHrs", "RunHrs", "Doba", "colDoba"))),
        "OpDatumSt": _as_clean_str(
            _first_value(
                row,
                ("OpDatumSt", "DerStartDate", "JshStartDate", "StartDate", "SchedStartDate", "colOpDatumSt"),
            )
        ),
        "OpDatumSp": _as_clean_str(
            _first_value(
                row,
                ("OpDatumSp", "DerEndDate", "JshEndDate", "EndDate", "SchedFinishDate", "colOpDatumSp"),
            )
        ),
    }


def _parse_job_suffix_oper(value: Any) -> Optional[tuple[str, str, str]]:
    text = _as_clean_str(value)
    if not text:
        return None

    # Prefer separators that do not clash with slash inside job number.
    for sep in (";", "|", ",", ":", "_", "-", " "):
        if sep not in text:
            continue
        parts = [part.strip() for part in text.split(sep) if part.strip()]
        if len(parts) < 3:
            continue
        suffix = parts[-2]
        oper = parts[-1]
        job = sep.join(parts[:-2]).strip()
        if job and suffix.isdigit() and oper.isdigit():
            return (job, suffix or "0", oper)

    # Slash fallback: parse from right side to preserve slash in job number.
    slash_match = re.match(r"^\s*(.+)/(\d+)/(\d+)\s*$", text)
    if slash_match:
        job = slash_match.group(1).strip()
        suffix = slash_match.group(2).strip()
        oper = slash_match.group(3).strip()
        if job and oper:
            return (job, suffix or "0", oper)
    return None


def _infor_ok(response: Dict[str, Any], *, allow_nonzero_return: bool = False) -> bool:
    msg_code = int(response.get("MessageCode", 0) or 0)
    if msg_code != 0:
        return False

    if allow_nonzero_return:
        return True

    infobar = (response.get("ReturnValue") or "").strip()
    if infobar and infobar not in {"0", "null", "NULL", "0.00"}:
        return False

    return True


def _infor_error(response: Dict[str, Any]) -> str:
    msg_code = int(response.get("MessageCode", 0) or 0)
    infobar = (response.get("ReturnValue") or "").strip()
    message = (response.get("Message") or "").strip()

    if msg_code != 0:
        return f"Infor chyba (kód {msg_code}): {infobar or message or 'Unknown error'}"

    if infobar and infobar not in {"0", "null", "NULL", "0.00"}:
        return f"Infor SP chyba: {infobar}"

    return "Unknown Infor error"


def _extract_rv_from_response(
    response: Dict[str, Any],
    rv_indices: Dict[str, int],
) -> Dict[str, str]:
    """Extract RV (output) parameter values from invoke_method_positional response.

    Infor REST API returns ALL positional params (V + RV) comma-separated in
    ReturnValue.  RV params at their original indices contain SP output values.

    Used to capture vOldEmpNum, vStroj, vWc from ValidateOperNumMachineSp
    (indices 7, 8, 9 in 11-param signature — verified from InduStream IL).

    Args:
        response: Raw Infor API response dict
        rv_indices: Mapping of logical name → positional index
                    e.g. {"old_emp_num": 7, "stroj": 8, "wc": 9}
    Returns:
        Dict of logical name → extracted value (only non-empty values included)
    """
    rv_raw = (response.get("ReturnValue") or "").strip()
    if not rv_raw:
        return {}
    parts = rv_raw.split(",")
    result: Dict[str, str] = {}
    for name, idx in rv_indices.items():
        if idx < len(parts):
            val = parts[idx].strip()
            if val:
                result[name] = val
    return result


async def _invoke_checked(
    infor_client,
    method_name: str,
    positional_values: Sequence[str],
    *,
    allow_nonzero_return: bool = False,
) -> Dict[str, Any]:
    response = await infor_client.invoke_method_positional(
        ido_name=_WRITE_IDO,
        method_name=method_name,
        positional_values=[str(v) if v is not None else "" for v in positional_values],
    )
    if not _infor_ok(response, allow_nonzero_return=allow_nonzero_return):
        raise RuntimeError(_infor_error(response))
    return response


async def _invoke_checked_candidates(
    infor_client,
    method_name: str,
    candidates: Sequence[Sequence[str]],
    *,
    allow_nonzero_return: bool = False,
) -> Dict[str, Any]:
    errors: List[str] = []
    for idx, params in enumerate(candidates, start=1):
        try:
            result = await _invoke_checked(
                infor_client,
                method_name,
                params,
                allow_nonzero_return=allow_nonzero_return,
            )
            logger.info("%s accepted variant %s (params=%s)", method_name, idx, len(params))
            return result
        except Exception as exc:
            errors.append(f"variant {idx}: {exc}")

    raise RuntimeError(f"{method_name} selhalo ve všech variantách: {' | '.join(errors)}")


async def _invoke_nonfatal_candidates(
    infor_client,
    method_name: str,
    candidates: Sequence[Sequence[str]],
) -> None:
    for params in candidates:
        try:
            await infor_client.invoke_method_positional(
                ido_name=_WRITE_IDO,
                method_name=method_name,
                positional_values=[str(v) if v is not None else "" for v in params],
            )
            return
        except Exception:
            continue


async def _invoke_best_effort_candidates(
    infor_client,
    method_name: str,
    candidates: Sequence[Sequence[str]],
    *,
    allow_nonzero_return: bool = False,
) -> None:
    errors: List[str] = []
    for idx, params in enumerate(candidates, start=1):
        try:
            await _invoke_checked(
                infor_client,
                method_name,
                params,
                allow_nonzero_return=allow_nonzero_return,
            )
            logger.info("%s accepted variant %s (params=%s)", method_name, idx, len(params))
            return
        except Exception as exc:
            errors.append(f"variant {idx}: {exc}")

    if errors:
        logger.warning("%s best-effort skipped: %s", method_name, " | ".join(errors))


async def _load_collection_first(
    infor_client,
    ido_name: str,
    property_sets: Sequence[Sequence[str]],
    *,
    filter_expr: Optional[str] = None,
    order_by: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """Načte data z IDO s automatickou paginací přes bookmark.

    Infor API typicky vrací max ~200 řádků na stránku. Tato funkce
    automaticky následuje bookmark dokud nejsou načteny všechny záznamy
    (nebo dosažen record_cap). Řádky se deduplikují podle RowPointer
    (pokud existuje), jinak podle všech hodnot řádku.
    """
    errors: List[str] = []

    for properties in property_sets:
        kwargs: Dict[str, Any] = {
            "ido_name": ido_name,
            "properties": list(properties),
            "record_cap": record_cap,
        }
        if filter_expr:
            kwargs["filter"] = filter_expr
        if order_by:
            kwargs["order_by"] = order_by

        try:
            result = await infor_client.load_collection(**kwargs)
            message_code = result.get("message_code")
            message = (result.get("message") or "").strip()
            if message_code not in (None, 0, 200, 210):
                errors.append(f"{list(properties)} -> {message or f'MessageCode {message_code}'}")
                continue

            all_data = list(result.get("data", []))
            page_sizes = [len(all_data)]

            # Automatická paginace přes bookmark.
            # Infor API typicky vrací max ~200 řádků na stránku nezávisle na record_cap.
            # Paginace pokračuje dokud:
            #   - has_more je True a bookmark existuje
            #   - nedosáhli jsme record_cap
            bookmark = result.get("bookmark")
            has_more = result.get("has_more", False)
            page = 1
            while has_more and bookmark and (record_cap <= 0 or len(all_data) < record_cap):
                page += 1
                page_kwargs: Dict[str, Any] = {
                    "ido_name": ido_name,
                    "properties": list(properties),
                    "record_cap": record_cap,
                    "load_type": "NEXT",
                    "bookmark": bookmark,
                }
                if filter_expr:
                    page_kwargs["filter"] = filter_expr
                if order_by:
                    page_kwargs["order_by"] = order_by
                next_result = await infor_client.load_collection(**page_kwargs)
                next_code = next_result.get("message_code")
                if next_code not in (None, 0, 200, 210):
                    logger.warning("LoadCollection %s page %d: error code %s", ido_name, page, next_code)
                    break
                page_data = list(next_result.get("data", []))
                if not page_data:
                    break
                page_sizes.append(len(page_data))
                all_data.extend(page_data)
                new_bookmark = next_result.get("bookmark")
                if new_bookmark == bookmark:
                    break
                bookmark = new_bookmark
                has_more = next_result.get("has_more", False)

            if page > 1:
                before = len(all_data)
                all_data = _dedup_rows(all_data, list(properties))
                after = len(all_data)
                logger.info(
                    "LoadCollection %s: %d pages %s, %d rows (dedup removed %d)",
                    ido_name, page, page_sizes, after, before - after,
                )
            else:
                logger.info(
                    "LoadCollection %s: 1 page, %d rows",
                    ido_name, len(all_data),
                )

            return all_data
        except Exception as exc:
            errors.append(f"{list(properties)} -> {exc}")

    raise RuntimeError(
        f"LoadCollection {ido_name} failed for all property sets: {' || '.join(errors)}"
    )


def _dedup_rows(
    rows: List[Dict[str, Any]],
    properties: List[str],
) -> List[Dict[str, Any]]:
    """Deduplikuje řádky z Infor API (paginace může vracet overlapping data).

    Používá RowPointer (pokud existuje) jako unikátní klíč, jinak
    kombinaci všech hodnot řádku.
    """
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for row in rows:
        rp = row.get("RowPointer")
        if rp:
            key: Any = rp
        else:
            key = tuple(str(row.get(p, "")) for p in properties)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _eq_filter(field: str, value: str) -> str:
    safe_value = value.strip().replace("'", "''")
    return f"{field} = '{safe_value}'"


def _or_item_filter(field: str, values: Sequence[str]) -> Optional[str]:
    cleaned = []
    seen: set[str] = set()
    for value in values:
        text = _as_clean_str(value)
        if not text:
            continue
        upper = text.upper()
        if upper in seen:
            continue
        seen.add(upper)
        cleaned.append(text)
    if not cleaned:
        return None
    parts: List[str] = []
    for value in cleaned:
        safe_value = value.replace("'", "''")
        parts.append(f"{field} = '{safe_value}'")
    return " OR ".join(parts)


def _is_jbr_detail_only_bookmark(value: Any) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    text_lower = text.lower()
    return "<p>sessionid</p>" in text_lower and "<p>opernum</p>" in text_lower and "<p>job</p>" not in text_lower


async def _fetch_queue_from_jbr(
    infor_client,
    wc: Optional[str],
    record_cap: int,
    *,
    truncate: bool = True,
) -> List[Dict[str, Any]]:
    wc_upper = (wc or "").strip().upper()
    fetch_cap = min(max(record_cap * 10, record_cap), 5000)

    try:
        rows = await _load_collection_first(
            infor_client,
            ido_name="IteCzTsdJbrDetails",
            property_sets=_QUEUE_PROP_SETS,
            record_cap=fetch_cap,
        )
    except Exception as exc:
        # Some Infor installations expose only default view columns for this IDO.
        logger.warning("JbrDetails property-set load failed, trying default properties: %s", exc)
        result = await infor_client.load_collection(
            ido_name="IteCzTsdJbrDetails",
            record_cap=fetch_cap,
        )
        message_code = result.get("message_code")
        if message_code not in (None, 0, 200, 210):
            message = (result.get("message") or "").strip() or f"MessageCode {message_code}"
            raise RuntimeError(message)
        rows = list(result.get("data", []))
        if not rows and _is_jbr_detail_only_bookmark(result.get("bookmark")):
            raise RuntimeError("JBR detail-only schema (SessionId/OperNum) cannot provide queue rows.")

    queue: List[Dict[str, Any]] = []
    for row in rows:
        normalized = _normalize_queue_row(row)
        if not normalized:
            continue
        if wc_upper and ((normalized.get("Wc") or "").strip().upper() != wc_upper):
            continue
        if _is_operation_completed_row(normalized):
            continue
        queue.append(normalized)

    queue.sort(key=lambda item: (_sort_key_for_date(item.get("OpDatumSt")), item["Job"], item["OperNum"]))
    if truncate:
        return queue[:record_cap]
    return queue


async def _fetch_queue_from_sljobroutes(
    infor_client,
    wc: Optional[str],
    record_cap: int,
    *,
    truncate: bool = True,
) -> List[Dict[str, Any]]:
    filters = [_eq_filter("Type", "J"), _eq_filter("JobStat", "R")]
    if wc:
        filters.append(_eq_filter("Wc", wc))
    filter_expr = " AND ".join(filters)

    fetch_cap = min(max(record_cap * 10, record_cap), 5000)
    rows = await _load_collection_first(
        infor_client,
        ido_name="SLJobRoutes",
        property_sets=_JOB_ROUTE_PROP_SETS,
        filter_expr=filter_expr,
        order_by="DerStartDate ASC, Job ASC, OperNum ASC",
        record_cap=fetch_cap,
    )

    queue: List[Dict[str, Any]] = []
    for row in rows:
        normalized = _normalize_queue_row(row)
        if not normalized:
            continue
        if _is_operation_completed_row(normalized):
            continue
        queue.append(normalized)

    queue.sort(key=lambda item: (_sort_key_for_date(item.get("OpDatumSt")), item["Job"], item["OperNum"]))
    if truncate:
        return queue[:record_cap]
    return queue


async def fetch_wc_queue(
    infor_client,
    wc: Optional[str] = None,
    record_cap: int = 200,
    job_filter: Optional[str] = None,
    sort_by: str = "OpDatumSt",
    sort_dir: str = "asc",
) -> List[Dict[str, Any]]:
    """Načte frontu práce z JBR; při detail-only JBR schema přepne na SLJobRoutes."""
    queue: List[Dict[str, Any]]
    try:
        queue = await _fetch_queue_from_jbr(infor_client, wc, max(record_cap, 200), truncate=False)
    except Exception as exc:
        if "detail-only schema" in str(exc):
            logger.warning("JBR queue unsupported on this instance, switching to SLJobRoutes compatibility mode")
            try:
                queue = await _fetch_queue_from_sljobroutes(infor_client, wc, max(record_cap, 200), truncate=False)
            except Exception as compat_exc:
                logger.error("SLJobRoutes compatibility queue load failed: %s", compat_exc)
                raise RuntimeError(f"SLJobRoutes queue source unavailable: {compat_exc}") from compat_exc

        else:
            logger.error("JbrDetails queue load failed: %s", exc)
            raise RuntimeError(f"JbrDetails queue source unavailable: {exc}") from exc

    safe_job_filter = (job_filter or "").strip().upper()
    if safe_job_filter:
        queue = [row for row in queue if safe_job_filter in (row.get("Job", "").upper())]

    queue = sort_queue(queue, sort_by=sort_by, sort_dir=sort_dir)
    return queue[:record_cap]


async def fetch_open_jobs(
    infor_client,
    wc_filter: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """Vrátí deduplikovaný seznam zakázek (1 řádek na Job+Suffix)."""
    queue = await fetch_wc_queue(
        infor_client=infor_client,
        wc=wc_filter,
        record_cap=record_cap * 10,
    )

    seen: set[tuple[str, str]] = set()
    jobs: List[Dict[str, Any]] = []
    for item in queue:
        key = (item["Job"], item["Suffix"])
        if key in seen:
            continue
        seen.add(key)
        jobs.append(
            {
                "Job": item["Job"],
                "Suffix": item["Suffix"],
                "Type": "J",
                "Wc": item.get("Wc"),
                "OperNum": item["OperNum"],
                "DerJobItem": item.get("DerJobItem"),
                "JobDescription": item.get("JobDescription"),
                "JobStat": "R",
                "JobQtyReleased": item.get("JobQtyReleased"),
                "QtyComplete": item.get("QtyComplete"),
                "QtyScrapped": item.get("QtyScrapped"),
                "JshSetupHrs": item.get("JshSetupHrs"),
                "DerRunMchHrs": item.get("DerRunMchHrs"),
            }
        )
        if len(jobs) >= record_cap:
            break

    return jobs


async def fetch_machine_plan(
    infor_client,
    wc: Optional[str] = None,
    job_filter: Optional[str] = None,
    sort_by: str = "OpDatumSt",
    sort_dir: str = "asc",
    record_cap: int = 500,
) -> List[Dict[str, Any]]:
    """Plán stroje — released operace ze stejného zdroje jako fronta (JBR/SLJobRoutes),
    zásobník (F/S/W) doplněn přímo ze SLJobRoutes (read-only)."""

    # 1) Released: stejný zdroj jako existující fronta práce (JBR → SLJobRoutes fallback)
    released = await fetch_wc_queue(
        infor_client=infor_client,
        wc=wc,
        record_cap=record_cap,
        job_filter=job_filter,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    for row in released:
        row["JobStat"] = "R"

    # 2) Zásobník (F/S/W): přímo ze SLJobRoutes — jen pro zobrazení, nelze vykazovat
    backlog: List[Dict[str, Any]] = []
    try:
        stat_values = ["F", "S", "W"]
        stat_filter = " OR ".join(_eq_filter("JobStat", s) for s in stat_values)
        filters = [_eq_filter("Type", "J"), f"({stat_filter})"]
        if wc:
            filters.append(_eq_filter("Wc", wc))
        filter_expr = " AND ".join(filters)

        fetch_cap = min(max(record_cap * 2, 200), 5000)
        rows = await _load_collection_first(
            infor_client,
            ido_name="SLJobRoutes",
            property_sets=_JOB_ROUTE_PROP_SETS,
            filter_expr=filter_expr,
            order_by="DerStartDate ASC, Job ASC, OperNum ASC",
            record_cap=fetch_cap,
        )

        for row in rows:
            normalized = _normalize_queue_row(row)
            if not normalized:
                continue
            if _is_operation_completed_row(normalized):
                continue
            job_stat = _as_clean_str(row.get("JobStat")) or "F"
            normalized["JobStat"] = job_stat.upper()
            backlog.append(normalized)

        safe_job_filter = (job_filter or "").strip().upper()
        if safe_job_filter:
            backlog = [r for r in backlog if safe_job_filter in (r.get("Job", "").upper())]

        backlog = sort_queue(backlog, sort_by=sort_by, sort_dir=sort_dir)
        backlog = backlog[:record_cap]
    except Exception as exc:
        logger.warning("Backlog (F/S/W) load failed, showing released only: %s", exc)

    return released + backlog


async def fetch_vp_list(
    infor_client,
    stat_values: Sequence[str] = ("R", "F"),
    search: Optional[str] = None,
    wc: Optional[str] = None,
    sort_by: str = "Job",
    sort_dir: str = "asc",
    record_cap: int = 500,
) -> List[Dict[str, Any]]:
    """Live fallback pro VP list — znovupoužije fetch_machine_plan() a deduplikuje."""
    all_ops = await fetch_machine_plan(
        infor_client=infor_client,
        wc=None,
        record_cap=5000,
    )

    stat_set = set(s.upper() for s in stat_values)

    vp_map: Dict[str, Dict[str, Any]] = {}
    for row in all_ops:
        job_stat = (row.get("JobStat") or "R").upper()
        if job_stat not in stat_set:
            continue
        job = row.get("Job") or ""
        suffix = row.get("Suffix") or "0"
        key = f"{job}|{suffix}"

        if key not in vp_map:
            qty_c = row.get("QtyComplete") or row.get("Kusy")
            qty_s = row.get("QtyScrapped")
            vp_map[key] = {
                "job": job,
                "suffix": suffix,
                "item": row.get("DerJobItem") or row.get("Dil"),
                "description": row.get("JobDescription") or row.get("Nazev"),
                "job_stat": job_stat,
                "qty_released": row.get("JobQtyReleased") or row.get("VpMnoz"),
                "qty_complete": _parse_float(qty_c),
                "qty_scrapped": _parse_float(qty_s),
                "start_date": row.get("OpDatumSt"),
                "end_date": row.get("OpDatumSp"),
                "oper_count": 1,
                "_wcs": {(row.get("Wc") or "").upper()},
            }
        else:
            entry = vp_map[key]
            entry["oper_count"] += 1
            entry["_wcs"].add((row.get("Wc") or "").upper())
            op_st = row.get("OpDatumSt")
            op_sp = row.get("OpDatumSp")
            if op_st and (not entry["start_date"] or op_st < entry["start_date"]):
                entry["start_date"] = op_st
            if op_sp and (not entry["end_date"] or op_sp > entry["end_date"]):
                entry["end_date"] = op_sp

    result = list(vp_map.values())

    if wc:
        wc_upper = wc.strip().upper()
        result = [r for r in result if wc_upper in r["_wcs"]]

    if search:
        s = search.strip().upper()
        result = [
            r for r in result
            if s in (r["job"] or "").upper()
            or s in (r["item"] or "").upper()
            or s in (r["description"] or "").upper()
        ]

    for r in result:
        r.pop("_wcs", None)

    reverse = sort_dir.lower() == "desc"
    def _vp_sort_key(r: Dict[str, Any]) -> Any:
        v = r.get(sort_by.lower()) if sort_by.lower() in r else r.get(sort_by)
        return v if v is not None else ""
    result.sort(key=_vp_sort_key, reverse=reverse)

    return result[:record_cap]


async def fetch_job_operations(
    infor_client,
    job: str,
    suffix: str = "0",
    sort_by: str = "OpDatumSt",
    sort_dir: str = "asc",
) -> List[Dict[str, Any]]:
    """Načte VŠECHNY operace zakázky přímo ze SLJobRoutes (včetně hotových)."""
    safe_job = job.strip()
    safe_suffix = suffix.strip() or "0"

    try:
        filter_expr = (
            f"{_eq_filter('Job', safe_job)} AND "
            f"{_eq_filter('Suffix', safe_suffix)} AND "
            f"{_eq_filter('Type', 'J')}"
        )
        route_rows = await _load_collection_first(
            infor_client,
            ido_name="SLJobRoutes",
            property_sets=_JOB_ROUTE_PROP_SETS,
            filter_expr=filter_expr,
            order_by="OperNum ASC",
            record_cap=200,
        )

        operations: List[Dict[str, Any]] = []
        for row in route_rows:
            normalized = _normalize_queue_row(row)
            if not normalized:
                continue
            operations.append(
                {
                    "Job": normalized["Job"],
                    "Suffix": normalized["Suffix"],
                    "OperNum": normalized["OperNum"],
                    "Wc": normalized.get("Wc") or "",
                    "QtyReleased": normalized.get("JobQtyReleased"),
                    "QtyComplete": normalized.get("QtyComplete"),
                    "ScrapQty": normalized.get("QtyScrapped"),
                    "SetupHrs": normalized.get("JshSetupHrs"),
                    "RunHrs": normalized.get("DerRunMchHrs"),
                    "OpDatumSt": normalized.get("OpDatumSt"),
                    "OpDatumSp": normalized.get("OpDatumSp"),
                }
            )

        if operations:
            operations = _sort_operations(operations, sort_by=sort_by, sort_dir=sort_dir)
        return operations
    except Exception as exc:
        logger.error("Operations load failed: %s", exc)
        raise RuntimeError(f"Operations source unavailable: {exc}") from exc


async def fetch_job_materials(
    infor_client,
    job: str,
    suffix: str = "0",
    oper_num: str = "0",
    sort_by: str = "Material",
    sort_dir: str = "asc",
) -> List[Dict[str, Any]]:
    """Načte materiál k operaci (IteCzTsdSLJobMatls)."""
    safe_job = job.strip()
    safe_suffix = suffix.strip() or "0"
    safe_oper = oper_num.strip() or "0"

    filter_expr = (
        f"{_eq_filter('Job', safe_job)} AND "
        f"{_eq_filter('Suffix', safe_suffix)} AND "
        f"{_eq_filter('OperNum', safe_oper)}"
    )
    job_filter_expr = (
        f"{_eq_filter('Job', safe_job)} AND "
        f"{_eq_filter('Suffix', safe_suffix)}"
    )

    try:
        rows = await _load_collection_first(
            infor_client,
            ido_name="IteCzTsdSLJobMatls",
            property_sets=_MATERIAL_PROP_SETS,
            filter_expr=filter_expr,
            record_cap=100,
        )
    except Exception as exc:
        logger.warning("fetch_job_materials failed (job=%s oper=%s): %s", job, oper_num, exc)
        return []

    materials: List[Dict[str, Any]] = []
    for row in rows:
        material = _as_clean_str(_first_value(row, ("MaterialBd", "Item", "Material")))
        if not material:
            continue

        materials.append(
            {
                "Material": material,
                "Desc": _as_clean_str(
                    _first_value(row, ("DescriptionBd", "DerItemDescription", "Desc", "Description"))
                ),
                "TotCons": _parse_float(_first_value(row, ("TotalConsumptionBd", "TotCons", "MatlQty"))),
                # Qty držíme v jednotce materiálu; DerQty často není v materiálové UM.
                "Qty": _parse_float(_first_value(row, ("QtyPerPcBd", "Qty"))),
                "BatchCons": _parse_float(_first_value(row, ("BatchConsumptionBd", "BatchCons"))),
                "QtyIssued": _parse_float(_first_value(row, ("QtyIssued", "IssuedQty", "MatlQtyIssued"))),
                "RemainingCons": _parse_float(
                    _first_value(
                        row,
                        ("RemainingConsumptionBd", "RemConsumptionBd", "QtyRemaining", "RemainingQty", "RemQty"),
                    )
                ),
                "UM": _as_clean_str(_first_value(row, ("UM", "Uom", "Unit", "ItmUM"))),
            }
        )

    # Fallback/rozšíření jednotek: některé instalace mají plná UM data pouze v SLJobmatls.
    alt_rows: List[Dict[str, Any]] = []
    try:
        alt_rows = await _load_collection_first(
            infor_client,
            ido_name="SLJobmatls",
            property_sets=_SLJOBMATLS_UOM_PROP_SETS,
            # Některé instalace vrací použitelné UM pro stejný item na jiných operacích VP.
            filter_expr=job_filter_expr,
            record_cap=2000,
        )
    except Exception:
        alt_rows = []

    # Některé instalace po odvodu vrací stejný materiál ve více řádcích (sekvence spotřeby).
    # Pro dílnickou UI vracíme 1 řádek na materiál.
    deduped: Dict[str, Dict[str, Any]] = {}
    um_sets: Dict[str, set[str]] = {}
    qty_by_um: Dict[str, Dict[str, float]] = {}
    batch_by_um: Dict[str, Dict[str, float]] = {}

    def _remember_um(material_key: str, um: Optional[str], qty: Optional[float], batch: Optional[float]) -> None:
        if not um:
            return
        um_sets.setdefault(material_key, set()).add(um)
        if qty is not None:
            qty_by_um.setdefault(material_key, {})
            qty_by_um[material_key].setdefault(um, qty)
        if batch is not None and batch > 0:
            batch_by_um.setdefault(material_key, {})
            batch_by_um[material_key].setdefault(um, batch)

    for row in materials:
        key = (row.get("Material") or "").strip().upper()
        if not key:
            continue
        existing = deduped.get(key)
        _remember_um(key, _as_clean_str(row.get("UM")), _parse_float(row.get("Qty")), _parse_float(row.get("BatchCons")))
        if existing is None:
            deduped[key] = dict(row)
            continue
        for field in ("Desc", "UM", "TotCons", "Qty", "BatchCons", "QtyIssued", "RemainingCons"):
            if existing.get(field) is None and row.get(field) is not None:
                existing[field] = row.get(field)

    for row in alt_rows:
        item = _as_clean_str(_first_value(row, ("Item", "ItmItem", "Material")))
        if not item:
            continue
        key = item.upper()
        um = _as_clean_str(_first_value(row, ("UM", "Uom", "Unit")))
        qty_conv = _parse_float(_first_value(row, ("MatlQtyConv", "Qty", "MatlQty")))
        _remember_um(key, um, qty_conv, None)
        existing = deduped.get(key)
        if not existing:
            continue
        if not existing.get("UM") and um:
            existing["UM"] = um
        if existing.get("Qty") is None and qty_conv is not None:
            existing["Qty"] = qty_conv
        batch_from_alt = _parse_float(_first_value(row, ("DerMatlTransQty", "BatchCons")))
        if existing.get("BatchCons") is None and batch_from_alt is not None and batch_from_alt > 0:
            existing["BatchCons"] = batch_from_alt
        _remember_um(key, um, None, batch_from_alt)
        total_from_alt = _parse_float(_first_value(row, ("DerMatlQtyRequired",)))
        if existing.get("TotCons") is None and total_from_alt is not None and total_from_alt > 0:
            existing["TotCons"] = total_from_alt
        issued_from_alt = _parse_float(_first_value(row, ("DerQtyIssuedConv", "QtyIssued")))
        # QtyIssued na IteCzTsdSLJobMatls byva v jine jednotce; pro UI preferujeme
        # konvertovanou hodnotu z SLJobmatls (DerQtyIssuedConv) pokud je dostupna.
        if issued_from_alt is not None:
            existing["QtyIssued"] = issued_from_alt
        remaining_from_alt = _parse_float(
            _first_value(row, ("DerQtyToPick", "QtyRemaining", "RemainingQty", "RemQty"))
        )
        if existing.get("RemainingCons") is None and remaining_from_alt is not None:
            existing["RemainingCons"] = remaining_from_alt

    # Standardní CSI zdroj alternativních MJ pro položku (bez custom Ite*):
    # SLUmConvs(Item, FromUM, ToUM, ConvFactor).
    # Používáme pouze seznam dostupných UM; množství bez explicitního Infor pole nedopočítáváme.
    item_filters = [
        _as_clean_str(row.get("Material"))
        for row in deduped.values()
    ]
    if item_filters:
        for chunk_start in range(0, len(item_filters), 25):
            chunk = item_filters[chunk_start:chunk_start + 25]
            umconv_filter = _or_item_filter("Item", chunk)
            if not umconv_filter:
                continue
            try:
                umconv_rows = await _load_collection_first(
                    infor_client,
                    ido_name="SLUmConvs",
                    property_sets=_SLUMCONVS_PROP_SETS,
                    filter_expr=umconv_filter,
                    record_cap=2000,
                )
            except Exception:
                umconv_rows = []

            for row in umconv_rows:
                item = _as_clean_str(row.get("Item"))
                if not item:
                    continue
                key = item.upper()
                from_um = _as_clean_str(_first_value(row, ("FromUM", "FromUm", "FromUom", "FromUnit")))
                to_um = _as_clean_str(_first_value(row, ("ToUM", "ToUm", "ToUom", "ToUnit")))
                _remember_um(key, from_um, None, None)
                _remember_um(key, to_um, None, None)

    for key, row in deduped.items():
        available = sorted(um_sets.get(key, set()))
        if available:
            row["UMs"] = available
            if not row.get("UM"):
                row["UM"] = available[0]
        if key in qty_by_um:
            row["QtyByUM"] = qty_by_um[key]
        if key in batch_by_um:
            row["BatchConsByUM"] = batch_by_um[key]
        # Nezobrazuj nulovou dávku jako validní hodnotu; UI pak použije TotCons/Qty fallback.
        batch_value = _parse_float(row.get("BatchCons"))
        if batch_value is not None and batch_value <= 0:
            row["BatchCons"] = None

    materials = list(deduped.values())
    return _sort_materials(materials, sort_by=sort_by, sort_dir=sort_dir)


def _coitem_customer_code(row: Dict[str, Any]) -> Optional[str]:
    return _as_clean_str(_first_value(row, ("CoCustNum", "CustNum", "CoCustNnum")))


# _build_orders_overview_filter removed — replaced by _build_view_filter for IteRybPrehledZakazekView


def _is_vp_like(job: Optional[str]) -> bool:
    text = (_as_clean_str(job) or "").upper()
    return "VP" in text


def _split_job_key(job_key: Optional[str]) -> tuple[Optional[str], str]:
    text = _as_clean_str(job_key)
    if not text:
        return (None, "0")
    if "|" not in text:
        return (text, "0")
    job, suffix = text.split("|", 1)
    return (_as_clean_str(job), _normalize_suffix_for_key(suffix))


def _job_has_remaining_qty(
    job_meta: Optional[Dict[str, Any]],
    route_rows: Sequence[Dict[str, Any]],
) -> bool:
    released_qty = _parse_float(_first_value(job_meta or {}, ("QtyReleased", "JobQtyReleased")))
    completed_qty = _parse_float(_first_value(job_meta or {}, ("QtyComplete",)))
    scrapped_qty = _parse_float(_first_value(job_meta or {}, ("QtyScrapped",)))

    if released_qty is None and route_rows:
        released_qty = _parse_float(_first_value(route_rows[0], ("JobQtyReleased",)))
    if completed_qty is None and route_rows:
        completed_qty = max(_parse_float(row.get("QtyComplete")) or 0.0 for row in route_rows)
    if scrapped_qty is None and route_rows:
        scrapped_qty = max(_parse_float(row.get("QtyScrapped")) or 0.0 for row in route_rows)

    if released_qty is None:
        return False
    return released_qty - (completed_qty or 0.0) - (scrapped_qty or 0.0) > _QTY_EPSILON


_VP_STATUS_RANK = {"R": 0, "F": 1, "S": 2}


def _sort_vp_candidates_by_status(
    candidate_keys: Sequence[str],
    *,
    jobs_by_key: Dict[str, Dict[str, Any]],
    routes_by_key: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    """Sort VP candidates: Released > Firm > other, in-progress first, newest first."""
    unique: List[str] = []
    seen: set[str] = set()
    for key in candidate_keys:
        normalized = _as_clean_str(key)
        if not normalized:
            continue
        upper = normalized.upper()
        if upper in seen:
            continue
        seen.add(upper)
        unique.append(normalized)

    def _rank(job_key_value: str) -> tuple:
        job_meta = jobs_by_key.get(job_key_value, {})
        status = (_as_clean_str(_first_value(job_meta, ("Stat", "JobStat"))) or "").upper()
        route_rows = routes_by_key.get(job_key_value, [])
        operations = _build_route_operations(route_rows)
        has_in_progress = any(op.get("status") == "in_progress" for op in operations)
        record_date = _as_clean_str(job_meta.get("RecordDate"))
        due_date = _as_clean_str(_first_value(job_meta, ("DerDueDate", "JschEndDate")))
        job, suffix = _split_job_key(job_key_value)
        return (
            _VP_STATUS_RANK.get(status, 9),
            0 if has_in_progress else 1,
            _sort_key_for_date(due_date),
            _sort_key_for_text(job),
            _sort_key_for_text(suffix),
        )

    return sorted(unique, key=_rank)


def _sort_job_candidates(
    candidates: Sequence[str],
    *,
    jobs_by_key: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Backward-compatible sorter used by tests and older overview code paths."""
    normalized_keys = [f"{job}|0" for job in candidates]
    sorted_keys = _sort_job_candidate_keys(
        normalized_keys,
        jobs_by_key=jobs_by_key,
        routes_by_key={},
        source_priority={key: 1 for key in normalized_keys},
    )
    out: List[str] = []
    for key in sorted_keys:
        job, _suffix = _split_job_key(key)
        if job:
            out.append(job)
    return out


def _sort_job_candidate_keys(
    candidate_keys: Sequence[str],
    *,
    jobs_by_key: Dict[str, Dict[str, Any]],
    routes_by_key: Dict[str, List[Dict[str, Any]]],
    source_priority: Dict[str, int],
) -> List[str]:
    unique: List[str] = []
    seen: set[str] = set()
    for key in candidate_keys:
        normalized = _as_clean_str(key)
        if not normalized:
            continue
        upper = normalized.upper()
        if upper in seen:
            continue
        seen.add(upper)
        unique.append(normalized)

    def _rank(job_key_value: str) -> tuple:
        job, suffix = _split_job_key(job_key_value)
        job_meta = jobs_by_key.get(job_key_value, {})
        due_date = _as_clean_str(_first_value(job_meta, ("DerDueDate", "JschEndDate", "RecordDate")))
        route_rows = routes_by_key.get(job_key_value, [])
        operations = _build_route_operations(route_rows)
        has_in_progress = any(op.get("status") == "in_progress" for op in operations)
        return (
            source_priority.get(job_key_value, 9),
            0 if _is_vp_like(job) else 1,
            0 if has_in_progress else 1,
            _sort_key_for_date(due_date),
            _sort_key_for_text(job),
            _sort_key_for_text(suffix),
        )

    return sorted(unique, key=_rank)


def _build_route_operations(routes: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_routes = sorted(
        routes,
        key=lambda row: (
            _oper_sort_key(_as_clean_str(row.get("OperNum"))),
            _sort_key_for_date(_as_clean_str(row.get("DerStartDate"))),
        ),
    )
    out: List[Dict[str, Any]] = []
    for row in sorted_routes:
        out.append(
            {
                "oper_num": _as_clean_str(row.get("OperNum")) or "",
                "wc": _as_clean_str(row.get("Wc")) or "",
                "status": _operation_status(row),
                "state_text": _status_state_text(row) or None,
            }
        )
    return out


def _build_view_operations(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Převede flat Wc01-10 / Comp01-10 / Wip01-10 sloupce na seznam operací."""
    ops: List[Dict[str, Any]] = []
    for i in range(1, 11):
        idx = f"{i:02d}"
        wc = _as_clean_str(row.get(f"Wc{idx}"))
        if not wc:
            break
        comp = str(row.get(f"Comp{idx}", "0")).strip()
        wip = str(row.get(f"Wip{idx}", "0")).strip()
        if comp == "1":
            status = "done"
        elif wip == "1":
            status = "in_progress"
        else:
            status = "idle"
        ops.append({"oper_num": str(i * 10), "wc": wc, "status": status, "state_text": None})
    return ops


def _build_view_materials(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Převede flat Mat01-03 / MatComp01-03 sloupce na seznam materiálových buněk."""
    mats: List[Dict[str, Any]] = []
    for i in range(1, 4):
        idx = f"{i:02d}"
        mat = _as_clean_str(row.get(f"Mat{idx}"))
        if not mat:
            continue
        comp = str(row.get(f"MatComp{idx}", "0")).strip()
        status = "done" if comp == "1" else "idle"
        mats.append({"material": mat, "status": status})
    return mats


def _build_view_filter(
    *,
    customer: Optional[str],
    due_from: Optional[str],
    due_to: Optional[str],
    search: Optional[str],
) -> Optional[str]:
    """Filtr pro IteRybPrehledZakazekView."""
    clauses: List[str] = [
        _status_in_filter("Stat", _ORDER_OVERVIEW_STATUS_DEFAULT),
    ]
    clauses.extend(
        _build_date_range_filter("DueDate", date_from=due_from, date_to=due_to)
    )
    safe_customer = _as_clean_str(customer)
    if safe_customer:
        escaped = safe_customer.replace("'", "''")
        clauses.append(f"CustNum = '{escaped}'")
    safe_search = _as_clean_str(search)
    if safe_search:
        escaped = safe_search.replace("'", "''")
        clauses.append(
            "("
            f"CoNum LIKE '%{escaped}%' OR "
            f"Item LIKE '%{escaped}%' OR "
            f"ItemDescription LIKE '%{escaped}%'"
            ")"
        )
    if not clauses:
        return None
    return " AND ".join(clauses)


_VIEW_PROPERTIES_CORE = [
    "CoNum", "CoLine", "CoRelease",
    "CustNum", "CustName", "CustPo", "CustShipName",
    "Item", "ItemDescription", "Stat",
    "DueDate", "PromiseDate", "ProjectedDate", "ConfirmedDate",
    "RybDeadLineDate", "RybCoOrderDate",
    "RybCoConfirmationDate", "RybDatumPotvrRadZak", "RybConfirmDate", "RybDatumSlibRadZak",
    "QtyOrderedConv", "QtyShipped", "QtyOnHand", "QtyAvailable", "QtyWIP",
    "Job", "Suffix", "JobCount",
    "Wc01", "Wc02", "Wc03", "Wc04", "Wc05", "Wc06", "Wc07", "Wc08", "Wc09", "Wc10",
    "Comp01", "Comp02", "Comp03", "Comp04", "Comp05", "Comp06", "Comp07", "Comp08", "Comp09", "Comp10",
    "Wip01", "Wip02", "Wip03", "Wip04", "Wip05", "Wip06", "Wip07", "Wip08", "Wip09", "Wip10",
    "Mat01", "Mat02", "Mat03", "MatComp01", "MatComp02", "MatComp03",
    "Ready", "Picked", "IsOverPromiseDate",
    "TotalWeight", "PriceConv", "RybCena",
    "Baleni", "Regal",
    "RecordDate",
]

# Primary: full property set; Fallback: bez custom Ryb confirm polí (nemusí existovat)
_VIEW_PROPERTIES_FALLBACK = [
    p for p in _VIEW_PROPERTIES_CORE
    if p not in ("RybCoConfirmationDate", "RybDatumPotvrRadZak", "RybConfirmDate", "RybDatumSlibRadZak")
]
_VIEW_PROP_SETS = [
    _VIEW_PROPERTIES_CORE,
    _VIEW_PROPERTIES_FALLBACK,
]


async def fetch_orders_overview(
    infor_client,
    *,
    customer: Optional[str] = None,
    due_from: Optional[str] = None,
    due_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """Vrátí dispečerský přehled zakázek z custom IDO IteRybPrehledZakazekView."""
    safe_limit = max(1, min(limit, 5000))
    view_filter = _build_view_filter(
        customer=customer, due_from=due_from, due_to=due_to, search=search,
    )

    rows = await _load_collection_first(
        infor_client,
        ido_name="IteRybPrehledZakazekView",
        property_sets=_VIEW_PROP_SETS,
        filter_expr=view_filter,
        order_by="DueDate ASC",
        record_cap=safe_limit,
    )
    logger.info("orders_overview: loaded %d rows from IteRybPrehledZakazekView (limit=%d)", len(rows), safe_limit)
    if not rows:
        return []

    # ── Pass 1: Sběr VP jobů podle Item ──
    # View vrací 1 Job per CO řádek, ale JobCount říká kolik VP existuje.
    # Pro single-VP items bereme data přímo z view.
    # Pro multi-VP items (JobCount > 1) děláme separátní SLJobRoutes lookup.
    item_vp_map: Dict[str, List[Dict[str, Any]]] = {}
    multi_vp_items: set[str] = set()
    seen_vp_jobs: set[str] = set()

    for row in rows:
        item = _as_clean_str(row.get("Item"))
        job = _as_clean_str(row.get("Job"))
        suffix = _as_clean_str(row.get("Suffix")) or "0"
        if not item or not job:
            continue

        # Zjistíme zda Item má více VP
        job_count_str = str(row.get("JobCount", "1")).strip()
        if job_count_str not in ("", "0", "1"):
            multi_vp_items.add(item)
            continue  # zpracujeme přes SLJobRoutes

        vp_key = f"{job}|{suffix}"
        if vp_key in seen_vp_jobs:
            continue
        seen_vp_jobs.add(vp_key)
        operations = _build_view_operations(row)
        if not operations:
            continue  # Job bez operací (completed) není kandidát
        entry = {
            "job": job,
            "suffix": suffix,
            "job_stat": None,
            "qty_released": None,
            "qty_complete": None,
            "qty_scrapped": None,
            "item": item,
            "customer_name": _as_clean_str(row.get("CustName")),
            "due_date": _as_clean_str(row.get("DueDate")),
            "operations": operations,
        }
        item_vp_map.setdefault(item, []).append(entry)

    # ── Multi-VP lookup přes SLJobRoutes ──
    if multi_vp_items:
        logger.info("orders_overview: %d items with multiple VPs, querying SLJobRoutes", len(multi_vp_items))
        multi_items_list = sorted(multi_vp_items)
        batch_size = 200
        all_route_rows: List[Dict[str, Any]] = []
        for batch_start in range(0, len(multi_items_list), batch_size):
            batch = multi_items_list[batch_start:batch_start + batch_size]
            item_filter = _or_item_filter("DerJobItem", batch)
            if not item_filter:
                continue
            filter_routes = f"({item_filter}) AND {_eq_filter('Type', 'J')} AND (JobStat = 'R' OR JobStat = 'F' OR JobStat = 'S')"
            try:
                batch_rows = await _load_collection_first(
                    infor_client,
                    ido_name="SLJobRoutes",
                    property_sets=_JOB_ROUTE_PROP_SETS,
                    filter_expr=filter_routes,
                    order_by="DerJobItem ASC, Job ASC, OperNum ASC",
                    record_cap=5000,
                )
                all_route_rows.extend(batch_rows)
            except Exception as exc:
                logger.warning("SLJobRoutes multi-VP lookup failed: %s", exc)

        # Seskupit podle Item → Job|Suffix → operace
        route_by_item: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for rrow in all_route_rows:
            r_item = _as_clean_str(rrow.get("DerJobItem"))
            r_job = _as_clean_str(rrow.get("Job"))
            r_suffix = _as_clean_str(rrow.get("Suffix")) or "0"
            if not r_item or not r_job:
                continue
            vp_key = f"{r_job}|{r_suffix}"
            if r_item not in route_by_item:
                route_by_item[r_item] = {}
            if vp_key not in route_by_item[r_item]:
                route_by_item[r_item][vp_key] = {
                    "job": r_job,
                    "suffix": r_suffix,
                    "job_stat": _as_clean_str(rrow.get("JobStat")),
                    "qty_released": _parse_float(rrow.get("JobQtyReleased")),
                    "qty_complete": None,
                    "qty_scrapped": None,
                    "item": r_item,
                    "customer_name": None,
                    "due_date": None,
                    "operations": [],
                }
            # Přidat operaci
            oper_num = _as_clean_str(rrow.get("OperNum"))
            wc = _as_clean_str(rrow.get("Wc"))
            if oper_num and wc:
                op_complete = _parse_float(rrow.get("QtyComplete")) or 0
                op_released = _parse_float(rrow.get("JobQtyReleased")) or 0
                if op_released > 0 and op_complete >= op_released:
                    op_status = "done"
                elif op_complete > 0:
                    op_status = "in_progress"
                else:
                    op_status = "idle"
                route_by_item[r_item][vp_key]["operations"].append({
                    "oper_num": oper_num,
                    "wc": wc,
                    "status": op_status,
                    "state_text": None,
                })

        # Seřadit operace numericky v každém VP
        for vp_dict in route_by_item.values():
            for vp in vp_dict.values():
                vp["operations"].sort(key=lambda op: int(op["oper_num"]) if op["oper_num"] and str(op["oper_num"]).isdigit() else 0)

        # Doplnit customer_name a due_date z view řádku, zapsat do item_vp_map
        for r_item, vp_dict in route_by_item.items():
            view_row = next((r for r in rows if _as_clean_str(r.get("Item")) == r_item), None)
            cust_name = _as_clean_str(view_row.get("CustName")) if view_row else None
            due_date = _as_clean_str(view_row.get("DueDate")) if view_row else None
            entries = list(vp_dict.values())
            for entry in entries:
                entry["customer_name"] = cust_name
                entry["due_date"] = due_date
            item_vp_map[r_item] = entries

        logger.info(
            "orders_overview: SLJobRoutes found %d route rows -> %d items with multi-VP data",
            len(all_route_rows), len(route_by_item),
        )

    multi_vp_counts = {item: len(vps) for item, vps in item_vp_map.items() if len(vps) > 1}
    logger.info("orders_overview: %d items with multiple VPs in final map", len(multi_vp_counts))

    # ── Confirm date lookup z SLCoItems (RybDatumPotvrRadZak) ──
    # View IteRybPrehledZakazekView toto pole nevrací, musíme ho načíst zvlášť.
    confirm_date_map: Dict[str, str] = {}  # "CoNum|CoLine|CoRelease" → date
    co_nums = sorted({_as_clean_str(r.get("CoNum")) or "" for r in rows if _as_clean_str(r.get("CoNum"))})
    if co_nums:
        batch_size = 200
        for batch_start in range(0, len(co_nums), batch_size):
            batch = co_nums[batch_start:batch_start + batch_size]
            co_filter = _or_item_filter("CoNum", batch)
            if not co_filter:
                continue
            try:
                co_rows = await _load_collection_first(
                    infor_client,
                    ido_name="SLCoItems",
                    property_sets=[
                        ["CoNum", "CoLine", "CoRelease", "RybDatumPotvrRadZak"],
                        ["CoNum", "CoLine", "CoRelease"],
                    ],
                    filter_expr=f"({co_filter})",
                    order_by="CoNum ASC, CoLine ASC",
                    record_cap=5000,
                )
                for cr in co_rows:
                    c_num = _as_clean_str(cr.get("CoNum")) or ""
                    c_line = _as_clean_str(cr.get("CoLine")) or ""
                    c_rel = _as_clean_str(cr.get("CoRelease")) or "0"
                    c_date = _as_clean_str(cr.get("RybDatumPotvrRadZak"))
                    if c_date:
                        confirm_date_map[f"{c_num}|{c_line}|{c_rel}"] = c_date
            except Exception as exc:
                logger.warning("SLCoItems confirm date lookup failed: %s", exc)
        logger.info("orders_overview: confirm_date_map has %d entries from SLCoItems", len(confirm_date_map))

    # ── Pass 2: Sestavení výstupních řádků ──
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        co_num = _as_clean_str(row.get("CoNum")) or ""
        co_line = _as_clean_str(row.get("CoLine")) or ""
        co_release = _as_clean_str(row.get("CoRelease")) or "0"
        row_id = f"{co_num}|{co_line}|{co_release}"
        if row_id in seen:
            continue
        seen.add(row_id)

        item = _as_clean_str(row.get("Item"))
        operations = _build_view_operations(row)
        job = _as_clean_str(row.get("Job"))
        job_has_routing = bool(operations)
        active_job = job if (job and job_has_routing) else None

        # VP candidates = všechny aktivní VP joby pro stejný Item
        vp_entries = item_vp_map.get(item, []) if item else []

        # VP operace mají přednost (skutečné OperNum z routingu)
        if vp_entries and vp_entries[0].get("operations"):
            operations = vp_entries[0]["operations"]

        customer_code = _as_clean_str(row.get("CustNum"))
        out.append({
            "row_id": row_id,
            "customer_code": customer_code,
            "customer_name": _as_clean_str(row.get("CustName")),
            "delivery_code": customer_code,
            "delivery_name": _as_clean_str(row.get("CustShipName")) or _as_clean_str(row.get("CustName")),
            "co_num": co_num,
            "co_line": co_line,
            "co_release": co_release,
            "item": _as_clean_str(row.get("Item")),
            "description": _as_clean_str(row.get("ItemDescription")),
            "material_ready": str(row.get("Ready", "0")).strip() == "1",
            "qty_ordered": _parse_float(row.get("QtyOrderedConv")),
            "qty_shipped": _parse_float(row.get("QtyShipped")),
            "qty_on_hand": _parse_float(row.get("QtyOnHand")),
            "qty_available": _parse_float(row.get("QtyAvailable")),
            "qty_wip": _parse_float(row.get("QtyWIP")),
            "due_date": _as_clean_str(row.get("DueDate")),
            "promise_date": _as_clean_str(row.get("PromiseDate")),
            "confirm_date": confirm_date_map.get(row_id, None),
            "vp_candidates": vp_entries,
            "selected_vp_job": active_job,
            "operations": operations,
            "materials": _build_view_materials(row),
            "record_date": _as_clean_str(row.get("RecordDate")),
        })

    logger.info("orders_overview: output=%d rows (dedup_skipped=%d)", len(out), len(rows) - len(out))
    return out


def _build_validate_item_dcjmc_candidates(
    *,
    job: str,
    suffix: str,
    oper_num: str,
    material: str,
    whse: str,
    released_qty: float,
) -> List[List[str]]:
    released_value = _format_decimal(released_qty)
    raw_candidates = [
        [
            job,
            suffix,
            oper_num,
            whse,
            "1",
            released_value,
            "0",
            material,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ],
        [job, suffix, oper_num, material, whse],
        [job, suffix, oper_num, material],
    ]
    return _dedupe_candidates(raw_candidates)


def _build_validate_qty_dcjmc_candidates(
    *,
    job: str,
    suffix: str,
    material: str,
    serial_tracked: str,
    um: str,
    qty: float,
    whse: str,
) -> List[List[str]]:
    qty_value = _format_decimal(qty)
    raw_candidates = [
        [job, suffix, material, serial_tracked, um, whse, qty_value, "", "", "", "", "", ""],
        [job, suffix, material, serial_tracked, um, whse, qty_value],
        [job, suffix, material, qty_value],
    ]
    return _dedupe_candidates(raw_candidates)


def _build_process_job_matl_trans_candidates(
    *,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    material: str,
    qty: float,
    wc: str,
    location: str,
    lot: str,
) -> List[List[str]]:
    # Legacy evidence (Module_01140, AddNewItemEventHandler):
    # IteCzTsdProcessJobMatlTransDcSp(V(vJob), V(vSuffix), V(vOperNum), V(vItem), "", RV(vInfobar))
    return [[job, suffix, oper_num, material, "", ""]]


def _build_validate_lot_dcjmc_candidates(
    *,
    qty: float,
    material: str,
    location: str,
    lot: str,
    whse: str,
) -> List[List[str]]:
    qty_value = _format_decimal(qty)
    raw_candidates = [
        [qty_value, material, location, lot, whse, "", "", ""],
        [material, location, lot, whse],
        [material, lot],
        [lot],
    ]
    return _dedupe_candidates(raw_candidates)


def _build_ins_valid_vydej_mat_candidates(
    *,
    job: str,
    suffix: str,
    oper_num: str,
    job_lot: str,
    material: str,
    lot: str,
    prea_sn: str,
    qty: float,
    whse: str,
    location: str,
) -> List[List[str]]:
    qty_value = _format_decimal(qty)
    # Legacy evidence (Module_01140, ValidateVydejMatNaVpLotOrSc):
    # IteCzInsValidVydejMatNaVpLotOrScSp(
    #   V(vJob), V(vSuffix), V(vOperNum), V(vJobLot), V(vItem), V(vLot),
    #   V(vPreaSN), V(vMnozstvi), V(vCurrWhse), V(vLoc), RV(vSessionId), RV(vInfoBar)
    # )
    return [[
        job,
        suffix,
        oper_num,
        job_lot,
        material,
        lot,
        prea_sn,
        qty_value,
        whse,
        location,
        "",
        "",
    ]]


def _build_update_dcjmc_candidates(
    *,
    emp_num: str,
    job: str,
    suffix: str,
    oper_num: str,
    material: str,
    um: str,
    qty: float,
    whse: str,
    location: str,
    lot: str,
    ser_num_list: str,
    job_lot: str,
    prea_sn: str,
) -> List[List[str]]:
    qty_value = _format_decimal(qty)
    # Legacy evidence (Module_01140, ZpracovatEventHandler): 16-param deterministic signature.
    return [[
        "''",
        emp_num,
        "1",
        job,
        suffix,
        oper_num,
        material,
        um,
        whse,
        qty_value,
        location,
        lot,
        ser_num_list,
        job_lot,
        prea_sn,
        "",
    ]]


async def post_material_issue(
    infor_client,
    *,
    emp_num: str,
    job: str,
    suffix: str = "0",
    oper_num: str,
    material: str,
    um: Optional[str] = None,
    qty: float,
    wc: Optional[str] = None,
    location: Optional[str] = None,
    lot: Optional[str] = None,
) -> Dict[str, Any]:
    safe_job = (job or "").strip()
    safe_suffix = (suffix or "0").strip() or "0"
    safe_oper = (oper_num or "").strip()
    safe_material = (material or "").strip()
    safe_wc = (wc or "").strip()
    # Workshop proces používá fixní sklad/místo (MAIN/PRIJEM); lot se standardně nevyplňuje.
    safe_location = _WORKSHOP_DEFAULT_LOC
    safe_lot = ""
    safe_job_lot = ""
    safe_prea_sn = ""
    safe_ser_num_list = ""
    safe_serial_tracked = "0"
    safe_emp_num = _normalize_emp_num(emp_num) or "1"

    if not safe_job or not safe_oper or not safe_material:
        raise HTTPException(status_code=422, detail="Povinná pole: job, oper_num, material, emp_num")
    if qty <= 0:
        raise HTTPException(status_code=422, detail="Množství materiálu musí být větší než 0")

    route_result = await infor_client.load_collection(
        ido_name="SLJobRoutes",
        properties=["OperNum", "Wc", "JobQtyReleased", "QtyComplete", "QtyScrapped"],
        filter=f"{_eq_filter('Job', safe_job)} AND {_eq_filter('Suffix', safe_suffix)}",
        order_by="OperNum ASC",
        record_cap=500,
    )
    route_rows = list(route_result.get("data", []))
    route_row = next(
        (row for row in route_rows if _same_oper_num(_as_clean_str(row.get("OperNum")), safe_oper)),
        None,
    )
    route_wc = _as_clean_str(route_row.get("Wc")) if route_row is not None else None
    effective_wc = safe_wc or (route_wc or "")
    if _is_coop_wc(effective_wc):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Odvod materiálu je pro kooperaci zablokován (Wc={effective_wc}). "
                "Kooperační operace odvádějte standardním kooperačním procesem."
            ),
        )
    if route_row is not None:
        released_qty = _parse_float(route_row.get("JobQtyReleased")) or 0.0
        completed_qty = _parse_float(route_row.get("QtyComplete")) or 0.0
        scrapped_qty = _parse_float(route_row.get("QtyScrapped")) or 0.0
        if released_qty > 0 and (completed_qty + scrapped_qty) >= (released_qty - 1e-9):
            raise HTTPException(
                status_code=422,
                detail=_operation_done_error(released_qty, completed_qty, scrapped_qty),
            )

    materials = await fetch_job_materials(
        infor_client=infor_client,
        job=safe_job,
        suffix=safe_suffix,
        oper_num=safe_oper,
    )
    selected_material = next(
        (row for row in materials if (row.get("Material") or "").upper() == safe_material.upper()),
        None,
    )
    if not selected_material:
        raise HTTPException(
            status_code=404,
            detail=f"Materiál '{safe_material}' není navázán na operaci {safe_job}/{safe_suffix}/Op {safe_oper}",
        )
    available_ums = [
        (candidate or "").strip()
        for candidate in (selected_material.get("UMs") or [])
        if (candidate or "").strip()
    ]
    selected_default_um = _as_clean_str(selected_material.get("UM"))
    if selected_default_um and selected_default_um not in available_ums:
        available_ums.append(selected_default_um)

    requested_um = _as_clean_str(um)
    safe_um = selected_default_um
    if requested_um:
        match_by_upper = {candidate.upper(): candidate for candidate in available_ums}
        matched = match_by_upper.get(requested_um.upper())
        if available_ums and not matched:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Jednotka '{requested_um}' není pro materiál '{safe_material}' dostupná. "
                    f"Dostupné jednotky: {', '.join(available_ums)}."
                ),
            )
        safe_um = matched or requested_um
    elif not safe_um and available_ums:
        safe_um = available_ums[0]

    released_qty = _parse_float(selected_material.get("TotCons")) or 0.0

    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_INIT_PARMS,
        candidates=[[], [""], [safe_job, safe_suffix, safe_oper]],
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_EMP_MCHTRX,
        candidates=[[safe_wc], [safe_job], []],
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_CLM_GET_JOB_MATERIAL,
        candidates=[
            [safe_job, safe_suffix, safe_oper],
            [safe_job, safe_suffix],
            [safe_job],
            [],
        ],
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_CONTROL_BF_JOBMATL_ITEM,
        candidates=[
            [safe_job, safe_suffix, safe_oper, safe_material],
            [safe_job, safe_suffix, safe_material],
            [safe_material],
            [],
        ],
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_ITEM_DCJMC,
        candidates=_build_validate_item_dcjmc_candidates(
            job=safe_job,
            suffix=safe_suffix,
            oper_num=safe_oper,
            material=safe_material,
            whse=_WORKSHOP_DEFAULT_WHSE,
            released_qty=released_qty,
        ),
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_QTY_DCJMC,
        candidates=_build_validate_qty_dcjmc_candidates(
            job=safe_job,
            suffix=safe_suffix,
            material=safe_material,
            serial_tracked=safe_serial_tracked,
            um=safe_um or "",
            qty=qty,
            whse=_WORKSHOP_DEFAULT_WHSE,
        ),
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_LOT_DCJMC,
        candidates=_build_validate_lot_dcjmc_candidates(
            qty=qty,
            material=safe_material,
            location=safe_location,
            lot=safe_lot,
            whse=_WORKSHOP_DEFAULT_WHSE,
        ),
    )
    ins_valid_params = _build_ins_valid_vydej_mat_candidates(
        job=safe_job,
        suffix=safe_suffix,
        oper_num=safe_oper,
        job_lot=safe_job_lot,
        material=safe_material,
        lot=safe_lot,
        prea_sn=safe_prea_sn,
        qty=qty,
        whse=_WORKSHOP_DEFAULT_WHSE,
        location=safe_location,
    )[0]
    await _invoke_checked_candidates(
        infor_client,
        _WRITE_SP_INS_VALID_VYDEJ_MAT,
        candidates=[ins_valid_params],
    )
    update_dcjmc_params = _build_update_dcjmc_candidates(
        emp_num=safe_emp_num,
        job=safe_job,
        suffix=safe_suffix,
        oper_num=safe_oper,
        material=safe_material,
        um=safe_um or "",
        qty=qty,
        whse=_WORKSHOP_DEFAULT_WHSE,
        location=safe_location,
        lot=safe_lot,
        ser_num_list=safe_ser_num_list,
        job_lot=safe_job_lot,
        prea_sn=safe_prea_sn,
    )[0]
    response = await _invoke_checked_candidates(
        infor_client,
        _WRITE_SP_UPDATE_DCJMC,
        candidates=[update_dcjmc_params],
    )
    # Legacy sekvence po UpdateDcJmc: ProcessJobMatlTransDcSp (jeden deterministický pokus).
    process_candidates = _build_process_job_matl_trans_candidates(
        emp_num=safe_emp_num,
        job=safe_job,
        suffix=safe_suffix,
        oper_num=safe_oper,
        material=safe_material,
        qty=qty,
        wc=effective_wc,
        location=safe_location,
        lot=safe_lot,
    )
    process_response = await _invoke_checked(
        infor_client,
        _WRITE_SP_PROCESS_JOB_MATL_TRANS,
        process_candidates[0] if process_candidates else [],
    )

    return {
        "Job": safe_job,
        "Suffix": safe_suffix,
        "OperNum": safe_oper,
        "Material": safe_material,
        "QtyIssued": round(float(qty), 4),
        "UM": safe_um,
        "Wc": safe_wc or None,
        "Whse": _WORKSHOP_DEFAULT_WHSE,
        "Location": safe_location or None,
        "Lot": safe_lot or None,
        "Infor": response,
        "ProcessInfor": process_response,
    }


async def _build_qty_policy_context(
    tx: WorkshopTransaction,
    infor_client,
) -> Optional[Dict[str, Any]]:
    requested_complete_qty = float(tx.qty_completed or 0.0)
    requested_scrap_qty = float(tx.qty_scrapped or 0.0)
    requested_total_qty = requested_complete_qty + requested_scrap_qty

    safe_job = tx.infor_job.strip()
    safe_suffix = (tx.infor_suffix or "0").strip() or "0"
    safe_oper = tx.oper_num.strip()
    if not safe_job or not safe_oper:
        return None

    result = await infor_client.load_collection(
        ido_name="SLJobRoutes",
        properties=["OperNum", "Wc", "DerJobItem", "JobQtyReleased", "QtyComplete", "QtyScrapped"],
        filter=f"{_eq_filter('Job', safe_job)} AND {_eq_filter('Suffix', safe_suffix)}",
        order_by="OperNum ASC",
        record_cap=500,
    )
    rows = list(result.get("data", []))
    if not rows:
        return None

    current_row = next(
        (row for row in rows if _same_oper_num(_as_clean_str(row.get("OperNum")), safe_oper)),
        None,
    )
    if not current_row:
        return None

    released_qty = _parse_float(current_row.get("JobQtyReleased")) or 0.0
    completed_qty = _parse_float(current_row.get("QtyComplete")) or 0.0
    scrapped_qty = _parse_float(current_row.get("QtyScrapped")) or 0.0
    total_done_qty = completed_qty + scrapped_qty
    remaining_qty = max(0.0, released_qty - total_done_qty)
    overrun = (
        _requires_qty_validation(tx)
        and requested_total_qty > (remaining_qty + _QTY_EPSILON)
    )

    wc = tx.wc or _as_clean_str(current_row.get("Wc"))
    infor_item = tx.infor_item or _as_clean_str(
        _first_value(current_row, ("DerJobItem", "Item", "ItmItem"))
    )
    is_first_operation = _is_first_operation(safe_oper, rows)
    allow_overrun = _is_saw_wc(wc) and is_first_operation

    target_released_qty: Optional[float] = None
    if overrun and allow_overrun:
        proposed = total_done_qty + requested_total_qty
        if proposed > (released_qty + _QTY_EPSILON):
            target_released_qty = proposed

    return {
        "wc": wc,
        "infor_item": infor_item,
        "released_qty": released_qty,
        "completed_qty": completed_qty,
        "scrapped_qty": scrapped_qty,
        "operation_completed": _operation_completed_by_qty(released_qty, completed_qty, scrapped_qty),
        "remaining_qty": remaining_qty,
        "requested_qty": requested_total_qty,
        "requested_complete_qty": requested_complete_qty,
        "requested_scrap_qty": requested_scrap_qty,
        "overrun": overrun,
        "allow_overrun": allow_overrun,
        "target_released_qty": target_released_qty,
    }


async def _sync_sljobs_qty_released(
    infor_client,
    *,
    job: str,
    suffix: str,
    target_qty_released: float,
) -> None:
    if target_qty_released <= 0:
        return

    result = await infor_client.load_collection(
        ido_name="SLJobs",
        properties=["Job", "Suffix", "QtyReleased", "_ItemId"],
        filter=f"{_eq_filter('Job', job)} AND {_eq_filter('Suffix', suffix)}",
        record_cap=1,
    )
    rows = list(result.get("data", []))
    if not rows:
        raise RuntimeError(f"SLJobs row not found for {job}/{suffix}")

    row = rows[0]
    item_id = _as_clean_str(row.get("_ItemId"))
    if not item_id:
        raise RuntimeError(f"SLJobs _ItemId missing for {job}/{suffix}")

    current_qty_released = _parse_float(row.get("QtyReleased")) or 0.0
    if target_qty_released <= (current_qty_released + _QTY_EPSILON):
        return

    request = {
        "IDOName": "SLJobs",
        "RefreshAfterSave": False,
        "Changes": [
            {
                "Action": 2,  # Update
                "ItemId": item_id,
                "Properties": [
                    {
                        "Name": "QtyReleased",
                        "Value": _format_decimal(target_qty_released),
                        "Modified": True,
                    },
                ],
            }
        ],
    }

    response = await infor_client.execute_update_request(
        request_body=request,
        response_mode="summary",
    )
    msg_code = int(response.get("MessageCode", 0) or 0)
    if msg_code not in {0, 200, 210}:
        raise RuntimeError(f"SLJobs qty sync failed: {response}")


def _dcsfc_trans_type_code(trans_type: Any) -> str:
    value = trans_type.value if hasattr(trans_type, "value") else str(trans_type)
    if value == "setup_start":
        return "1"
    if value == "setup_end":
        return "2"
    if value == "start":
        return "3"
    # stop / qty_complete / scrap / time -> UkoncitPraci
    return "4"


def _parse_infor_time_seconds(value: Any) -> Optional[int]:
    """Parse Infor StartTime/EndTime value into seconds since midnight."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    text = _as_clean_str(value)
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        pass

    # Accept "HH:MM[:SS]" and timestamp tails "... HH:MM:SS".
    time_part = text
    if "T" in time_part:
        time_part = time_part.split("T")[-1]
    if " " in time_part:
        time_part = time_part.split(" ")[-1]
    hhmmss = time_part.split(":")
    if len(hhmmss) < 2:
        return None
    try:
        hours = int(hhmmss[0])
        minutes = int(hhmmss[1])
        seconds = int(float(hhmmss[2])) if len(hhmmss) > 2 else 0
        return (hours * 3600) + (minutes * 60) + seconds
    except (TypeError, ValueError):
        return None


def _expected_dcsfc_verify_markers(
    tx: WorkshopTransaction,
    trans_type: str,
) -> tuple[Optional[str], Optional[int], Optional[int]]:
    """Expected TransDate/StartTime/EndTime markers for read-after-write check."""
    date_ref: Optional[datetime]
    if trans_type in {"setup_end", "stop"}:
        date_ref = tx.finished_at or tx.started_at
    else:
        date_ref = tx.started_at or tx.finished_at

    expected_trans_date = (
        _to_workshop_local_naive(date_ref).strftime("%Y-%m-%d")
        if date_ref is not None
        else None
    )
    expected_start = _datetime_to_infor_seconds(tx.started_at)
    expected_end = _datetime_to_infor_seconds(tx.finished_at)
    return expected_trans_date, expected_start, expected_end


async def _verify_infor_write(tx: WorkshopTransaction, infor_client) -> None:
    """Read-after-write verification for near-atomic Gestima->Infor handoff.

    We mark tx as POSTED only after the expected DcSfc row is observable.
    """
    job = tx.infor_job.strip()
    oper = tx.oper_num.strip()
    tt_code = _dcsfc_trans_type_code(tx.trans_type)
    trans_type = _trans_type_value(tx.trans_type)
    expected_trans_date, expected_start, expected_end = _expected_dcsfc_verify_markers(tx, trans_type)

    if not job or not oper:
        raise RuntimeError("Write verification failed: missing job/oper context.")

    # Infor may expose the row with slight delay -> bounded retries.
    delays = [0.0, 0.35, 0.9]
    for delay in delays:
        if delay > 0:
            await asyncio.sleep(delay)

        base_filters = [
            _eq_filter("Job", job),
            f"OperNum = {oper}",
            _eq_filter("TransType", tt_code),
        ]
        filter_attempts: List[List[str]] = [list(base_filters)]
        if expected_trans_date:
            filter_attempts.insert(0, list(base_filters) + [_eq_filter("TransDate", expected_trans_date)])

        for attempt_idx, filters in enumerate(filter_attempts, start=1):
            result = await infor_client.load_collection(
                ido_name="SLDcsfcs",
                properties=["TransNum", "StartTime", "EndTime", "TransDate", "_ItemId"],
                filter=" AND ".join(filters),
                order_by="TransDate DESC, TransNum DESC",
                record_cap=8,
            )
            data_rows = result.get("data", [])
            if asyncio.iscoroutine(data_rows):
                data_rows = await data_rows
            rows = list(data_rows or [])
            if not rows:
                continue

            if attempt_idx > 1 and expected_trans_date:
                logger.warning(
                    "_verify_infor_write: fallback without TransDate for %s/%s op=%s tt=%s",
                    job,
                    tx.infor_suffix or "0",
                    oper,
                    tt_code,
                )

            for row in rows:
                row_start = _parse_infor_time_seconds(row.get("StartTime"))
                row_end = _parse_infor_time_seconds(row.get("EndTime"))
                has_start = row_start is not None
                has_end = row_end is not None

                if trans_type in {"setup_start", "start"}:
                    if not has_start:
                        continue
                    if expected_start is not None and row_start != expected_start:
                        continue
                    return

                if trans_type in {"setup_end", "stop"}:
                    if not (has_start and has_end):
                        continue
                    if expected_start is not None and row_start != expected_start:
                        continue
                    if expected_end is not None and row_end != expected_end:
                        continue
                    return

                # qty_complete / scrap / time (legacy TT=4 write) – time markers may vary by installation.
                if not (has_start or has_end):
                    continue
                if expected_start is not None and has_start and row_start != expected_start:
                    continue
                if expected_end is not None and has_end and row_end != expected_end:
                    continue
                return

    raise RuntimeError(
        f"Write verification failed: no confirmed SLDcsfcs row for {job}/{tx.infor_suffix or '0'} "
        f"op={oper} tt={tt_code} expected_date={expected_trans_date} "
        f"expected_start={expected_start} expected_end={expected_end}."
    )


def _datetime_to_infor_seconds(dt: Optional[datetime]) -> Optional[int]:
    """Convert datetime to Infor StartTime/EndTime format (seconds since midnight, CET)."""
    if dt is None:
        return None
    local_dt = _to_workshop_local_naive(dt)
    return local_dt.hour * 3600 + local_dt.minute * 60 + local_dt.second


async def _active_operation_keys_for_user(
    db: AsyncSession,
    username: str,
    exclude_tx_id: Optional[int] = None,
) -> set[tuple[str, str, str]]:
    """
    Current active runs for user, paired from START/STOP transactions.

    Uses POSTED+POSTING to avoid a race where a second START is posted while the
    first START is still POSTING (not yet POSTED).
    """
    query = select(WorkshopTransaction).where(
        WorkshopTransaction.created_by == username,
        WorkshopTransaction.trans_type.in_([
            WorkshopTransType.SETUP_START,
            WorkshopTransType.SETUP_END,
            WorkshopTransType.START,
            WorkshopTransType.STOP,
        ]),
        WorkshopTransaction.status.in_([
            WorkshopTxStatus.POSTING,
            WorkshopTxStatus.POSTED,
        ]),
        WorkshopTransaction.deleted_at.is_(None),
    )
    if exclude_tx_id is not None:
        query = query.where(WorkshopTransaction.id != exclude_tx_id)

    result = await db.execute(
        query.order_by(
            WorkshopTransaction.created_at.asc(),
            WorkshopTransaction.id.asc(),
        )
    )
    txs = _extract_workshop_transactions(result)
    stacks: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for tx in txs:
        key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
        bucket = stacks.setdefault(key, {"setup": 0, "production": 0, "wc": None})
        if not bucket["wc"] and tx.wc:
            bucket["wc"] = tx.wc
        tx_type = _trans_type_value(tx.trans_type)
        if tx_type == "setup_start":
            bucket["setup"] += 1
        elif tx_type == "start":
            bucket["production"] += 1
        elif tx_type == "setup_end":
            if bucket["setup"] > 0:
                bucket["setup"] -= 1
            elif bucket["production"] > 0:
                bucket["production"] -= 1
        elif tx_type == "stop":
            if bucket["production"] > 0:
                bucket["production"] -= 1
            elif bucket["setup"] > 0:
                bucket["setup"] -= 1

    return {
        key
        for key, bucket in stacks.items()
        if (bucket["setup"] > 0 or bucket["production"] > 0)
    }


def _extract_workshop_transactions(result: Any) -> List[WorkshopTransaction]:
    """
    SQLAlchemy may return Result or ScalarResult depending on execution path.
    Keep active-runs logic resilient to both.
    """
    if result is None:
        return []

    if hasattr(result, "scalars"):
        try:
            scalar_rows = list(result.scalars().all())
            if scalar_rows:
                return [row for row in scalar_rows if isinstance(row, WorkshopTransaction)]
            return []
        except Exception:
            pass

    if hasattr(result, "all"):
        try:
            rows = list(result.all())
        except Exception:
            rows = []
        extracted: List[WorkshopTransaction] = []
        for row in rows:
            if isinstance(row, WorkshopTransaction):
                extracted.append(row)
                continue
            if isinstance(row, (list, tuple)) and row and isinstance(row[0], WorkshopTransaction):
                extracted.append(row[0])
        return extracted

    if isinstance(result, list):
        return [row for row in result if isinstance(row, WorkshopTransaction)]

    return []


async def _active_operations_for_user(
    db: AsyncSession,
    username: str,
    exclude_tx_id: Optional[int] = None,
) -> Dict[tuple[str, str, str], Dict[str, Any]]:
    keys = await _active_operation_keys_for_user(db, username, exclude_tx_id=exclude_tx_id)
    if not keys:
        return {}

    query = select(WorkshopTransaction).where(
        WorkshopTransaction.created_by == username,
        WorkshopTransaction.trans_type.in_([
            WorkshopTransType.SETUP_START,
            WorkshopTransType.START,
        ]),
        WorkshopTransaction.status.in_([
            WorkshopTxStatus.POSTING,
            WorkshopTxStatus.POSTED,
        ]),
        WorkshopTransaction.deleted_at.is_(None),
    )
    if exclude_tx_id is not None:
        query = query.where(WorkshopTransaction.id != exclude_tx_id)

    result = await db.execute(
        query.order_by(
            WorkshopTransaction.created_at.desc(),
            WorkshopTransaction.id.desc(),
        )
    )
    txs = _extract_workshop_transactions(result)
    active: Dict[tuple[str, str, str], Dict[str, Any]] = {
        key: {"wc": None} for key in keys
    }
    for tx in txs:
        key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
        if key not in active:
            continue
        if not active[key]["wc"] and tx.wc:
            active[key]["wc"] = tx.wc
    return active


async def _ensure_start_not_duplicate_active(
    db: AsyncSession,
    tx: WorkshopTransaction,
    username: str,
) -> None:
    trans_type = _trans_type_value(tx.trans_type)
    if trans_type not in {"start", "setup_start"}:
        return

    active_keys = await _active_operation_keys_for_user(
        db,
        username,
        exclude_tx_id=getattr(tx, "id", None),
    )
    key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
    if key in active_keys:
        raise RuntimeError(
            f"Operace {tx.infor_job}/{tx.infor_suffix or '0'} op {tx.oper_num} je již spuštěná. "
            "Nejprve ji ukončete."
        )


async def _resolve_ukoncit_stroj_flag(
    db: AsyncSession,
    tx: WorkshopTransaction,
    username: str,
) -> str:
    trans_type = _trans_type_value(tx.trans_type)
    if trans_type != "stop":
        return "0"

    # Explicit override from payload (if available).
    explicit = _as_clean_str(getattr(tx, "ukoncit_stroj_flag", None))
    if explicit is not None:
        return _normalize_bool_flag(explicit, default="1")

    active = await _active_operations_for_user(
        db,
        username,
        exclude_tx_id=getattr(tx, "id", None),
    )
    key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
    current_wc = (_as_clean_str(tx.wc) or "").upper()
    other_ops = [
        (other_key, meta)
        for other_key, meta in active.items()
        if other_key != key
    ]
    if not other_ops:
        return "1"

    # If we cannot safely determine machine context, prefer keeping machine running.
    if not current_wc:
        return "0"
    for _, meta in other_ops:
        other_wc = (_as_clean_str(meta.get("wc")) or "").upper()
        if not other_wc or other_wc == current_wc:
            return "0"
    return "1"


async def _resolve_multi_job_flag(
    db: AsyncSession,
    tx: WorkshopTransaction,
    username: str,
) -> str:
    explicit = _as_clean_str(getattr(tx, "multi_job_flag", None))
    if explicit:
        return _normalize_multi_job_flag(explicit)
    # InduStream behavior (from IL-verified DLL analysis):
    # First job on machine → "0", subsequent jobs → "1".
    # InduStream tracks this as runtime V(vMultiJobFlag) state on the form.
    # Gestima infers from local active-operation stack.
    trans_type = _trans_type_value(tx.trans_type)
    if trans_type in {"stop", "setup_end"}:
        # At stop time, flag describes whether OTHER jobs remain active.
        active_keys = await _active_operation_keys_for_user(
            db, username, exclude_tx_id=getattr(tx, "id", None),
        )
        current_key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
        other_active = {k for k in active_keys if k != current_key}
        return "1" if other_active else "0"
    else:
        # At start time, flag describes whether ANYTHING is already running.
        active_keys = await _active_operation_keys_for_user(
            db, username, exclude_tx_id=getattr(tx, "id", None),
        )
        return "1" if active_keys else "0"


def _build_validate_multi_job_candidates(
    tx: WorkshopTransaction,
    emp_num: str,
    multi_job_flag: str,
) -> List[List[str]]:
    suffix = tx.infor_suffix or "0"
    raw_candidates = [
        [emp_num, multi_job_flag, tx.infor_job, suffix, tx.oper_num, ""],
        [emp_num, multi_job_flag, tx.infor_job, suffix, tx.oper_num],
        [emp_num, multi_job_flag, tx.infor_job, suffix],
        [multi_job_flag],
        [],
    ]
    return _dedupe_candidates(raw_candidates)


async def create_transaction(
    db: AsyncSession,
    data: WorkshopTransactionCreate,
    current_user: User,
) -> WorkshopTransaction:
    """Uloží dílnickou transakci do lokálního bufferu."""
    tx = WorkshopTransaction(
        infor_job=data.infor_job,
        infor_suffix=data.infor_suffix,
        infor_item=data.infor_item,
        oper_num=data.oper_num,
        wc=data.wc,
        trans_type=data.trans_type,
        qty_completed=data.qty_completed,
        qty_scrapped=data.qty_scrapped,
        qty_moved=data.qty_moved,
        scrap_reason=data.scrap_reason,
        actual_hours=data.actual_hours,
        oper_complete=data.oper_complete,
        job_complete=data.job_complete,
        started_at=data.started_at,
        finished_at=data.finished_at,
        status=WorkshopTxStatus.PENDING,
    )
    set_audit(tx, current_user.username)
    db.add(tx)
    await safe_commit(db, tx, "vytvoření dílnické transakce")
    logger.info(
        "Workshop transaction created: job=%s oper=%s type=%s by=%s",
        data.infor_job,
        data.oper_num,
        data.trans_type,
        current_user.username,
    )
    return tx


async def post_transaction_to_infor(
    db: AsyncSession,
    tx_id: int,
    infor_client,
    current_user: User,
) -> WorkshopTransaction:
    """Odešle lokální workshop transakci do Inforu podle trans_type."""
    result = await db.execute(
        select(WorkshopTransaction).where(
            WorkshopTransaction.id == tx_id,
            WorkshopTransaction.deleted_at.is_(None),
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transakce nenalezena")

    if tx.status not in (WorkshopTxStatus.PENDING, WorkshopTxStatus.FAILED):
        raise HTTPException(
            status_code=409,
            detail=f"Transakci nelze odeslat — aktuální status: {tx.status}",
        )

    tx.status = WorkshopTxStatus.POSTING
    set_audit(tx, current_user.username, is_update=True)
    await safe_commit(db, tx, "nastavení posting statusu")

    emp_num = resolve_infor_emp_num(current_user)
    trans_type = tx.trans_type.value if hasattr(tx.trans_type, "value") else str(tx.trans_type)
    qty_policy_context: Optional[Dict[str, Any]] = None
    multi_job_flag = "0"
    ukoncit_stroj_flag = "0"
    write_phase_started = False

    try:
        qty_policy_context = await _build_qty_policy_context(tx, infor_client)
        if qty_policy_context:
            if not tx.wc and qty_policy_context.get("wc"):
                tx.wc = _as_clean_str(qty_policy_context.get("wc"))
            if not tx.infor_item and qty_policy_context.get("infor_item"):
                tx.infor_item = _as_clean_str(qty_policy_context.get("infor_item"))

        if qty_policy_context and qty_policy_context.get("operation_completed"):
            raise RuntimeError(
                _operation_done_error(
                    float(qty_policy_context.get("released_qty") or 0.0),
                    float(qty_policy_context.get("completed_qty") or 0.0),
                    float(qty_policy_context.get("scrapped_qty") or 0.0),
                )
            )

        if (
            qty_policy_context
            and qty_policy_context.get("overrun")
            and not qty_policy_context.get("allow_overrun")
        ):
            raise RuntimeError(
                _overrun_block_error(
                    float(qty_policy_context.get("remaining_qty") or 0.0),
                    float(qty_policy_context.get("requested_qty") or 0.0),
                )
            )

        await _ensure_start_not_duplicate_active(db, tx, current_user.username)

        multi_job_flag = await _resolve_multi_job_flag(db, tx, current_user.username)
        setattr(tx, "multi_job_flag", multi_job_flag)
        if trans_type == "stop":
            ukoncit_stroj_flag = await _resolve_ukoncit_stroj_flag(db, tx, current_user.username)
            setattr(tx, "ukoncit_stroj_flag", ukoncit_stroj_flag == "1")

        logger.info(
            "Posting workshop tx=%s type=%s job=%s/%s oper=%s wc=%s item=%s multi_job=%s ukoncit_stroj=%s",
            tx.id,
            trans_type,
            tx.infor_job,
            tx.infor_suffix or "0",
            tx.oper_num,
            tx.wc,
            tx.infor_item,
            multi_job_flag,
            ukoncit_stroj_flag,
        )

        await _invoke_nonfatal_candidates(
            infor_client,
            _WRITE_SP_VALIDATE_MULTI_JOB,
            candidates=_build_validate_multi_job_candidates(tx, emp_num, multi_job_flag),
        )

        # Recalculate actual_hours on backend from naive-UTC timestamps.
        # Frontend calculation is unreliable (timezone parsing issues with
        # new Date(isoString) in CET/CEST browser environments).
        if trans_type in {"stop", "setup_end"} and tx.started_at and tx.finished_at:
            delta = tx.finished_at - tx.started_at
            tx.actual_hours = round(delta.total_seconds() / 3600, 4)

        write_phase_started = True
        if trans_type in {"setup_start", "setup_end", "start"}:
            await _post_wrapper_flow(tx, infor_client, emp_num)
        elif trans_type == "stop":
            await _post_stop_flow(tx, infor_client, emp_num)
        else:
            await _post_sfc34_flow(tx, infor_client, emp_num)

        if (
            qty_policy_context
            and qty_policy_context.get("overrun")
            and qty_policy_context.get("allow_overrun")
            and qty_policy_context.get("target_released_qty") is not None
        ):
            target_qty_released = float(qty_policy_context["target_released_qty"])
            try:
                await _sync_sljobs_qty_released(
                    infor_client,
                    job=tx.infor_job.strip(),
                    suffix=(tx.infor_suffix or "0").strip() or "0",
                    target_qty_released=target_qty_released,
                )
                logger.info(
                    "QtyReleased synchronized after saw overrun: %s/%s -> %.3f",
                    tx.infor_job,
                    tx.infor_suffix or "0",
                    target_qty_released,
                )
            except Exception as sync_exc:
                logger.warning(
                    "Posted tx %s but QtyReleased sync failed for %s/%s: %s",
                    tx_id,
                    tx.infor_job,
                    tx.infor_suffix or "0",
                    sync_exc,
                )

        # Verify DcSfc record exists in Infor before marking POSTED.
        await _verify_infor_write(tx, infor_client)

        tx.status = WorkshopTxStatus.POSTED
        tx.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        tx.error_msg = None
        logger.info("Transaction %s posted to Infor successfully", tx_id)
    except Exception as exc:
        recovered = False
        if write_phase_started and not isinstance(exc, _NonRecoverablePostError):
            try:
                # Recovery path: if the main DcSfc SP succeeded but a subsequent
                # non-critical step (KapacityUpdate, Mchtrx) failed, check if the
                # DcSfc record exists in Infor.  Existence = POSTED.
                await _verify_infor_write(tx, infor_client)
                tx.status = WorkshopTxStatus.POSTED
                tx.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                tx.error_msg = None
                recovered = True
                logger.warning(
                    "Transaction %s recovered as POSTED after post-path error: %s",
                    tx_id,
                    exc,
                )
            except Exception:
                recovered = False

        if not recovered:
            tx.status = WorkshopTxStatus.FAILED
            tx.error_msg = str(exc)[:500]
            logger.error("Transaction %s failed to post: %s", tx_id, exc)

    set_audit(tx, current_user.username, is_update=True)
    await safe_commit(db, tx, "aktualizace statusu transakce")
    return tx


async def _post_wrapper_flow(tx: WorkshopTransaction, infor_client, emp_num: str) -> None:
    """Post start/setup flows — rewritten to match InduStream IL exactly.

    InduStream verified flows (from VB$StateMachine IL analysis):

    ZahajitPraci (start, TT=3):
      1. ValidateOperNumMachineSp  → captures RV(vOldEmpNum, vStroj, vWc)
      2. WrapperSp(TT=3)
      3. KapacityUpdateSp
      4. UpdateMchtrxSp(mode="H") → uses captured vOldEmpNum, vStroj, vWc

    ZahajitNastaveni (setup_start, TT=1):
      1. WrapperSp(TT=1)
      (no ValidateOperNumMachine, no UpdateMchtrx)

    UkoncitNastaveni (setup_end, TT=2):
      1. WrapperSp(TT=2)
      2. (conditional) WrapperSp(TT=3) if vZahajitPraciFlag — not implemented
      3. ValidateOperNumMachineSp → captures RV
      4. UpdateMchtrxSp(mode="H") → uses captured RV
    """
    trans_type = _trans_type_value(tx.trans_type)

    # Refresh Infor server context (date/time) — required for REST API.
    # InduStream gets this from persistent COM session; our REST calls are stateless.
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_INIT_PARMS,
        candidates=[[], [""], [tx.infor_job, tx.infor_suffix or "0", tx.oper_num]],
    )

    if trans_type == "start":
        # === InduStream ZahajitPraci flow (IL-verified) ===

        # Step 1: ValidateOperNumMachineSp — capture RV outputs
        await _validate_oper_machine_and_capture(tx, infor_client, emp_num)

        # Step 2: WrapperSp(TT=3)
        await _invoke_checked(
            infor_client,
            _WRITE_SP_WRAPPER,
            _build_wrapper_params(tx, emp_num),
        )

        # Step 3: KapacityUpdateSp
        await _invoke_nonfatal_candidates(
            infor_client,
            _WRITE_SP_KAPACITY_UPDATE,
            candidates=[_build_kapacity_update_params(tx)],
        )

        # Step 4: UpdateMchtrxSp(mode="H") — uses captured vOldEmpNum, vStroj, vWc
        await _invoke_checked(
            infor_client,
            _WRITE_SP_MCHTRX,
            _build_mchtrx_candidates(tx, emp_num, mode="H")[0],
        )

    elif trans_type == "setup_start":
        # === InduStream ZahajitNastaveni flow (IL-verified) ===
        # Only WrapperSp(TT=1), no validate, no mchtrx.
        await _invoke_checked(
            infor_client,
            _WRITE_SP_WRAPPER,
            _build_wrapper_params(tx, emp_num),
        )

    elif trans_type == "setup_end":
        # === InduStream UkoncitNastaveni flow (IL-verified) ===

        # Step 1: WrapperSp(TT=2)
        await _invoke_checked(
            infor_client,
            _WRITE_SP_WRAPPER,
            _build_wrapper_params(tx, emp_num),
        )

        # Step 2: ValidateOperNumMachineSp — capture RV outputs
        await _validate_oper_machine_and_capture(tx, infor_client, emp_num)

        # Step 3: UpdateMchtrxSp(mode="H") — uses captured vOldEmpNum, vStroj, vWc
        await _invoke_checked(
            infor_client,
            _WRITE_SP_MCHTRX,
            _build_mchtrx_candidates(tx, emp_num, mode="H")[0],
        )



async def _validate_oper_machine_and_capture(
    tx: WorkshopTransaction,
    infor_client,
    emp_num: str,
) -> None:
    """Call ValidateOperNumMachineSp and capture RV output values onto tx.

    InduStream IL signature (11 params):
      V(vJob), V(vSuffix), V(vOperNum), V(vEmpNum), "H",
      V(vItem), V(vWhse),
      RV(vOldEmpNum),   # index 7
      RV(vStroj),       # index 8
      RV(vWc),          # index 9
      RV(vInfoBar)      # index 10

    The captured values are stored as tx dynamic attributes and used by
    _build_mchtrx_candidates for the subsequent UpdateMchtrxSp call.
    """
    try:
        response = await _invoke_checked_candidates(
            infor_client,
            _WRITE_SP_VALIDATE_OPER_MACHINE,
            candidates=[_build_validate_oper_machine_params(tx, emp_num)],
            allow_nonzero_return=True,
        )
        rv = _extract_rv_from_response(response, {
            "old_emp_num": 7,
            "stroj": 8,
            "wc": 9,
        })
        if rv.get("old_emp_num"):
            setattr(tx, "old_emp_num", rv["old_emp_num"])
            logger.info("ValidateOperNumMachine: captured vOldEmpNum=%s", rv["old_emp_num"])
        if rv.get("stroj"):
            setattr(tx, "stroj", rv["stroj"])
            logger.info("ValidateOperNumMachine: captured vStroj=%s", rv["stroj"])
        if rv.get("wc") and not tx.wc:
            tx.wc = rv["wc"]
            logger.info("ValidateOperNumMachine: captured vWc=%s", rv["wc"])
    except Exception as exc:
        logger.warning(
            "ValidateOperNumMachineSp failed (non-fatal for write flow): %s", exc,
        )


async def _post_stop_flow(tx: WorkshopTransaction, infor_client, emp_num: str) -> None:
    """Post stop flow — rewritten to match InduStream UkoncitPraci IL exactly.

    InduStream verified flow (VB$StateMachine_225_UkoncitPraciEventHandler):
      1. IteCzInsWrapperDcsfcUpdateSp (27 params, TT=4) — CRITICAL: creates DcSfc TT=4
      2. IteCzTsdKapacityUpdateSp (3 params)
      3. IteCzTsdUpdateDcSfcMchtrxSp (22 params) — machine stop

    Gestima addition (not in InduStream but necessary for REST API integration):
      - InitParmsSp: refreshes Infor server context (nonfatal)
    """
    # Pre-step: refresh Infor server context (best-effort).
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_INIT_PARMS,
        candidates=[[], [""], [tx.infor_job, tx.infor_suffix or "0", tx.oper_num]],
    )

    # Step 1 (IL-verified): InsWrapperDcsfcUpdateSp — creates DcSfc TT=4.
    # This is the CRITICAL write — if it succeeds, the labor record exists in Infor.
    await _invoke_checked(
        infor_client,
        _WRITE_SP_INS_WRAPPER_DCSFC_UPDATE,
        _build_ins_wrapper_dcsfc_update_params(tx, emp_num),
    )

    # Step 2 (IL-verified): KapacityUpdateSp
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_KAPACITY_UPDATE,
        candidates=[_build_kapacity_update_params(tx)],
    )

    # Step 3 (IL-verified): UpdateDcSfcMchtrxSp — machine stop.
    # If this fails, the DcSfc labor record (step 1) already exists in Infor.
    # Do NOT raise _NonRecoverablePostError — the labor write is valid.
    try:
        await _invoke_checked_candidates(
            infor_client,
            _WRITE_SP_DCSFC_MCHTRX,
            _build_dcsfc_mchtrx_candidates(tx, emp_num),
        )
    except Exception as exc:
        logger.warning(
            "STOP machine step via %s failed, trying legacy %s fallback: %s",
            _WRITE_SP_DCSFC_MCHTRX,
            _WRITE_SP_MCHTRX,
            exc,
        )
        try:
            await _invoke_checked_candidates(
                infor_client,
                _WRITE_SP_MCHTRX,
                _build_mchtrx_stop_candidates(tx, emp_num),
            )
        except Exception as fallback_exc:
            # DcSfc TT=4 was already created in step 1 — labor record exists in Infor.
            # Machine-stop failure is NOT a reason to mark the whole transaction as
            # non-recoverable.  The verify step will find the DcSfc record and
            # recover the transaction to POSTED status.
            logger.error(
                "STOP machine step failed after DcSfc TT=4 was written. "
                "Labor record exists in Infor but machine state may be inconsistent. "
                "%s | fallback %s: %s",
                exc,
                _WRITE_SP_MCHTRX,
                fallback_exc,
            )


async def _post_sfc34_flow(tx: WorkshopTransaction, infor_client, emp_num: str) -> None:
    params = _build_sfc34_params(tx, emp_num)
    await _invoke_checked(infor_client, _WRITE_SP_SFC34, params)


async def list_my_transactions(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
) -> List[WorkshopTransaction]:
    """Vrátí transakce aktuálně přihlášeného uživatele."""
    result = await db.execute(
        select(WorkshopTransaction)
        .where(
            WorkshopTransaction.created_by == current_user.username,
            WorkshopTransaction.deleted_at.is_(None),
        )
        .order_by(WorkshopTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


def _trans_type_code_wrapper(trans_type: Any) -> str:
    value = trans_type.value if hasattr(trans_type, "value") else str(trans_type)
    mapping = {
        "setup_start": "1",
        "setup_end": "2",
        "start": "3",
        "stop": "4",
    }
    return mapping.get(value, "3")


def _source_module_for_wrapper(trans_type: str) -> str:
    source_map = {
        "setup_start": "01110",
        "setup_end": "01111",
        "start": "01100",
        "stop": "01101",
    }
    return source_map.get(trans_type, "01120")


def _tx_dynamic_str(tx: WorkshopTransaction, *names: str) -> str:
    for name in names:
        value = _as_clean_str(getattr(tx, name, None))
        if value:
            return value
    return ""


def _build_validate_oper_machine_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    whse_value = _tx_dynamic_str(tx, "whse", "warehouse") or _WORKSHOP_DEFAULT_WHSE
    return [
        tx.infor_job,
        tx.infor_suffix or "0",
        tx.oper_num,
        emp_num,
        "H",
        tx.infor_item or "",
        whse_value,
        "",
        "",
        "",
        "",
    ]


def _build_validate_emp_mchtrx_candidates(tx: WorkshopTransaction, emp_num: str) -> List[List[str]]:
    wc_value = _tx_dynamic_str(tx, "wc", "v_wc", "vWc")
    machine_value = _tx_dynamic_str(
        tx,
        "stroj",
        "v_stroj",
        "vStroj",
        "machine_id",
        "id_machine",
    ) or wc_value
    return _dedupe_candidates([
        [emp_num, machine_value],
        [machine_value, emp_num],
        [emp_num, wc_value],
        [wc_value, emp_num],
        [emp_num, tx.infor_job],
        [tx.infor_job, emp_num],
        [emp_num],
        [machine_value],
        [wc_value],
        [tx.infor_job],
        [],
    ])


def _build_kapacity_update_params(tx: WorkshopTransaction) -> List[str]:
    ptr_value = _tx_dynamic_str(tx, "ptr_kapacity", "kapacity_ptr", "v_ptr_kapacity")
    return ["J", ptr_value, ""]


def _build_wrapper_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    trans_type = _trans_type_value(tx.trans_type)
    trans_code = _trans_type_code_wrapper(tx.trans_type)
    source_module = _source_module_for_wrapper(trans_type)
    id_machine = _tx_dynamic_str(tx, "id_machine", "machine_id", "gv_id_machine")
    res_id = _tx_dynamic_str(tx, "res_id", "resource_id", "gv_res_id")
    mode_value = _tx_dynamic_str(tx, "mode", "trans_mode") or "T"
    multi_job_flag = _normalize_multi_job_flag(
        _tx_dynamic_str(tx, "multi_job_flag", "v_multi_job_flag")
    )

    base_25 = [
        "",  # 0
        emp_num,  # 1 V(vEmpNum)
        multi_job_flag,  # 2 V(vMultiJobFlag)
        trans_code,  # 3 TransType (1/2/3)
        tx.infor_job,  # 4 V(vJob)
        tx.infor_suffix or "0",  # 5 V(vSuffix)
        tx.oper_num,  # 6 V(vOperNum)
        "",  # 7
        "",  # 8
        "",  # 9
        "0",  # 10 V(vOperCompleteFlag)
        "0",  # 11 V(vJobCompleteFlag)
        "0",  # 12 V(vIssueParentFlag)
        "",  # 13 V(vLoc)
        "",  # 14 V(vLot)
        "",  # 15 V(vReasonCode)
        "",  # 16 V(vSerNumList)
        "",  # 17
        "",  # 18
        source_module,  # 19 V(vSourceModul)
        id_machine,  # 20 G(gvIdMachine)
        res_id,  # 21 G(gvResid)
        "0",  # 22
        mode_value,  # 23 V(vMode)
        "",  # 24 RV(vInfoBar)
    ]
    if trans_type == "start":
        batch_value = _tx_dynamic_str(tx, "batch_kapacity", "v_batch_kapacity")
        return base_25 + ["", "", "", "", "", "", batch_value]
    return base_25


def _build_wrapper_candidates(tx: WorkshopTransaction, emp_num: str) -> List[List[str]]:
    base = _build_wrapper_params(tx, emp_num)
    return [base]

def _dedupe_candidates(candidates: Sequence[Sequence[str]]) -> List[List[str]]:
    seen: set[tuple[str, ...]] = set()
    out: List[List[str]] = []
    for candidate in candidates:
        key = tuple(candidate)
        if key in seen:
            continue
        seen.add(key)
        out.append(list(candidate))
    return out


def _build_mchtrx_candidates(tx: WorkshopTransaction, emp_num: str, mode: str) -> List[List[str]]:
    wc_value = _tx_dynamic_str(tx, "wc", "v_wc", "vWc")
    suffix = tx.infor_suffix or "0"
    # stroj + old_emp_num: populated by _validate_oper_machine_and_capture()
    # from ValidateOperNumMachineSp RV outputs (indices 8, 7).
    # Fallback: stroj→wc, old_emp_num→emp_num (self-handoff).
    stroj_value = _tx_dynamic_str(tx, "stroj", "v_stroj", "vStroj", "machine_id", "id_machine") or wc_value
    old_emp_num = _tx_dynamic_str(tx, "old_emp_num", "v_old_emp_num", "vOldEmpNum") or emp_num
    # IL-verified 9-param signature (InduStream UpdateMchtrxSp):
    # [V(vEmpNum), Mode, V(vJob), V(vSuffix), V(vOperNum), V(vWc), V(vStroj), V(vOldEmpNum), RV(vInfoBar)]
    return [[
        emp_num,
        mode,
        tx.infor_job,
        suffix,
        tx.oper_num,
        wc_value,
        stroj_value,
        old_emp_num,
        "",
    ]]


def _build_mchtrx_stop_candidates(tx: WorkshopTransaction, emp_num: str) -> List[List[str]]:
    wc_value = _tx_dynamic_str(tx, "wc", "v_wc", "vWc")
    suffix = tx.infor_suffix or "0"
    stroj_value = _tx_dynamic_str(
        tx,
        "stroj",
        "v_stroj",
        "vStroj",
        "machine_id",
        "id_machine",
    ) or wc_value
    old_emp_num = _tx_dynamic_str(tx, "old_emp_num", "v_old_emp_num", "vOldEmpNum") or emp_num
    return _dedupe_candidates([
        [emp_num, "J", tx.infor_job, suffix, tx.oper_num, wc_value, stroj_value, old_emp_num, ""],
        [emp_num, "J", tx.infor_job, suffix, tx.oper_num, wc_value, wc_value, emp_num, ""],
        [emp_num, "J", tx.infor_job, suffix, tx.oper_num, wc_value, stroj_value, "", ""],
        [emp_num, "J", tx.infor_job, suffix, tx.oper_num, wc_value, "", old_emp_num, ""],
        [emp_num, "J", tx.infor_job, suffix, tx.oper_num, wc_value, "", "", ""],
    ])


def _build_ins_wrapper_dcsfc_update_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    source_module = _source_module_for_wrapper("stop")
    id_machine = _tx_dynamic_str(tx, "id_machine", "machine_id", "gv_id_machine")
    res_id = _tx_dynamic_str(tx, "res_id", "resource_id", "gv_res_id")
    mode_value = _tx_dynamic_str(tx, "mode", "trans_mode") or "T"
    multi_job_flag = _normalize_multi_job_flag(
        _tx_dynamic_str(tx, "multi_job_flag", "v_multi_job_flag")
    )
    issue_parent_flag = _bool_to_flag(bool(getattr(tx, "issue_parent", False)))
    ser_num_list = _tx_dynamic_str(tx, "ser_num_list")
    return [
        "1",
        "",
        emp_num,
        multi_job_flag,
        "4",
        tx.infor_job,
        tx.infor_suffix or "0",
        tx.oper_num,
        _format_decimal(tx.qty_completed),
        _format_decimal(tx.qty_scrapped),
        _format_decimal(tx.qty_moved),
        _bool_to_flag(tx.oper_complete),
        _bool_to_flag(tx.job_complete),
        issue_parent_flag,
        _tx_dynamic_str(tx, "loc", "location"),
        _tx_dynamic_str(tx, "lot"),
        tx.scrap_reason or "",
        "0",
        ser_num_list,
        "",
        "",
        source_module,
        id_machine,
        res_id,
        "0",
        mode_value,
        "",
    ]


def _build_dcsfc_mchtrx_candidates(tx: WorkshopTransaction, emp_num: str) -> List[List[str]]:
    suffix = tx.infor_suffix or "0"
    item_value = tx.infor_item or ""
    whse_value = _tx_dynamic_str(tx, "whse", "warehouse") or _WORKSHOP_DEFAULT_WHSE
    issue_parent_flag = _bool_to_flag(bool(getattr(tx, "issue_parent", False)))
    ukoncit_stroj_flag = _normalize_bool_flag(
        _tx_dynamic_str(tx, "ukoncit_stroj_flag"),
        default="1",
    )
    ser_num_list = _tx_dynamic_str(tx, "ser_num_list")
    multi_job_flag = _normalize_multi_job_flag(
        _tx_dynamic_str(tx, "multi_job_flag", "v_multi_job_flag")
    )
    qty_comp = _format_decimal(tx.qty_completed)
    qty_scrap = _format_decimal(tx.qty_scrapped)
    qty_move = _format_decimal(tx.qty_moved)
    loc_value = _tx_dynamic_str(tx, "loc", "location")
    lot_value = _tx_dynamic_str(tx, "lot")
    reason_value = tx.scrap_reason or ""

    def _candidate(
        trans_code: str,
        *,
        item: str,
        whse: str,
        multi_job: str,
        qty_complete_value: str,
        qty_scrap_value: str,
        qty_move_value: str,
    ) -> List[str]:
        return [
            "",
            emp_num,
            multi_job,
            trans_code,
            tx.infor_job,
            suffix,
            tx.oper_num,
            item,
            whse,
            qty_complete_value,
            qty_scrap_value,
            qty_move_value,
            _bool_to_flag(tx.oper_complete),
            _bool_to_flag(tx.job_complete),
            issue_parent_flag,
            loc_value,
            lot_value,
            reason_value,
            ser_num_list,
            "",
            ukoncit_stroj_flag,
            "",
        ]

    # Canonical IL candidate first, then tenant-compatibility fallbacks.
    # Some installations return SP error 16 for strict combinations.
    item_fallback = "0"
    qty_variants: List[tuple[str, str, str]] = [(qty_comp, qty_scrap, qty_move)]
    if qty_comp == "0.00000000" and qty_scrap == "0.00000000" and qty_move == "0.00000000":
        qty_variants.append(("", "", ""))

    canonical = [
        _candidate(
            "J",
            item=item_value,
            whse=whse_value,
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "1",
            item=item_value,
            whse=whse_value,
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "J",
            item=item_fallback,
            whse=whse_value,
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "1",
            item=item_fallback,
            whse=whse_value,
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "J",
            item=item_value,
            whse="",
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "J",
            item=item_fallback,
            whse="",
            multi_job=multi_job_flag,
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "J",
            item=item_value,
            whse=whse_value,
            multi_job="0",
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
        _candidate(
            "J",
            item=item_fallback,
            whse=whse_value,
            multi_job="0",
            qty_complete_value=qty_comp,
            qty_scrap_value=qty_scrap,
            qty_move_value=qty_move,
        ),
    ]

    generated: List[List[str]] = []
    multi_job_candidates = [multi_job_flag]
    if multi_job_flag != "0":
        multi_job_candidates.append("0")
    for trans_code in ("J", "1"):
        for item_candidate in (item_value, item_fallback):
            for whse_candidate in (whse_value, ""):
                for multi_job_candidate in multi_job_candidates:
                    for qty_complete_value, qty_scrap_value, qty_move_value in qty_variants:
                        generated.append(
                            _candidate(
                                trans_code,
                                item=item_candidate,
                                whse=whse_candidate,
                                multi_job=multi_job_candidate,
                                qty_complete_value=qty_complete_value,
                                qty_scrap_value=qty_scrap_value,
                                qty_move_value=qty_move_value,
                            )
                        )
    return _dedupe_candidates(canonical + generated)


def _build_sfc34_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    actual_hours = tx.actual_hours
    if actual_hours is None and tx.started_at and tx.finished_at:
        delta = tx.finished_at - tx.started_at
        actual_hours = round(delta.total_seconds() / 3600, 4)

    tx_date = _format_infor_datetime(tx.finished_at)

    return [
        emp_num,  # 0 @TEmpNum
        "",  # 1 must stay empty
        tx.infor_job,  # 2 @TJobNum
        tx.infor_suffix or "0",  # 3 @TJobSuffix
        tx.oper_num,  # 4 @TOperNum
        str(tx.qty_completed or 0),  # 5 @QtyComp
        str(tx.qty_scrapped or 0),  # 6 @QtyScrap
        str(tx.qty_moved or 0),  # 7 @QtyMove
        str(actual_hours or 0),  # 8 @Hours
        _bool_to_flag(tx.oper_complete),  # 9 @Complete
        _bool_to_flag(tx.job_complete),  # 10 @Close
        "0",  # 11 @IssueParent
        "",  # 12 @Location
        "",  # 13 @Lot
        tx.scrap_reason or "",  # 14 @ReasonCode
        "",  # 15 @SerNumList
        tx.wc or "",  # 16 @Wc
        "",  # 17 @Infobar OUT
        "",  # 18 @Stroj
        tx_date,  # 19 @DatumTransakce (empty -> Infor server datetime)
    ]


# ============================================================================
# DB-read funkce — čtení z lokální SQLite DB (< 10ms)
# ============================================================================

async def read_wc_queue_from_db(
    db: AsyncSession,
    wc: Optional[str] = None,
    job_filter: Optional[str] = None,
    sort_by: str = "OpDatumSt",
    sort_dir: str = "asc",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Načte frontu z lokální tabulky workshop_job_routes (job_stat='R')."""
    from app.models.workshop_job_route import WorkshopJobRoute

    query = select(WorkshopJobRoute).where(
        WorkshopJobRoute.deleted_at.is_(None),
        WorkshopJobRoute.job_stat == "R",
    )
    if wc:
        query = query.where(WorkshopJobRoute.wc == wc.strip())

    result = await db.execute(query)
    entries = result.scalars().all()

    rows = [_wjr_to_queue_dict(e) for e in entries]
    rows = [r for r in rows if not _is_operation_completed_row(r)]

    # Filtr
    if job_filter:
        jf = job_filter.strip().upper()
        rows = [r for r in rows if jf in (r.get("Job", "").upper())]

    rows = sort_queue(rows, sort_by=sort_by, sort_dir=sort_dir)
    return rows[:limit]


async def read_machine_plan_from_db(
    db: AsyncSession,
    wc: Optional[str] = None,
    job_filter: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "OpDatumSt",
    sort_dir: str = "asc",
    record_cap: int = 500,
) -> List[Dict[str, Any]]:
    """Načte plán stroje z DB: released (R) + backlog (F/S/W).

    Args:
        search: Fulltextové hledání v Job + DerJobItem + JobDescription (case-insensitive).
                Má přednost před job_filter.
    """
    from app.models.workshop_job_route import WorkshopJobRoute

    query = select(WorkshopJobRoute).where(
        WorkshopJobRoute.deleted_at.is_(None),
        WorkshopJobRoute.job_stat.in_(["R", "F", "S", "W"]),
    )
    if wc:
        query = query.where(WorkshopJobRoute.wc == wc.strip())

    result = await db.execute(query)
    entries = result.scalars().all()

    rows: List[Dict[str, Any]] = []
    for e in entries:
        d = _wjr_to_queue_dict(e)
        d["JobStat"] = e.job_stat or "R"
        # Filtr completed operací
        if _is_operation_completed_row(d):
            continue
        rows.append(d)

    if search:
        s = search.strip().upper()
        rows = [
            r for r in rows
            if s in (r.get("Job", "") or "").upper()
            or s in (r.get("DerJobItem", "") or "").upper()
            or s in (r.get("JobDescription", "") or "").upper()
        ]
    elif job_filter:
        jf = job_filter.strip().upper()
        rows = [r for r in rows if jf in (r.get("Job", "").upper())]

    rows = sort_queue(rows, sort_by=sort_by, sort_dir=sort_dir)
    return rows[:record_cap]


async def enrich_orders_with_tier(
    db: AsyncSession, orders: List[Dict[str, Any]]
) -> None:
    """Doplní tier z production_priorities do orders overview řádků."""
    from app.models.production_priority import ProductionPriority
    from app.services.production_planner_service import _derive_tier

    all_jobs: set[str] = set()
    for order in orders:
        svj = order.get("selected_vp_job")
        if svj:
            all_jobs.add(svj.strip().upper())
        for vp in order.get("vp_candidates", []):
            j = vp.get("job")
            if j:
                all_jobs.add(j.strip().upper())
    if not all_jobs:
        return

    prio_result = await db.execute(
        select(ProductionPriority).where(
            ProductionPriority.deleted_at.is_(None),
            ProductionPriority.infor_job.in_(list(all_jobs)),
        )
    )
    tier_map: Dict[str, str] = {}
    for pp in prio_result.scalars().all():
        tier_map[pp.infor_job] = _derive_tier(pp.priority, pp.is_hot)

    for order in orders:
        for vp in order.get("vp_candidates", []):
            job_upper = (vp.get("job") or "").strip().upper()
            vp["tier"] = tier_map.get(job_upper, "normal")
        svj = order.get("selected_vp_job")
        if svj:
            order["tier"] = tier_map.get(svj.strip().upper(), "normal")


async def read_orders_overview_from_db(
    db: AsyncSession,
    customer: Optional[str] = None,
    due_from: Optional[str] = None,
    due_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """Načte přehled zakázek z lokální tabulky workshop_order_overviews."""
    import json as _json
    from app.models.workshop_order_overview import WorkshopOrderOverview

    query = select(WorkshopOrderOverview).where(
        WorkshopOrderOverview.deleted_at.is_(None),
    ).order_by(WorkshopOrderOverview.due_date.asc())

    if customer:
        query = query.where(WorkshopOrderOverview.customer_code == customer.strip())

    # Filtr podle Potvrzeno, fallback na Požadováno pokud Potvrzeno je NULL
    # DB datumy: "YYYYMMDD 00:00:00.000", input: "YYYY-MM-DD" → normalizace na YYYYMMDD
    date_col = func.substr(
        func.coalesce(WorkshopOrderOverview.confirm_date, WorkshopOrderOverview.due_date),
        1, 8,
    )
    if due_from:
        query = query.where(date_col >= due_from.replace("-", ""))

    if due_to:
        query = query.where(date_col <= due_to.replace("-", ""))

    result = await db.execute(query)
    entries = result.scalars().all()

    out: List[Dict[str, Any]] = []
    for e in entries:
        # Parse raw_data JSON blob
        raw = {}
        if e.raw_data:
            try:
                raw = _json.loads(e.raw_data)
            except (ValueError, TypeError):
                pass

        # Build operations/materials z raw_data (Wc01-10, Comp01-10, Wip01-10, Mat01-03, MatComp01-03)
        operations = _build_view_operations(raw)
        materials = _build_view_materials(raw)

        row_id = f"{e.co_num}|{e.co_line}|{e.co_release}"
        row = {
            "row_id": row_id,
            "customer_code": e.customer_code,
            "customer_name": e.customer_name,
            "delivery_code": e.customer_code,
            "delivery_name": e.delivery_name,
            "co_num": e.co_num,
            "co_line": e.co_line,
            "co_release": e.co_release,
            "item": e.item,
            "description": e.description,
            "material_ready": e.material_ready or False,
            "qty_ordered": e.qty_ordered,
            "qty_shipped": e.qty_shipped,
            "qty_on_hand": e.qty_on_hand,
            "qty_available": e.qty_available,
            "qty_wip": e.qty_wip,
            "due_date": e.due_date,
            "promise_date": e.promise_date,
            "confirm_date": e.confirm_date,
            "vp_candidates": [],  # VP candidates se naplní z workshop_job_routes
            "selected_vp_job": e.job if (e.job and operations) else None,
            "operations": operations,
            "materials": materials,
            "record_date": e.record_date,
        }
        out.append(row)

    # In-memory search filtr (po DB query)
    if search:
        s = search.strip().upper()
        out = [
            r for r in out
            if s in (r.get("co_num") or "").upper()
            or s in (r.get("item") or "").upper()
            or s in (r.get("description") or "").upper()
            or s in (r.get("selected_vp_job") or "").upper()
        ]

    # VP candidates enrichment z workshop_job_routes
    await _enrich_orders_with_vp_candidates(db, out)

    return out[:limit]


async def _enrich_orders_with_vp_candidates(
    db: AsyncSession, orders: List[Dict[str, Any]]
) -> None:
    """Doplní vp_candidates do orders overview řádků z workshop_job_routes."""
    from app.models.workshop_job_route import WorkshopJobRoute

    # Sbíráme unikátní item kódy
    items = {r.get("item") for r in orders if r.get("item")}
    if not items:
        return

    result = await db.execute(
        select(WorkshopJobRoute).where(
            WorkshopJobRoute.deleted_at.is_(None),
            WorkshopJobRoute.der_job_item.in_(list(items)),
            WorkshopJobRoute.job_stat.in_(["R", "F", "S"]),
        ).order_by(WorkshopJobRoute.job, cast(WorkshopJobRoute.oper_num, Integer))
    )
    routes = result.scalars().all()

    # Grupování: item → job|suffix → operace
    item_vp_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for r in routes:
        item = r.der_job_item
        if not item:
            continue
        vp_key = f"{r.job}|{r.suffix}"
        if item not in item_vp_map:
            item_vp_map[item] = {}
        if vp_key not in item_vp_map[item]:
            item_vp_map[item][vp_key] = {
                "job": r.job,
                "suffix": r.suffix,
                "job_stat": r.job_stat,
                "qty_released": r.job_qty_released,
                "qty_complete": r.qty_complete,
                "qty_scrapped": r.qty_scrapped,
                "item": item,
                "customer_name": None,
                "due_date": None,
                "operations": [],
            }
        # Přidat operaci
        if r.oper_num and r.wc:
            released = r.job_qty_released or 0
            complete = r.qty_complete or 0
            if released > 0 and complete >= released:
                op_status = "done"
            elif complete > 0:
                op_status = "in_progress"
            else:
                op_status = "idle"
            item_vp_map[item][vp_key]["operations"].append({
                "oper_num": r.oper_num,
                "wc": r.wc,
                "status": op_status,
                "state_text": None,
            })

    # Seřadit operace numericky v každém VP
    for vps in item_vp_map.values():
        for vp in vps.values():
            vp["operations"].sort(key=lambda op: int(op["oper_num"]) if op["oper_num"] and str(op["oper_num"]).isdigit() else 0)

    # ── Načíst tier z production_priorities ──
    from app.models.production_priority import ProductionPriority
    from app.services.production_planner_service import _derive_tier

    all_jobs: set[str] = set()
    for vps in item_vp_map.values():
        for vp in vps.values():
            if vp.get("job"):
                all_jobs.add(vp["job"].strip().upper())
    for order in orders:
        svj = order.get("selected_vp_job")
        if svj:
            all_jobs.add(svj.strip().upper())

    tier_map: Dict[str, str] = {}
    if all_jobs:
        prio_result = await db.execute(
            select(ProductionPriority).where(
                ProductionPriority.deleted_at.is_(None),
                ProductionPriority.infor_job.in_(list(all_jobs)),
            )
        )
        for pp in prio_result.scalars().all():
            tier_map[pp.infor_job] = _derive_tier(pp.priority, pp.is_hot)

    for vps in item_vp_map.values():
        for vp in vps.values():
            job_upper = (vp.get("job") or "").strip().upper()
            vp["tier"] = tier_map.get(job_upper, "normal")

    # Assign do orders — VP operace mají přednost před view operacemi
    for order in orders:
        item = order.get("item")
        if item and item in item_vp_map:
            candidates = list(item_vp_map[item].values())
            order["vp_candidates"] = candidates
            if candidates and candidates[0].get("operations"):
                order["operations"] = candidates[0]["operations"]
        svj = order.get("selected_vp_job")
        if svj:
            order["tier"] = tier_map.get(svj.strip().upper(), "normal")


async def read_vp_list_from_db(
    db: AsyncSession,
    stat: Optional[List[str]] = None,
    search: Optional[str] = None,
    wc: Optional[str] = None,
    sort_by: str = "Job",
    sort_dir: str = "asc",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Deduplikace workshop_job_routes po Job+Suffix → 1 řádek na VP."""
    from app.models.workshop_job_route import WorkshopJobRoute

    stat_values = set(s.upper() for s in stat) if stat else {"R", "F"}

    query = select(WorkshopJobRoute).where(
        WorkshopJobRoute.deleted_at.is_(None),
        WorkshopJobRoute.job_stat.in_(list(stat_values)),
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    vp_map: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        job = e.job or ""
        suffix = e.suffix or "0"
        key = f"{job}|{suffix}"

        if key not in vp_map:
            vp_map[key] = {
                "job": job,
                "suffix": suffix,
                "item": e.der_job_item,
                "description": e.job_description,
                "job_stat": (e.job_stat or "R").upper(),
                "qty_released": e.job_qty_released,
                "qty_complete": e.qty_complete,
                "qty_scrapped": e.qty_scrapped,
                "start_date": e.op_datum_st,
                "end_date": e.op_datum_sp,
                "oper_count": 1,
                "_wcs": {(e.wc or "").upper()},
            }
        else:
            entry = vp_map[key]
            entry["oper_count"] += 1
            entry["_wcs"].add((e.wc or "").upper())
            if e.op_datum_st and (not entry["start_date"] or e.op_datum_st < entry["start_date"]):
                entry["start_date"] = e.op_datum_st
            if e.op_datum_sp and (not entry["end_date"] or e.op_datum_sp > entry["end_date"]):
                entry["end_date"] = e.op_datum_sp

    result_list = list(vp_map.values())

    if wc:
        wc_upper = wc.strip().upper()
        result_list = [r for r in result_list if wc_upper in r["_wcs"]]

    if search:
        s = search.strip().upper()
        result_list = [
            r for r in result_list
            if s in (r["job"] or "").upper()
            or s in (r["item"] or "").upper()
            or s in (r["description"] or "").upper()
        ]

    for r in result_list:
        r.pop("_wcs", None)

    reverse = sort_dir.lower() == "desc"

    def sort_key(r: Dict[str, Any]) -> Any:
        v = r.get(sort_by.lower()) if sort_by.lower() in r else r.get(sort_by)
        return v if v is not None else ""

    result_list.sort(key=sort_key, reverse=reverse)
    return result_list[:limit]


def _wjr_to_queue_dict(e) -> Dict[str, Any]:
    """Konvertuje WorkshopJobRoute ORM objekt na dict ve formátu _normalize_queue_row output."""
    return {
        "Job": e.job,
        "Suffix": e.suffix or "0",
        "OperNum": e.oper_num,
        "Wc": e.wc,
        "State": e.jbr_state,
        "StateAsd": e.jbr_state_asd,
        "LzeDokoncit": e.jbr_lze_dokoncit,
        "PlanFlag": e.jbr_plan_flag,
        "DerJobItem": e.der_job_item,
        "JobDescription": e.job_description,
        "JobQtyReleased": e.job_qty_released,
        "QtyComplete": e.qty_complete,
        "QtyScrapped": e.qty_scrapped,
        "JshSetupHrs": e.jsh_setup_hrs,
        "DerRunMchHrs": e.der_run_mch_hrs,
        "OpDatumSt": e.op_datum_st,
        "OpDatumSp": e.op_datum_sp,
    }
