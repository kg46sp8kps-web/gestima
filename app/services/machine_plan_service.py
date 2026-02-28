"""GESTIMA - Machine Plan DnD Service

Merge logika: DB = poradnik (playlist), Infor = zdroj dat.
Lokalni DB uklada POUZE poradi (position). Cerstva data (qty, popis, datumy)
se vzdy ctou z Inforu.

Enrichment: kazdy radek obohacen o OrderDueDate (z CO pres Item matching)
a priority/hot flag z lokalni DB (production_priorities).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import set_audit
from app.models.machine_plan import MachinePlanEntry
from app.models.production_priority import ProductionPriority
from app.services import workshop_service
from app.services.production_planner_service import _fetch_co_deadlines, _derive_tier

logger = logging.getLogger(__name__)

# Type alias for VP key (job, suffix)
VpKey = Tuple[str, str]

# Type alias for operation key
OpKey = Tuple[str, str, str]  # (job, suffix, oper_num)


def _make_key(job: str, suffix: str, oper_num: str) -> OpKey:
    return (job.strip(), (suffix or "0").strip(), oper_num.strip())


def _entry_key(entry: MachinePlanEntry) -> OpKey:
    return _make_key(entry.infor_job, entry.infor_suffix, entry.oper_num)


def _infor_row_key(row: Dict[str, Any]) -> OpKey:
    return _make_key(
        str(row.get("Job", "")),
        str(row.get("Suffix", "0")),
        str(row.get("OperNum", "")),
    )


def _vp_key(job: str, suffix: str) -> VpKey:
    return (job.strip().upper(), (suffix or "0").strip())


def _enrich_rows(
    rows: List[Dict[str, Any]],
    co_map: Dict[str, Dict[str, Any]],
    priorities: Dict[VpKey, ProductionPriority],
) -> None:
    """Obohatit kazdy radek o OrderDueDate, IsHot, Tier z CO lookup + DB priorit."""
    for row in rows:
        item = str(row.get("DerJobItem", "")).strip().upper()
        job = str(row.get("Job", "")).strip().upper()
        suffix = str(row.get("Suffix", "0")).strip()

        # CO deadline (Item-based matching, nejdrivejsi DueDate)
        co_info = co_map.get(item, {})
        due_date = co_info.get("co_due_date")
        row["OrderDueDate"] = due_date.isoformat() if isinstance(due_date, date) else None
        row["CoNum"] = co_info.get("co_num")

        # Priority/hot z DB
        prio = priorities.get(_vp_key(job, suffix))
        row["IsHot"] = prio.is_hot if prio else False
        row["Priority"] = prio.priority if prio else 100
        row["Tier"] = _derive_tier(prio.priority, prio.is_hot) if prio else "normal"


def _planned_sort_key(row: Dict[str, Any]):
    """Razeni planned fronty: hot navrch, pak dle OrderDueDate ASC."""
    return (
        not row.get("IsHot", False),              # hot first
        row.get("OrderDueDate") or "9999-12-31",  # earliest due date first
    )


def _unassigned_sort_key(row: Dict[str, Any]):
    """Razeni neprirazene fronty (F/S/W): hot navrch, S dole, pak dle OrderDueDate ASC."""
    return (
        not row.get("IsHot", False),           # hot first
        row.get("JobStat", "R") == "S",        # stopped (S) at the end
        row.get("OrderDueDate") or "9999-12-31",  # earliest due date first
    )


async def get_plan(
    db: AsyncSession,
    wc: str,
    infor_client,
    record_cap: int = 500,
) -> Dict[str, List[Dict[str, Any]]]:
    """Vrati merged plan: lokalni poradi + cerstva Infor data.

    Split logika:
      - Planned = Released (R) operace, auto-prirazene dle DueDate.
        Pokud maji DnD pozici (lokalni DB), pouzije se ta.
      - Unassigned = Nereleased (F/S/W) operace.

    Kazdy radek obohacen o:
      - OrderDueDate: nejblizsi termin ze zakazkoveho radku (Item matching)
      - IsHot / Tier: z lokalni tabulky production_priorities

    Returns:
        {"planned": [...], "unassigned": [...]}
    """
    # 1. Nacti cerstva Infor data
    infor_rows = await workshop_service.fetch_machine_plan(
        infor_client=infor_client,
        wc=wc,
        record_cap=record_cap,
    )

    # 2. Nacti lokalni DnD pozice (pro manual reorder)
    result = await db.execute(
        select(MachinePlanEntry)
        .where(
            MachinePlanEntry.wc == wc,
            MachinePlanEntry.deleted_at.is_(None),
        )
        .order_by(MachinePlanEntry.position.asc())
    )
    local_entries: List[MachinePlanEntry] = list(result.scalars().all())
    local_lookup: Dict[OpKey, MachinePlanEntry] = {
        _entry_key(e): e for e in local_entries
    }

    # 3. Enrichment: CO deadlines + production priorities
    item_codes = list({
        str(row.get("DerJobItem", "")).strip().upper()
        for row in infor_rows
        if str(row.get("DerJobItem", "")).strip()
    })
    co_map = await _fetch_co_deadlines(infor_client, item_codes) if item_codes else {}

    prio_result = await db.execute(
        select(ProductionPriority).where(ProductionPriority.deleted_at.is_(None))
    )
    priorities: Dict[VpKey, ProductionPriority] = {
        _vp_key(p.infor_job, p.infor_suffix): p
        for p in prio_result.scalars().all()
    }

    _enrich_rows(infor_rows, co_map, priorities)
    logger.info(
        "Machine plan enrichment for wc=%s: %d infor rows, %d unique items, %d CO matches, %d priorities",
        wc, len(infor_rows), len(item_codes), len(co_map), len(priorities),
    )
    # Log per-item CO matches for debugging
    for row in infor_rows:
        item = str(row.get("DerJobItem", "")).strip()
        due = row.get("OrderDueDate")
        co = row.get("CoNum")
        if due:
            logger.debug("  wc=%s Job=%s Item=%s → OrderDueDate=%s CoNum=%s", wc, row.get("Job"), item, due, co)
        else:
            logger.debug("  wc=%s Job=%s Item=%s → no CO match", wc, row.get("Job"), item)

    # 4. Split: Released (R) → planned, ostatni (F/S/W) → unassigned
    positioned: List[Dict[str, Any]] = []     # Released with DnD position
    auto_released: List[Dict[str, Any]] = []  # Released without DnD position
    unassigned: List[Dict[str, Any]] = []
    stale_entries: List[MachinePlanEntry] = []

    for row in infor_rows:
        if workshop_service._is_operation_completed_row(row):
            # Completed → ani planned ani unassigned, ale cleanup DB entry
            key = _infor_row_key(row)
            local_entry = local_lookup.get(key)
            if local_entry:
                stale_entries.append(local_entry)
            continue

        job_stat = str(row.get("JobStat", "R")).strip().upper()

        if job_stat == "R":
            key = _infor_row_key(row)
            local_entry = local_lookup.get(key)
            merged = dict(row)
            if local_entry:
                merged["_position"] = local_entry.position
                positioned.append(merged)
            else:
                auto_released.append(merged)
        else:
            unassigned.append(dict(row))

    # 5. Stale DB entries (lokalni zaznam bez Infor protejsku)
    infor_keys = {_infor_row_key(r) for r in infor_rows}
    for entry in local_entries:
        key = _entry_key(entry)
        if key not in infor_keys:
            stale_entries.append(entry)

    # 6. Planned = hot vždy nahoře, pak DnD-positioned, pak auto-released dle DueDate
    hot_items: List[Dict[str, Any]] = []
    non_hot_positioned: List[Dict[str, Any]] = []
    non_hot_auto: List[Dict[str, Any]] = []

    for r in positioned:
        if r.get("IsHot"):
            hot_items.append(r)
        else:
            non_hot_positioned.append(r)
    for r in auto_released:
        if r.get("IsHot"):
            hot_items.append(r)
        else:
            non_hot_auto.append(r)

    hot_items.sort(key=lambda r: r.get("OrderDueDate") or "9999-12-31")
    non_hot_positioned.sort(key=lambda r: r.get("_position", 9999))
    non_hot_auto.sort(key=_planned_sort_key)
    planned = hot_items + non_hot_positioned + non_hot_auto

    # 7. Unassigned = F/S/W, sorted
    unassigned.sort(key=_unassigned_sort_key)

    # 8. Auto-cleanup stale entries (soft-delete)
    if stale_entries:
        now = datetime.utcnow()
        for entry in stale_entries:
            entry.deleted_at = now
            entry.deleted_by = "system:auto-cleanup"
        await db.commit()
        logger.info("Machine plan auto-cleanup: soft-deleted %d stale entries for wc=%s", len(stale_entries), wc)

    return {"planned": planned, "unassigned": unassigned}


async def reorder(
    db: AsyncSession,
    wc: str,
    ordered_keys: List[Dict[str, str]],
    username: str,
) -> int:
    """Bulk update pozic — mistr pretahl DnD -> nove poradi.

    Args:
        ordered_keys: list of {"job": ..., "suffix": ..., "oper_num": ...}

    Returns:
        Number of entries updated/created.
    """
    # Load existing entries for this WC
    result = await db.execute(
        select(MachinePlanEntry).where(
            MachinePlanEntry.wc == wc,
        )
    )
    existing: Dict[OpKey, MachinePlanEntry] = {}
    for entry in result.scalars().all():
        existing[_entry_key(entry)] = entry

    count = 0
    for position, key_data in enumerate(ordered_keys):
        key = _make_key(key_data["job"], key_data.get("suffix", "0"), key_data["oper_num"])
        entry = existing.get(key)

        if entry is not None:
            # Update existing (restore if soft-deleted)
            entry.position = position
            if entry.deleted_at is not None:
                entry.deleted_at = None
                entry.deleted_by = None
            set_audit(entry, username, is_update=True)
        else:
            # Create new
            entry = MachinePlanEntry(
                wc=wc,
                infor_job=key[0],
                infor_suffix=key[1],
                oper_num=key[2],
                position=position,
            )
            set_audit(entry, username)
            db.add(entry)
        count += 1

    await db.commit()
    return count


async def add_to_plan(
    db: AsyncSession,
    wc: str,
    job: str,
    suffix: str,
    oper_num: str,
    username: str,
    position: Optional[int] = None,
) -> MachinePlanEntry:
    """Pridat operaci do planu. position=None -> MAX(position)+1."""
    key = _make_key(job, suffix, oper_num)

    # Check for existing entry (including soft-deleted)
    result = await db.execute(
        select(MachinePlanEntry).where(
            MachinePlanEntry.wc == wc,
            MachinePlanEntry.infor_job == key[0],
            MachinePlanEntry.infor_suffix == key[1],
            MachinePlanEntry.oper_num == key[2],
        )
    )
    entry = result.scalar_one_or_none()

    if position is None:
        # MAX(position) + 1
        max_result = await db.execute(
            select(func.max(MachinePlanEntry.position)).where(
                MachinePlanEntry.wc == wc,
                MachinePlanEntry.deleted_at.is_(None),
            )
        )
        max_pos = max_result.scalar() or -1
        position = max_pos + 1

    if entry is not None:
        # Restore if soft-deleted, update position
        entry.position = position
        entry.deleted_at = None
        entry.deleted_by = None
        set_audit(entry, username, is_update=True)
    else:
        entry = MachinePlanEntry(
            wc=wc,
            infor_job=key[0],
            infor_suffix=key[1],
            oper_num=key[2],
            position=position,
        )
        set_audit(entry, username)
        db.add(entry)

    await db.commit()
    await db.refresh(entry)
    return entry


async def remove_from_plan(
    db: AsyncSession,
    wc: str,
    job: str,
    suffix: str,
    oper_num: str,
    username: str,
) -> bool:
    """Soft-delete operace z planu. Returns True if found and deleted."""
    key = _make_key(job, suffix, oper_num)

    result = await db.execute(
        select(MachinePlanEntry).where(
            MachinePlanEntry.wc == wc,
            MachinePlanEntry.infor_job == key[0],
            MachinePlanEntry.infor_suffix == key[1],
            MachinePlanEntry.oper_num == key[2],
            MachinePlanEntry.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        return False

    entry.deleted_at = datetime.utcnow()
    entry.deleted_by = username
    await db.commit()
    return True
