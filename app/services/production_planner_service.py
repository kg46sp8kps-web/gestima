"""GESTIMA - Production Planner Service

VP-centricky Gantt pohled na vyrobu.
DB uklada POUZE prioritu + hot flag. Vsechna data (operace, datumy, mnozstvi)
vzdy z Inforu. CO terminy pres existujici Item-based matching.

Scheduling: Forward-scheduling engine — lokalni logika.
Z Inforu bereme jen CO dělat (operace, WC), JAK DLOUHO (setup + qty/pcs_per_hour)
a KDY hotovo (CO deadline). Planovani je 100% lokalni.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import safe_commit, set_audit
from app.models.production_priority import ProductionPriority
from app.services import workshop_service

logger = logging.getLogger(__name__)

# ============================================================================
# Scheduling constants
# ============================================================================
HOURS_PER_DAY = 8
SHIFT_START_HOUR = 7   # 07:00
SHIFT_END_HOUR = 15    # 15:00
DEFAULT_OP_HOURS = 2.0  # Fallback when setup+run missing

# Tier → (priority, is_hot) mapping
TIER_PRIORITY_MAP: Dict[str, tuple] = {
    'hot': (5, True),
    'urgent': (20, False),
    'normal': (100, False),
}


def _derive_tier(priority: int, is_hot: bool) -> str:
    """Odvodit tier z priority čísla a is_hot flagu."""
    if is_hot:
        return 'hot'
    if priority <= 20:
        return 'urgent'
    return 'normal'

# ============================================================================
# Scheduling helpers
# ============================================================================


def _clamp_to_work_start(dt: datetime) -> datetime:
    """Posunout datetime na nejblizsi pracovni cas (07:00, preskocit vikend)."""
    # Weekend: Saturday=5, Sunday=6
    while dt.weekday() >= 5:
        dt = dt.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
        dt += timedelta(days=1)
    # Before shift start -> move to shift start
    if dt.hour < SHIFT_START_HOUR:
        dt = dt.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
    # After shift end -> next workday 07:00
    if dt.hour >= SHIFT_END_HOUR:
        dt += timedelta(days=1)
        dt = dt.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
        # Skip weekend again
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
    return dt


def _add_work_hours(start: datetime, hours: float) -> datetime:
    """Pricit pracovni hodiny (8h den 07:00-15:00, preskocit vikendy)."""
    if hours <= 0:
        return start
    current = _clamp_to_work_start(start)
    remaining = hours
    while remaining > 0:
        day_end = current.replace(
            hour=SHIFT_END_HOUR, minute=0, second=0, microsecond=0,
        )
        available = (day_end - current).total_seconds() / 3600
        if available <= 0:
            # Move to next workday
            current += timedelta(days=1)
            current = current.replace(
                hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0,
            )
            current = _clamp_to_work_start(current)
            continue
        if remaining <= available:
            current += timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= available
            current = day_end
            # Move to next workday
            current += timedelta(days=1)
            current = current.replace(
                hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0,
            )
            current = _clamp_to_work_start(current)
    return current


def _compute_duration_hrs(
    setup_hrs: Optional[float],
    pcs_per_hour: Optional[float],
    qty: Optional[float],
) -> float:
    """Vypocet delky operace v hodinach: setup + qty/pcs_per_hour.

    DerRunMchHrs = ks/hod (kusy za hodinu stroje).
    JshSetupHrs = setup v hodinach.
    """
    setup = setup_hrs or 0.0
    if pcs_per_hour and pcs_per_hour > 0 and qty and qty > 0:
        run = qty / pcs_per_hour
    else:
        run = 0.0
    total = setup + run
    return total if total > 0 else DEFAULT_OP_HOURS


def _schedule_operations(
    vps: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Forward-schedule: prirazeni sched_start/sched_end kazdé operaci.

    Vraci wc_lanes strukturu pro WC pohled.
    """
    if now is None:
        now = datetime.now()
    today_start = _clamp_to_work_start(now)

    # Horizons
    wc_available: Dict[str, datetime] = {}
    vp_prev_end: Dict[str, datetime] = {}

    # --- Pass 1: done + in_progress ops → initialize horizons ---
    for vp in vps:
        key = _vp_key(vp["job"], vp["suffix"])
        for op in vp["operations"]:
            status = op["status"]
            if status == "done":
                # Keep Infor dates, update horizons
                op_end_date = _parse_date(op.get("end_date"))
                if op_end_date:
                    op_end_dt = datetime.combine(
                        op_end_date,
                        datetime.min.time().replace(hour=SHIFT_END_HOUR),
                    )
                    op_start_date = _parse_date(op.get("start_date"))
                    op_start_dt = datetime.combine(
                        op_start_date or op_end_date,
                        datetime.min.time().replace(hour=SHIFT_START_HOUR),
                    )
                    op["sched_start"] = op_start_dt.isoformat()
                    op["sched_end"] = op_end_dt.isoformat()

                    wc_code = op.get("wc") or "_NONE_"
                    wc_available[wc_code] = max(
                        wc_available.get(wc_code, today_start), op_end_dt,
                    )
                    vp_prev_end[key] = max(
                        vp_prev_end.get(key, today_start), op_end_dt,
                    )
                else:
                    op["sched_start"] = None
                    op["sched_end"] = None

                duration = _compute_duration_hrs(
                    op.get("setup_hrs"), op.get("pcs_per_hour"), op.get("qty_released"),
                )
                op["duration_hrs"] = round(duration, 2)

            elif status == "in_progress":
                duration = _compute_duration_hrs(
                    op.get("setup_hrs"), op.get("pcs_per_hour"), op.get("qty_released"),
                )
                op["duration_hrs"] = round(duration, 2)
                sched_start = _clamp_to_work_start(now)
                sched_end = _add_work_hours(sched_start, duration)
                op["sched_start"] = sched_start.isoformat()
                op["sched_end"] = sched_end.isoformat()

                wc_code = op.get("wc") or "_NONE_"
                wc_available[wc_code] = max(
                    wc_available.get(wc_code, today_start), sched_end,
                )
                vp_prev_end[key] = max(
                    vp_prev_end.get(key, today_start), sched_end,
                )

    # --- Pass 2: idle ops → forward-schedule ---
    # VPs already sorted by is_hot DESC, priority ASC, co_due_date ASC
    for vp in vps:
        key = _vp_key(vp["job"], vp["suffix"])
        ops_sorted = sorted(
            [o for o in vp["operations"] if o["status"] == "idle"],
            key=lambda o: int(o["oper_num"] or "0")
            if (o["oper_num"] or "0").isdigit()
            else 0,
        )
        for op in ops_sorted:
            duration = _compute_duration_hrs(
                op.get("setup_hrs"), op.get("pcs_per_hour"), op.get("qty_released"),
            )
            op["duration_hrs"] = round(duration, 2)

            wc_code = op.get("wc") or "_NONE_"
            earliest = max(
                wc_available.get(wc_code, today_start),
                vp_prev_end.get(key, today_start),
                today_start,
            )
            sched_start = _clamp_to_work_start(earliest)
            sched_end = _add_work_hours(sched_start, duration)
            op["sched_start"] = sched_start.isoformat()
            op["sched_end"] = sched_end.isoformat()

            wc_available[wc_code] = sched_end
            vp_prev_end[key] = sched_end

    # --- Build wc_lanes ---
    wc_ops_map: Dict[str, List[Dict[str, Any]]] = {}
    for vp in vps:
        for op in vp["operations"]:
            wc_code = op.get("wc") or "_NONE_"
            wc_op = {
                "job": vp["job"],
                "suffix": vp["suffix"],
                "oper_num": op.get("oper_num"),
                "item": vp.get("item"),
                "description": vp.get("description"),
                "status": op["status"],
                "sched_start": op.get("sched_start"),
                "sched_end": op.get("sched_end"),
                "duration_hrs": op.get("duration_hrs"),
                "setup_hrs": op.get("setup_hrs"),
                "pcs_per_hour": op.get("pcs_per_hour"),
                "priority": vp.get("priority", 100),
                "is_hot": vp.get("is_hot", False),
                "co_due_date": vp.get("co_due_date"),
            }
            if wc_code not in wc_ops_map:
                wc_ops_map[wc_code] = []
            wc_ops_map[wc_code].append(wc_op)

    # Sort ops within each WC by sched_start
    wc_lanes = []
    for wc_code in sorted(wc_ops_map.keys()):
        ops = wc_ops_map[wc_code]
        ops.sort(key=lambda o: o.get("sched_start") or "9999")
        wc_lanes.append({"wc": wc_code, "ops": ops})

    return wc_lanes


