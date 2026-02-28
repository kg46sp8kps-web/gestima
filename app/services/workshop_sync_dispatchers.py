"""GESTIMA — Workshop Sync Dispatchers

Dispatch funkce pro sync workshop dat z Inforu do lokální DB.
Voláno z InforSyncService._dispatch_step().

Tři dispatchery:
  - dispatch_workshop_routes: SLJobRoutes (Type='J') → workshop_job_routes
  - dispatch_workshop_orders: IteRybPrehledZakazekView → workshop_order_overviews
  - dispatch_workshop_jbr: IteCzTsdJbrDetails → workshop_job_routes (JBR columns only)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workshop_job_route import WorkshopJobRoute
from app.models.workshop_order_overview import WorkshopOrderOverview

logger = logging.getLogger(__name__)


def _as_clean_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _parse_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return round(float(s), 4)
    except (ValueError, TypeError):
        return None


# ─── Workshop Routes (SLJobRoutes Type='J') ──────────────────────────────

async def dispatch_workshop_routes(
    rows: List[Dict[str, Any]], db: AsyncSession
) -> Dict[str, Any]:
    """Upsert SLJobRoutes (Type='J') do workshop_job_routes.

    Klíč: (job, suffix, oper_num).
    Completed operace (job_stat='C') dostanou soft-delete.
    """
    if not rows:
        return _empty_result()

    total_created = 0
    total_updated = 0
    all_errors: List[str] = []

    # Batch: sbíráme klíče pro jednorázový lookup
    keys = []
    for row in rows:
        job = _as_clean_str(row.get("Job"))
        oper_num = _as_clean_str(row.get("OperNum"))
        suffix = _as_clean_str(row.get("Suffix")) or "0"
        if job and oper_num:
            keys.append((job, suffix, oper_num))

    if not keys:
        return _empty_result()

    # Batch lookup existujících záznamů
    existing_map: Dict[tuple, WorkshopJobRoute] = {}
    result = await db.execute(select(WorkshopJobRoute))
    for entry in result.scalars().all():
        existing_map[(entry.job, entry.suffix, entry.oper_num)] = entry

    now = datetime.utcnow()

    for row in rows:
        try:
            job = _as_clean_str(row.get("Job"))
            oper_num = _as_clean_str(row.get("OperNum"))
            suffix = _as_clean_str(row.get("Suffix")) or "0"
            if not job or not oper_num:
                continue

            job_stat = (_as_clean_str(row.get("JobStat")) or "R").upper()
            key = (job, suffix, oper_num)
            existing = existing_map.get(key)

            mapped = {
                "wc": _as_clean_str(row.get("Wc")),
                "job_stat": job_stat,
                "der_job_item": _as_clean_str(row.get("DerJobItem")),
                "job_description": _as_clean_str(row.get("JobDescription")),
                "job_qty_released": _parse_float(row.get("JobQtyReleased")),
                "qty_complete": _parse_float(row.get("QtyComplete")),
                "qty_scrapped": _parse_float(row.get("QtyScrapped")),
                "jsh_setup_hrs": _parse_float(row.get("JshSetupHrs")),
                "der_run_mch_hrs": _parse_float(row.get("DerRunMchHrs")),
                "op_datum_st": _as_clean_str(row.get("DerStartDate")),
                "op_datum_sp": _as_clean_str(row.get("DerEndDate")),
                "record_date": _as_clean_str(row.get("RecordDate")),
            }

            if existing:
                for attr, val in mapped.items():
                    setattr(existing, attr, val)
                existing.updated_at = now
                existing.updated_by = "sync"
                # Soft-delete completed, restore non-completed
                if job_stat == "C":
                    if existing.deleted_at is None:
                        existing.deleted_at = now
                        existing.deleted_by = "sync:completed"
                else:
                    if existing.deleted_at is not None:
                        existing.deleted_at = None
                        existing.deleted_by = None
                total_updated += 1
            else:
                entry = WorkshopJobRoute(
                    job=job,
                    suffix=suffix,
                    oper_num=oper_num,
                    **mapped,
                )
                entry.created_at = now
                entry.created_by = "sync"
                entry.updated_at = now
                entry.updated_by = "sync"
                if job_stat == "C":
                    entry.deleted_at = now
                    entry.deleted_by = "sync:completed"
                db.add(entry)
                existing_map[key] = entry
                total_created += 1

        except Exception as e:
            all_errors.append(f"Route sync error: {e}")
            logger.error("Workshop route sync error: %s", e, exc_info=True)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return _build_result(total_created, total_updated, 0, all_errors)


# ─── Workshop Orders (IteRybPrehledZakazekView) ─────────────────────────

# Sloupce, které jdou do raw_data JSON blob
_RAW_DATA_KEYS = [
    "Wc01", "Wc02", "Wc03", "Wc04", "Wc05", "Wc06", "Wc07", "Wc08", "Wc09", "Wc10",
    "Comp01", "Comp02", "Comp03", "Comp04", "Comp05", "Comp06", "Comp07", "Comp08", "Comp09", "Comp10",
    "Wip01", "Wip02", "Wip03", "Wip04", "Wip05", "Wip06", "Wip07", "Wip08", "Wip09", "Wip10",
    "Mat01", "Mat02", "Mat03", "MatComp01", "MatComp02", "MatComp03",
    "Ready", "Picked", "IsOverPromiseDate",
    "TotalWeight", "PriceConv", "RybCena",
    "Baleni", "Regal",
    "CustPo", "CustShipName",
]


async def dispatch_workshop_orders(
    rows: List[Dict[str, Any]], db: AsyncSession
) -> Dict[str, Any]:
    """Upsert IteRybPrehledZakazekView do workshop_order_overviews.

    Klíč: (co_num, co_line, co_release).
    raw_data = JSON blob pro view-specific sloupce.
    """
    if not rows:
        return _empty_result()

    total_created = 0
    total_updated = 0
    all_errors: List[str] = []

    # Batch lookup existujících záznamů
    existing_map: Dict[tuple, WorkshopOrderOverview] = {}
    result = await db.execute(
        select(WorkshopOrderOverview).where(WorkshopOrderOverview.deleted_at.is_(None))
    )
    for entry in result.scalars().all():
        existing_map[(entry.co_num, entry.co_line, entry.co_release)] = entry

    now = datetime.utcnow()

    for row in rows:
        try:
            co_num = _as_clean_str(row.get("CoNum"))
            co_line = _as_clean_str(row.get("CoLine"))
            co_release = _as_clean_str(row.get("CoRelease")) or "0"
            if not co_num or not co_line:
                continue

            # Build raw_data JSON
            raw = {}
            for k in _RAW_DATA_KEYS:
                v = row.get(k)
                if v is not None:
                    raw[k] = str(v).strip() if not isinstance(v, (int, float, bool)) else v
            raw_json = json.dumps(raw, default=str) if raw else None

            # Confirm date: pokus o několik polí
            confirm_date = (
                _as_clean_str(row.get("RybDatumPotvrRadZak"))
                or _as_clean_str(row.get("RybConfirmDate"))
                or _as_clean_str(row.get("RybCoConfirmationDate"))
                or _as_clean_str(row.get("ConfirmedDate"))
            )

            mapped = {
                "customer_code": _as_clean_str(row.get("CustNum")),
                "customer_name": _as_clean_str(row.get("CustName")),
                "delivery_name": _as_clean_str(row.get("CustShipName")) or _as_clean_str(row.get("CustName")),
                "item": _as_clean_str(row.get("Item")),
                "description": _as_clean_str(row.get("ItemDescription")),
                "stat": _as_clean_str(row.get("Stat")),
                "due_date": _as_clean_str(row.get("DueDate")),
                "promise_date": _as_clean_str(row.get("PromiseDate")),
                "confirm_date": confirm_date,
                "qty_ordered": _parse_float(row.get("QtyOrderedConv")),
                "qty_shipped": _parse_float(row.get("QtyShipped")),
                "qty_on_hand": _parse_float(row.get("QtyOnHand")),
                "qty_available": _parse_float(row.get("QtyAvailable")),
                "qty_wip": _parse_float(row.get("QtyWIP")),
                "job": _as_clean_str(row.get("Job")),
                "suffix": _as_clean_str(row.get("Suffix")),
                "job_count": int(row.get("JobCount", 0) or 0) if row.get("JobCount") is not None else None,
                "material_ready": str(row.get("Ready", "0")).strip() == "1",
                "raw_data": raw_json,
                "record_date": _as_clean_str(row.get("RecordDate")),
            }

            key = (co_num, co_line, co_release)
            existing = existing_map.get(key)

            if existing:
                for attr, val in mapped.items():
                    setattr(existing, attr, val)
                existing.updated_at = now
                existing.updated_by = "sync"
                total_updated += 1
            else:
                entry = WorkshopOrderOverview(
                    co_num=co_num,
                    co_line=co_line,
                    co_release=co_release,
                    **mapped,
                )
                entry.created_at = now
                entry.created_by = "sync"
                entry.updated_at = now
                entry.updated_by = "sync"
                db.add(entry)
                existing_map[key] = entry
                total_created += 1

        except Exception as e:
            all_errors.append(f"Order sync error: {e}")
            logger.error("Workshop order sync error: %s", e, exc_info=True)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return _build_result(total_created, total_updated, 0, all_errors)


# ─── Workshop JBR (IteCzTsdJbrDetails) ────────────────────────────────


def _jbr_first(row: Dict[str, Any], keys: tuple) -> Any:
    """Return first non-empty value from row matching any of the key variants."""
    for key in keys:
        v = row.get(key)
        if v not in (None, ""):
            return v
    return None


# Key variants for JBR fields — same aliases as _normalize_queue_row in workshop_service
_JBR_JOB_KEYS = ("Job", "JobNum", "colJob")
_JBR_SUFFIX_KEYS = ("Suffix", "JobSuffix", "colSuffix", "colJobSuffix", "vSuffix")
_JBR_OPER_KEYS = ("OperNum", "Oper", "colOper", "colOperNum")
_JBR_STATE_KEYS = ("State", "Status", "colState")
_JBR_STATE_ASD_KEYS = ("StateAsd", "StatusAsd", "colStateAsd")
_JBR_LZE_DOKONCIT_KEYS = ("LzeDokoncit", "colLzeDokoncit")
_JBR_PLAN_FLAG_KEYS = ("PlanFlag", "colPlanFlag")
_JBR_JOB_SUFFIX_OPER_KEYS = ("JobSuffixOperNum", "vJobSuffixOperNum", "colJobSuffixOperNum")


def _parse_jso(value) -> tuple | None:
    """Parse 'JOB;SUFFIX;OPER' composite key."""
    text = _as_clean_str(value)
    if not text:
        return None
    for sep in (";", "|", ",", ":", "_", "-", " "):
        if sep not in text:
            continue
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            return (sep.join(parts[:-2]).strip(), parts[-2] or "0", parts[-1])
    return None


async def dispatch_workshop_jbr(
    rows: List[Dict[str, Any]], db: AsyncSession
) -> Dict[str, Any]:
    """UPDATE ONLY — enrich existing workshop_job_routes with JBR state data.

    JBR is not a source for creating records (SLJobRoutes handles that).
    Only updates jbr_state, jbr_state_asd, jbr_lze_dokoncit, jbr_plan_flag.
    """
    if not rows:
        return _empty_result()

    total_updated = 0
    total_skipped = 0
    all_errors: List[str] = []

    # Log first row keys for debugging column names
    if rows:
        logger.info("JBR dispatch: %d rows, first row keys: %s", len(rows), list(rows[0].keys()))

    # Batch lookup all active workshop_job_routes
    result = await db.execute(
        select(WorkshopJobRoute).where(WorkshopJobRoute.deleted_at.is_(None))
    )
    existing_map: Dict[tuple, WorkshopJobRoute] = {}
    for entry in result.scalars().all():
        existing_map[(entry.job, entry.suffix, entry.oper_num)] = entry

    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    for row in rows:
        try:
            job = _as_clean_str(_jbr_first(row, _JBR_JOB_KEYS))
            oper_num = _as_clean_str(_jbr_first(row, _JBR_OPER_KEYS))
            suffix = _as_clean_str(_jbr_first(row, _JBR_SUFFIX_KEYS)) or "0"

            # Composite key fallback (JobSuffixOperNum)
            if not job or not oper_num:
                parsed = _parse_jso(_jbr_first(row, _JBR_JOB_SUFFIX_OPER_KEYS))
                if parsed:
                    if not job:
                        job = parsed[0]
                    if suffix in ("", "0") and parsed[1]:
                        suffix = parsed[1]
                    if not oper_num:
                        oper_num = parsed[2]

            if not job or not oper_num:
                continue

            key = (job, suffix, oper_num)
            existing = existing_map.get(key)
            if not existing:
                total_skipped += 1
                continue

            # Diff-update: only write if value actually changed
            changed = False
            for attr, keys in [
                ("jbr_state", _JBR_STATE_KEYS),
                ("jbr_state_asd", _JBR_STATE_ASD_KEYS),
                ("jbr_lze_dokoncit", _JBR_LZE_DOKONCIT_KEYS),
                ("jbr_plan_flag", _JBR_PLAN_FLAG_KEYS),
            ]:
                new_val = _as_clean_str(_jbr_first(row, keys))
                if getattr(existing, attr) != new_val:
                    setattr(existing, attr, new_val)
                    changed = True

            if changed:
                existing.jbr_synced_at = now_str
                total_updated += 1

        except Exception as e:
            all_errors.append(f"JBR sync error: {e}")
            logger.error("Workshop JBR sync error: %s", e, exc_info=True)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return _build_result(0, total_updated, total_skipped, all_errors)


# ─── Helpers ─────────────────────────────────────────────────────────────

def _empty_result() -> Dict[str, Any]:
    return {"created_count": 0, "updated_count": 0, "errors": []}


def _build_result(created: int, updated: int, skipped: int, errors: List[str]) -> Dict[str, Any]:
    return {
        "created_count": created,
        "updated_count": updated,
        "skipped_count": skipped,
        "errors": errors,
    }
