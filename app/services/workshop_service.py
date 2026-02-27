"""GESTIMA - Workshop Service

Dílenská aplikace napojená na Infor CloudSuite Industrial.

Tento modul implementuje RE flow z InduStream:
- fronta práce z SLJobRoutes (včetně plánovaných časů DerStartDate/DerEndDate)
- start/setup přes IteCzTsdUpdateDcSfcWrapperSp + IteCzTsdUpdateMchtrxSp
- stop přes IteCzTsdUpdateDcSfcWrapperSp + IteCzTsdUpdateMchtrxSp (fallback DCSFC_MCHTRX)
- manuální odvody přes IteCzTsdUpdateDcSfc34Sp (20 params)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import safe_commit, set_audit
from app.models.enums import WorkshopTxStatus
from app.models.user import User
from app.models.workshop_transaction import WorkshopTransaction, WorkshopTransactionCreate

logger = logging.getLogger(__name__)

# Infor write IDO/SP
_WRITE_IDO = "IteCzTsdStd"
_WRITE_SP_SFC34 = "IteCzTsdUpdateDcSfc34Sp"
_WRITE_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"
_WRITE_SP_INS_WRAPPER_STOP = "IteCzInsWrapperDcsfcUpdateSp"
_WRITE_SP_MCHTRX = "IteCzTsdUpdateMchtrxSp"
_WRITE_SP_DCSFC_MCHTRX = "IteCzTsdUpdateDcSfcMchtrxSp"
_WRITE_SP_INIT_PARMS = "IteCzTsdInitParmsSp"
_WRITE_SP_VALIDATE_EMP_MCHTRX = "IteCzTsdValidateEmpNumMchtrxSp"

_WRAPPER_TYPES = {"setup_start", "setup_end", "start", "stop"}
_QTY_EPSILON = 1e-6
_SAW_WC_PREFIXES = ("PS", "PILA", "SAW")
_DONE_STATE_MARKERS = ("DOKON", "COMPLET", "CLOSED", "FINISH", "DONE", "UZAVR")

# Queue properties from RE documentation (JbrDetails), with fallbacks for older aliases.
_QUEUE_PROP_SETS: List[List[str]] = [
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


def _format_decimal(value: float) -> str:
    # Infor quantity fields are commonly represented with 8 decimal digits.
    return f"{value:.8f}"


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


def _format_infor_datetime(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


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
    job = _as_clean_str(_first_value(row, ("Job", "JobNum")))
    oper_num = _as_clean_str(_first_value(row, ("OperNum", "Oper")))
    if not job or not oper_num:
        return None

    suffix = _as_clean_str(_first_value(row, ("Suffix", "JobSuffix"))) or "0"
    wc = _as_clean_str(_first_value(row, ("Wc", "WC", "colWc")))

    return {
        "Job": job,
        "Suffix": suffix,
        "OperNum": oper_num,
        "Wc": wc,
        "State": _as_clean_str(_first_value(row, ("State", "Status"))),
        "StateAsd": _as_clean_str(_first_value(row, ("StateAsd", "StatusAsd"))),
        "DerJobItem": _as_clean_str(_first_value(row, ("Dil", "DerJobItem", "Item"))),
        "JobDescription": _as_clean_str(
            _first_value(row, ("Nazev", "JobDescription", "Description", "DerItemDescription"))
        ),
        "JobQtyReleased": _parse_float(_first_value(row, ("VpMnoz", "JobQtyReleased", "QtyReleased"))),
        "QtyComplete": _parse_float(_first_value(row, ("Kusy", "QtyComplete", "JrtQtyComplete"))),
        "QtyScrapped": _parse_float(_first_value(row, ("QtyScrapped", "JrtQtyScrapped"))),
        "JshSetupHrs": _parse_float(_first_value(row, ("JshSetupHrs", "SetupHrs"))),
        "DerRunMchHrs": _parse_float(_first_value(row, ("DerRunMchHrs", "RunHrs", "Doba"))),
        "OpDatumSt": _as_clean_str(
            _first_value(row, ("OpDatumSt", "DerStartDate", "JshStartDate", "StartDate", "SchedStartDate"))
        ),
        "OpDatumSp": _as_clean_str(
            _first_value(row, ("OpDatumSp", "DerEndDate", "JshEndDate", "EndDate", "SchedFinishDate"))
        ),
    }


def _infor_ok(response: Dict[str, Any]) -> bool:
    msg_code = int(response.get("MessageCode", 0) or 0)
    if msg_code != 0:
        return False

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


async def _invoke_checked(
    infor_client,
    method_name: str,
    positional_values: Sequence[str],
) -> Dict[str, Any]:
    response = await infor_client.invoke_method_positional(
        ido_name=_WRITE_IDO,
        method_name=method_name,
        positional_values=[str(v) if v is not None else "" for v in positional_values],
    )
    if not _infor_ok(response):
        raise RuntimeError(_infor_error(response))
    return response


async def _invoke_checked_candidates(
    infor_client,
    method_name: str,
    candidates: Sequence[Sequence[str]],
) -> Dict[str, Any]:
    errors: List[str] = []
    for idx, params in enumerate(candidates, start=1):
        try:
            return await _invoke_checked(infor_client, method_name, params)
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


async def _load_collection_first(
    infor_client,
    ido_name: str,
    property_sets: Sequence[Sequence[str]],
    *,
    filter_expr: Optional[str] = None,
    order_by: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
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
            return list(result.get("data", []))
        except Exception as exc:
            errors.append(f"{list(properties)} -> {exc}")

    raise RuntimeError(
        f"LoadCollection {ido_name} failed for all property sets: {' || '.join(errors)}"
    )


def _eq_filter(field: str, value: str) -> str:
    safe_value = value.strip().replace("'", "''")
    return f"{field} = '{safe_value}'"


async def _fetch_queue_from_jbr(
    infor_client,
    wc: Optional[str],
    record_cap: int,
) -> List[Dict[str, Any]]:
    filters: List[str] = []
    if wc:
        filters.append(_eq_filter("Wc", wc))

    filter_expr = " AND ".join(filters) if filters else None

    rows = await _load_collection_first(
        infor_client,
        ido_name="IteCzTsdJbrDetails",
        property_sets=_QUEUE_PROP_SETS,
        filter_expr=filter_expr,
        order_by="OpDatumSt ASC, Job ASC, OperNum ASC",
        record_cap=record_cap,
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
    return queue


async def fetch_wc_queue(
    infor_client,
    wc: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """Načte frontu práce z rozvrhu operací (IteCzTsdJbrDetails), bez fallbacku."""
    try:
        return await _fetch_queue_from_jbr(infor_client, wc, record_cap)
    except Exception as exc:
        logger.error("JbrDetails queue load failed (no fallback allowed): %s", exc)
        raise RuntimeError(f"JbrDetails queue source unavailable: {exc}") from exc


async def fetch_open_jobs(
    infor_client,
    wc_filter: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """Vrátí deduplikovaný seznam zakázek (1 řádek na Job+Suffix)."""
    queue = await fetch_wc_queue(infor_client=infor_client, wc=wc_filter, record_cap=record_cap * 10)

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


async def fetch_job_operations(
    infor_client,
    job: str,
    suffix: str = "0",
) -> List[Dict[str, Any]]:
    """Načte operace zakázky z JbrDetails (bez fallbacku)."""
    safe_job = job.strip()
    safe_suffix = suffix.strip() or "0"

    filter_expr = f"{_eq_filter('Job', safe_job)} AND {_eq_filter('Suffix', safe_suffix)}"

    try:
        rows = await _load_collection_first(
            infor_client,
            ido_name="IteCzTsdJbrDetails",
            property_sets=_QUEUE_PROP_SETS,
            filter_expr=filter_expr,
            order_by="OpDatumSt ASC, OperNum ASC",
            record_cap=500,
        )

        operations: List[Dict[str, Any]] = []
        for row in rows:
            queue_row = _normalize_queue_row(row)
            if not queue_row:
                continue
            if _is_operation_completed_row(queue_row):
                continue
            operations.append(
                {
                    "Job": queue_row["Job"],
                    "Suffix": queue_row["Suffix"],
                    "OperNum": queue_row["OperNum"],
                    "Wc": queue_row.get("Wc") or "",
                    "QtyReleased": queue_row.get("JobQtyReleased"),
                    "QtyComplete": queue_row.get("QtyComplete"),
                    "ScrapQty": queue_row.get("QtyScrapped"),
                    "SetupHrs": queue_row.get("JshSetupHrs"),
                    "RunHrs": queue_row.get("DerRunMchHrs"),
                    "OpDatumSt": queue_row.get("OpDatumSt"),
                    "OpDatumSp": queue_row.get("OpDatumSp"),
                }
            )

        if operations:
            operations.sort(
                key=lambda item: (
                    _sort_key_for_date(item.get("OpDatumSt")),
                    item.get("OperNum") or "",
                )
            )
        return operations
    except Exception as exc:
        logger.error("JbrDetails operations load failed (no fallback allowed): %s", exc)
        raise RuntimeError(f"JbrDetails operations source unavailable: {exc}") from exc


async def fetch_job_materials(
    infor_client,
    job: str,
    suffix: str = "0",
    oper_num: str = "0",
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
                "Qty": _parse_float(_first_value(row, ("QtyPerPcBd", "Qty", "MatlQty", "DerQty"))),
                "BatchCons": _parse_float(_first_value(row, ("BatchConsumptionBd", "BatchCons", "QtyIssued"))),
            }
        )

    return materials


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
        properties=["OperNum", "Wc", "JobQtyReleased", "QtyComplete", "QtyScrapped"],
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
    is_first_operation = _is_first_operation(safe_oper, rows)
    allow_overrun = _is_saw_wc(wc) and is_first_operation

    target_released_qty: Optional[float] = None
    if overrun and allow_overrun:
        proposed = total_done_qty + requested_total_qty
        if proposed > (released_qty + _QTY_EPSILON):
            target_released_qty = proposed

    return {
        "wc": wc,
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

    emp_num = getattr(current_user, "infor_emp_num", None) or current_user.username
    trans_type = tx.trans_type.value if hasattr(tx.trans_type, "value") else str(tx.trans_type)
    qty_policy_context: Optional[Dict[str, Any]] = None

    try:
        qty_policy_context = await _build_qty_policy_context(tx, infor_client)
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

        tx.status = WorkshopTxStatus.POSTED
        tx.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        tx.error_msg = None
        logger.info("Transaction %s posted to Infor successfully", tx_id)
    except Exception as exc:
        tx.status = WorkshopTxStatus.FAILED
        tx.error_msg = str(exc)[:500]
        logger.error("Transaction %s failed to post: %s", tx_id, exc)

    set_audit(tx, current_user.username, is_update=True)
    await safe_commit(db, tx, "aktualizace statusu transakce")
    return tx


async def _post_wrapper_flow(tx: WorkshopTransaction, infor_client, emp_num: str) -> None:
    # Best-effort context init before machine transition.
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_INIT_PARMS,
        candidates=[[], [""], [tx.infor_job, tx.infor_suffix or "0", tx.oper_num]],
    )
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_EMP_MCHTRX,
        candidates=[[tx.wc or ""], [tx.infor_job], []],
    )

    # Labor transition
    wrapper_params = _build_wrapper_params(tx, emp_num)
    await _invoke_checked(infor_client, _WRITE_SP_WRAPPER, wrapper_params)

    # Machine transition (required for live machine state)
    await _invoke_checked_candidates(
        infor_client,
        _WRITE_SP_MCHTRX,
        candidates=_build_mchtrx_candidates(tx, emp_num, mode="H"),
    )


async def _post_stop_flow(tx: WorkshopTransaction, infor_client, emp_num: str) -> None:
    # Best-effort: refresh Infor-side state context before stop.
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_INIT_PARMS,
        candidates=[[], [""], [tx.infor_job, tx.infor_suffix or "0", tx.oper_num]],
    )

    # Best-effort: set Mchtrx employee context when Infor expects it.
    await _invoke_nonfatal_candidates(
        infor_client,
        _WRITE_SP_VALIDATE_EMP_MCHTRX,
        candidates=[[tx.wc or ""], [tx.infor_job], []],
    )

    # Stop labor transition.
    wrapper_params = _build_wrapper_params(tx, emp_num)
    await _invoke_checked(infor_client, _WRITE_SP_WRAPPER, wrapper_params)

    # Preferred machine stop (validated against RE logs): Mchtrx with transType=J.
    try:
        await _invoke_checked_candidates(
            infor_client,
            _WRITE_SP_MCHTRX,
            candidates=_build_mchtrx_candidates(tx, emp_num, mode="J"),
        )
    except Exception as mch_exc:
        # Fallback to full DCSFC machine stop signature for installations with stricter context.
        logger.warning("IteCzTsdUpdateMchtrxSp stop failed, fallback DCSFC_MCHTRX: %s", mch_exc)
        await _invoke_checked_candidates(
            infor_client,
            _WRITE_SP_DCSFC_MCHTRX,
            candidates=_build_dcsfc_mchtrx_candidates(tx, emp_num),
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


def _build_wrapper_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    trans_type = tx.trans_type.value if hasattr(tx.trans_type, "value") else str(tx.trans_type)
    is_stop = trans_type == "stop"

    return [
        "",  # 0
        emp_num,  # 1 EmpNum
        "0",  # 2 MultiJob flag
        _trans_type_code_wrapper(tx.trans_type),  # 3 TransType
        tx.infor_job,  # 4 Job
        tx.infor_suffix or "0",  # 5 Suffix
        tx.oper_num,  # 6 OperNum
        str(tx.qty_completed or 0) if is_stop else "",  # 7 QtyComplete
        str(tx.qty_scrapped or 0) if is_stop else "",  # 8 QtyScrap
        str(tx.qty_moved or 0) if (is_stop and tx.qty_moved is not None) else "",  # 9 QtyMoved
        _bool_to_flag(is_stop and tx.oper_complete),  # 10 Complete
        _bool_to_flag(is_stop and tx.job_complete),  # 11 Close
        "0",  # 12 IssueParent
        "",  # 13 Location
        "",  # 14 Lot
        tx.scrap_reason or "",  # 15 ReasonCode
        "",  # 16 SerNumList
        tx.wc or "",  # 17 Wc
        "",  # 18
        _source_module_for_wrapper(trans_type),  # 19 SourceModule
        "",  # 20 IdMachine
        "",  # 21 ResId
        "0",  # 22 flag
        "T",  # 23 terminal mode
        "",  # 24 Infobar OUT
    ]


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
    wc = tx.wc or ""
    suffix = tx.infor_suffix or "0"

    raw_candidates: List[List[str]] = [
        # Variant A: supply WC as both WC and machine id, keep emp context in OldEmpNum.
        [emp_num, mode, tx.infor_job, suffix, tx.oper_num, wc, wc, emp_num, ""],
        # Variant B: no machine id, but preserve employee context.
        [emp_num, mode, tx.infor_job, suffix, tx.oper_num, wc, "", emp_num, ""],
        # Variant C: legacy shape seen in logs.
        [emp_num, mode, tx.infor_job, suffix, tx.oper_num, wc, "", "", ""],
    ]
    return _dedupe_candidates(raw_candidates)


def _build_dcsfc_mchtrx_candidates(tx: WorkshopTransaction, emp_num: str) -> List[List[str]]:
    suffix = tx.infor_suffix or "0"
    item_value = tx.infor_item or "0"
    qty_comp = str(tx.qty_completed or 0)
    qty_scrap = str(tx.qty_scrapped or 0)
    qty_move = str(tx.qty_moved or 0)

    base_tail = [
        _bool_to_flag(tx.oper_complete),  # Complete
        _bool_to_flag(tx.job_complete),  # Close
        "0",  # IssueParent
        "",  # Location
        "",  # Lot
        tx.scrap_reason or "",  # ReasonCode
        "",  # SerNumList
        tx.wc or "",  # Wc
        "",  # Infobar OUT 1
        "",  # Infobar OUT 2
    ]

    return _dedupe_candidates(
        [
            # Signature discovered by probe (22 params): term, emp, multijob, transtype, job...
            [
                "",
                emp_num,
                "0",
                "J",
                tx.infor_job,
                suffix,
                tx.oper_num,
                item_value,
                "",
                qty_comp,
                qty_scrap,
                qty_move,
                *base_tail,
            ],
            # Alternate trans type coding used in some wrappers.
            [
                "",
                emp_num,
                "0",
                "1",
                tx.infor_job,
                suffix,
                tx.oper_num,
                item_value,
                "",
                qty_comp,
                qty_scrap,
                qty_move,
                *base_tail,
            ],
        ]
    )


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