# Property sets pro CO lookup přes IteRybPrehledZakazekView
_CO_VIEW_PROPS: List[str] = [
    "Item",
    "CoNum",
    "CoLine",
    "DueDate",
    "PromiseDate",
    "CustNum",
    "CustName",
    "QtyOrderedConv",
    "QtyShipped",
]


def _as_clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


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


def _parse_date(value: Any) -> Optional[date]:
    """Parse date string from Infor to date object.

    Handles formats: 2026-03-15, 2026-03-15T00:00:00, 15.03.2026, 03/15/2026,
    and Infor's compact format: 20260315 00:00:00.000
    """
    text = _as_clean_str(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except (ValueError, IndexError):
            continue
    # Infor compact: "20260315 00:00:00.000" or "20260315"
    try:
        return datetime.strptime(text[:8], "%Y%m%d").date()
    except (ValueError, IndexError):
        pass
    return None


def _op_status(row: Dict[str, Any]) -> str:
    """Determine operation status: done / in_progress / idle."""
    qty_released = _parse_float(row.get("JobQtyReleased")) or 0
    qty_complete = _parse_float(row.get("QtyComplete")) or 0
    qty_scrapped = _parse_float(row.get("QtyScrapped")) or 0
    if qty_released > 0 and (qty_complete + qty_scrapped) >= qty_released:
        return "done"
    if qty_complete > 0 or qty_scrapped > 0:
        return "in_progress"
    return "idle"


def _vp_key(job: str, suffix: str) -> str:
    return f"{job.upper()}|{(suffix or '0').strip()}"


async def _fetch_co_deadlines(
    infor_client,
    item_codes: List[str],
) -> Dict[str, Dict[str, Any]]:
    """CO deadline lookup pres IteRybPrehledZakazekView (otevrene zakazky).

    Returns: {ITEM_UPPER: {co_num, co_due_date (date), customer_name, ...}}
    Pri vice zakazkach na stejny item bere nejblizsi DueDate.
    """
    if not item_codes:
        return {}

    _BATCH = 200
    all_rows: List[Dict[str, Any]] = []

    for i in range(0, len(item_codes), _BATCH):
        batch = item_codes[i:i + _BATCH]
        quoted = ", ".join(
            "'" + code.replace("'", "''") + "'" for code in batch
        )
        filter_expr = f"Item IN ({quoted}) AND Stat = 'O'"

        try:
            result = await infor_client.load_collection(
                ido_name="IteRybPrehledZakazekView",
                properties=_CO_VIEW_PROPS,
                filter=filter_expr,
                order_by="DueDate ASC",
                record_cap=min(len(batch) * 5, 2000),
            )
            all_rows.extend(result.get("data", []))
        except Exception as exc:
            logger.warning("CO deadlines fetch failed for batch: %s", exc)

    # Group by Item, keep nearest DueDate
    result_map: Dict[str, Dict[str, Any]] = {}
    for row in all_rows:
        item = _as_clean_str(row.get("Item"))
        if not item:
            continue
        item_upper = item.upper()
        due_date = _parse_date(row.get("DueDate"))
        promise_date = _parse_date(row.get("PromiseDate"))
        effective_date = due_date or promise_date

        existing = result_map.get(item_upper)
        if existing and existing.get("co_due_date"):
            existing_date = existing["co_due_date"]
            if not effective_date or effective_date >= existing_date:
                continue

        result_map[item_upper] = {
            "co_num": _as_clean_str(row.get("CoNum")),
            "co_due_date": effective_date,
            "customer_name": _as_clean_str(row.get("CustName")),
            "qty_ordered": _parse_float(row.get("QtyOrderedConv")),
            "qty_shipped": _parse_float(row.get("QtyShipped")),
        }

    return result_map


async def fetch_planner_data(
    db: AsyncSession,
    infor_client,
    record_cap: int = 500,
) -> Dict[str, Any]:
    """VP-centricky Gantt data pro Production Planner."""

    # 1) Fetch all operations from Infor (all WC)
    raw_ops = await workshop_service.fetch_machine_plan(
        infor_client=infor_client,
        wc=None,
        record_cap=record_cap,
    )

    # 2) Group by VP (Job, Suffix) -> VP rows with operations[]
    vp_map: Dict[str, Dict[str, Any]] = {}
    for row in raw_ops:
        job = _as_clean_str(row.get("Job"))
        suffix = _as_clean_str(row.get("Suffix")) or "0"
        if not job:
            continue
        key = _vp_key(job, suffix)

        if key not in vp_map:
            vp_map[key] = {
                "job": job,
                "suffix": suffix,
                "item": _as_clean_str(row.get("DerJobItem")),
                "description": _as_clean_str(row.get("JobDescription")),
                "job_stat": _as_clean_str(row.get("JobStat")),
                "qty_released": _parse_float(row.get("JobQtyReleased")),
                "qty_complete": None,
                "qty_scrapped": None,
                "operations": [],
            }

        op_start = _parse_date(row.get("OpDatumSt"))
        op_end = _parse_date(row.get("OpDatumSp"))
        status = _op_status(row)

        setup_hrs = _parse_float(row.get("JshSetupHrs"))
        pcs_per_hour = _parse_float(row.get("DerRunMchHrs"))
        qty_released = _parse_float(row.get("JobQtyReleased"))

        vp_map[key]["operations"].append({
            "oper_num": _as_clean_str(row.get("OperNum")),
            "wc": _as_clean_str(row.get("Wc")),
            "status": status,
            "start_date": op_start.isoformat() if op_start else None,
            "end_date": op_end.isoformat() if op_end else None,
            "setup_hrs": setup_hrs,
            "pcs_per_hour": pcs_per_hour,
            "run_hrs": pcs_per_hour,  # legacy alias
            "qty_complete": _parse_float(row.get("QtyComplete")),
            "qty_released": qty_released,
        })

    # Skip VPs without operations
    vp_list = [vp for vp in vp_map.values() if vp["operations"]]

    # 3) vp_due_date = last OpDatumSp from its operations
    for vp in vp_list:
        end_dates = [
            _parse_date(op["end_date"])
            for op in vp["operations"]
            if op["end_date"]
        ]
        vp["vp_due_date"] = max(end_dates).isoformat() if end_dates else None

        # Aggregate qty from last operation
        ops_sorted = sorted(
            vp["operations"],
            key=lambda o: int(o["oper_num"] or "0") if (o["oper_num"] or "0").isdigit() else 0,
        )
        if ops_sorted:
            last_op = ops_sorted[-1]
            vp["qty_complete"] = last_op["qty_complete"]
            vp["qty_scrapped"] = _parse_float(None)  # Not available per-VP, keep None

    # 4) Extract unique Items -> fetch CO deadlines
    items = list({
        vp["item"].upper()
        for vp in vp_list
        if vp.get("item")
    })
    co_map = await _fetch_co_deadlines(infor_client, items)

    # 5) Load local priorities from DB
    stmt = select(ProductionPriority).where(ProductionPriority.deleted_at.is_(None))
    result = await db.execute(stmt)
    priorities = {
        _vp_key(p.infor_job, p.infor_suffix): p
        for p in result.scalars().all()
    }

    # 6) Merge: VP data + CO deadline + priority + is_hot
    today = date.today()

    for vp in vp_list:
        item_upper = (vp.get("item") or "").upper()
        co_info = co_map.get(item_upper, {})
        key = _vp_key(vp["job"], vp["suffix"])
        prio = priorities.get(key)

        vp["priority"] = prio.priority if prio else 100
        vp["is_hot"] = prio.is_hot if prio else False
        vp["tier"] = _derive_tier(vp["priority"], vp["is_hot"])
        vp["co_num"] = co_info.get("co_num")
        vp["co_due_date"] = co_info["co_due_date"].isoformat() if co_info.get("co_due_date") else None
        vp["customer_name"] = co_info.get("customer_name")

        # ops_done / ops_total
        vp["ops_total"] = len(vp["operations"])
        vp["ops_done"] = sum(1 for op in vp["operations"] if op["status"] == "done")

        # 7) is_delayed/delay_days — will be recomputed after scheduling (step 10)
        vp["is_delayed"] = False
        vp["delay_days"] = None

    # 8) Sort: is_hot DESC, priority ASC, co_due_date ASC
    def _sort_key(vp: Dict[str, Any]):
        # All done VPs go to the end
        all_done = all(op["status"] == "done" for op in vp["operations"])
        hot = vp.get("is_hot", False)
        priority = vp.get("priority", 100)
        co_due = vp.get("co_due_date") or "9999-12-31"
        return (all_done, not hot, priority, co_due)

    vp_list.sort(key=_sort_key)

    # 9) Forward-schedule operations
    wc_lanes = _schedule_operations(vp_list)

    # 10) Recompute is_delayed from last sched_end vs co_due_date
    for vp in vp_list:
        sched_ends = []
        for op in vp["operations"]:
            se = op.get("sched_end")
            if se:
                try:
                    sched_ends.append(datetime.fromisoformat(se))
                except (ValueError, TypeError):
                    pass
        if sched_ends:
            last_sched_end = max(sched_ends)
            co_due = _parse_date(vp.get("co_due_date"))
            if co_due and last_sched_end.date() > co_due:
                vp["is_delayed"] = True
                vp["delay_days"] = (last_sched_end.date() - co_due).days
            else:
                vp["is_delayed"] = False
                vp["delay_days"] = None

    # 11) Time range from sched_start/sched_end
    min_date = None
    max_date = None
    for vp in vp_list:
        for op in vp["operations"]:
            for dk in ("sched_start", "sched_end"):
                val = op.get(dk)
                if val:
                    try:
                        d = datetime.fromisoformat(val).date()
                        if min_date is None or d < min_date:
                            min_date = d
                        if max_date is None or d > max_date:
                            max_date = d
                    except (ValueError, TypeError):
                        pass

    if not min_date:
        min_date = today - timedelta(days=7)
    if not max_date:
        max_date = today + timedelta(days=30)
    max_date = max_date + timedelta(days=3)  # padding

    return {
        "vps": vp_list,
        "wc_lanes": wc_lanes,
        "time_range": {
            "min_date": min_date.isoformat(),
            "max_date": max_date.isoformat(),
        },
    }


async def set_priority(
    db: AsyncSession,
    job: str,
    suffix: str,
    priority: int,
    username: str,
) -> ProductionPriority:
    """Upsert priority for a VP."""
    safe_job = job.strip().upper()
    safe_suffix = (suffix or "0").strip()

    stmt = select(ProductionPriority).where(
        ProductionPriority.infor_job == safe_job,
        ProductionPriority.infor_suffix == safe_suffix,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.deleted_at:
            existing.deleted_at = None
            existing.deleted_by = None
        existing.priority = priority
        set_audit(existing, username, is_update=True)
        await safe_commit(db, existing, "set_priority")
        return existing

    entry = ProductionPriority(
        infor_job=safe_job,
        infor_suffix=safe_suffix,
        priority=priority,
    )
    set_audit(entry, username)
    db.add(entry)
    await safe_commit(db, entry, "set_priority")
    return entry


async def set_hot(
    db: AsyncSession,
    job: str,
    suffix: str,
    is_hot: bool,
    username: str,
) -> ProductionPriority:
    """Toggle hot flag. Multiple hot VPs allowed."""
    safe_job = job.strip().upper()
    safe_suffix = (suffix or "0").strip()

    stmt = select(ProductionPriority).where(
        ProductionPriority.infor_job == safe_job,
        ProductionPriority.infor_suffix == safe_suffix,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.deleted_at:
            existing.deleted_at = None
            existing.deleted_by = None
        existing.is_hot = is_hot
        set_audit(existing, username, is_update=True)
        await safe_commit(db, existing, "set_hot")
        return existing

    entry = ProductionPriority(
        infor_job=safe_job,
        infor_suffix=safe_suffix,
        is_hot=is_hot,
    )
    set_audit(entry, username)
    db.add(entry)
    await safe_commit(db, entry, "set_hot")
    return entry


async def set_tier(
    db: AsyncSession,
    job: str,
    suffix: str,
    tier: Literal['hot', 'urgent', 'normal'],
    username: str,
) -> ProductionPriority:
    """Nastavit tier (hot/urgent/normal) na VP. Upsert."""
    priority, is_hot = TIER_PRIORITY_MAP[tier]
    safe_job = job.strip().upper()
    safe_suffix = (suffix or "0").strip()

    stmt = select(ProductionPriority).where(
        ProductionPriority.infor_job == safe_job,
        ProductionPriority.infor_suffix == safe_suffix,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.deleted_at:
            existing.deleted_at = None
            existing.deleted_by = None
        existing.priority = priority
        existing.is_hot = is_hot
        set_audit(existing, username, is_update=True)
        await safe_commit(db, existing, "set_tier")
        return existing

    entry = ProductionPriority(
        infor_job=safe_job,
        infor_suffix=safe_suffix,
        priority=priority,
        is_hot=is_hot,
    )
    set_audit(entry, username)
    db.add(entry)
    await safe_commit(db, entry, "set_tier")
    return entry
