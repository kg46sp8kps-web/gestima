"""GESTIMA - Operator Service

Servisní vrstva pro operátorský terminál.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workshop_transaction import WorkshopTransaction
from app.models.workshop_job_route import WorkshopJobRoute
from app.models.enums import WorkshopTransType, WorkshopTxStatus

logger = logging.getLogger(__name__)


def _to_utc_iso(value: datetime | None) -> str | None:
    """Serialize datetime as explicit UTC ISO-8601 (with trailing Z)."""
    if value is None:
        return None

    if value.tzinfo is None:
        dt_utc = value.replace(tzinfo=timezone.utc)
    else:
        dt_utc = value.astimezone(timezone.utc)
    return dt_utc.isoformat().replace("+00:00", "Z")


def _to_utc_sort_key(value: datetime) -> datetime:
    """Normalize datetime for stable ordering (UTC naive key)."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def get_active_jobs(db: AsyncSession, username: str) -> List[Dict[str, Any]]:
    """Get jobs where user has started but not yet stopped work."""
    # Local active-jobs mirror must track only successfully posted Infor writes.
    # FAILED/PENDING transactions must not open/close runtime state.
    start_types = [WorkshopTransType.START, WorkshopTransType.SETUP_START]
    stop_types = [WorkshopTransType.STOP, WorkshopTransType.SETUP_END]
    relevant_types = start_types + stop_types

    tx_result = await db.execute(
        select(WorkshopTransaction).where(
            WorkshopTransaction.created_by == username,
            WorkshopTransaction.trans_type.in_(relevant_types),
            WorkshopTransaction.status == WorkshopTxStatus.POSTED,
            WorkshopTransaction.deleted_at.is_(None),
        ).order_by(
            WorkshopTransaction.created_at.asc(),
            WorkshopTransaction.id.asc(),
        )
    )
    txs = list(tx_result.scalars().all())

    # Pair starts/stops in chronological order, per Job+Suffix+Oper.
    stacks: Dict[tuple[str, str, str], Dict[str, List[WorkshopTransaction]]] = {}
    for tx in txs:
        key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
        bucket = stacks.setdefault(key, {"setup": [], "production": []})

        if tx.trans_type == WorkshopTransType.SETUP_START:
            bucket["setup"].append(tx)
        elif tx.trans_type == WorkshopTransType.START:
            bucket["production"].append(tx)
        elif tx.trans_type == WorkshopTransType.SETUP_END:
            if bucket["setup"]:
                bucket["setup"].pop()
            elif bucket["production"]:
                # Defensive fallback for malformed historical data.
                bucket["production"].pop()
        elif tx.trans_type == WorkshopTransType.STOP:
            if bucket["production"]:
                bucket["production"].pop()
            elif bucket["setup"]:
                # Defensive fallback for malformed historical data.
                bucket["setup"].pop()

    active_rows: List[tuple[datetime, Dict[str, Any]]] = []
    for bucket in stacks.values():
        for tx in bucket["setup"] + bucket["production"]:
            started_at = tx.started_at or tx.created_at or datetime.utcnow()
            active_rows.append((
                _to_utc_sort_key(started_at),
                {
                    "job": tx.infor_job,
                    "suffix": tx.infor_suffix or "0",
                    "oper_num": tx.oper_num,
                    "wc": tx.wc,
                    "item": tx.infor_item,
                    "trans_type": tx.trans_type.value,
                    "started_at": _to_utc_iso(started_at),
                },
            ))

    active_rows.sort(key=lambda row: row[0], reverse=True)

    # Enrich with workshop_job_routes data (description, qty, dates, etc.)
    if active_rows:
        keys = [(r["job"], r.get("suffix") or "0", r["oper_num"]) for _, r in active_rows]
        from sqlalchemy import tuple_
        route_result = await db.execute(
            select(WorkshopJobRoute).where(
                tuple_(
                    WorkshopJobRoute.job,
                    WorkshopJobRoute.suffix,
                    WorkshopJobRoute.oper_num,
                ).in_(keys)
            )
        )
        route_map = {
            (r.job, r.suffix or "0", r.oper_num): r
            for r in route_result.scalars().all()
        }
        for _, row in active_rows:
            route = route_map.get((row["job"], row.get("suffix") or "0", row["oper_num"]))
            if route:
                row["description"] = route.job_description
                row["der_job_item"] = route.der_job_item
                row["job_stat"] = route.job_stat
                row["qty_released"] = route.job_qty_released
                row["qty_complete"] = route.qty_complete
                row["op_datum_st"] = route.op_datum_st
                row["op_datum_sp"] = route.op_datum_sp
            else:
                row["description"] = None
                row["der_job_item"] = row.get("item")
                row["job_stat"] = None
                row["qty_released"] = None
                row["qty_complete"] = None
                row["op_datum_st"] = None
                row["op_datum_sp"] = None

    return [row for _, row in active_rows]


async def get_operator_stats(db: AsyncSession, username: str) -> Dict[str, Any]:
    """Get operator statistics for today and this week."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monday of current week
    week_start = today_start - timedelta(days=today_start.weekday())

    # Today's stats
    today_result = await db.execute(
        select(
            func.coalesce(func.sum(WorkshopTransaction.actual_hours), 0).label("hours"),
            func.coalesce(func.sum(WorkshopTransaction.qty_completed), 0).label("pieces"),
            func.coalesce(func.sum(WorkshopTransaction.qty_scrapped), 0).label("scrap"),
        ).where(
            WorkshopTransaction.created_by == username,
            WorkshopTransaction.trans_type == WorkshopTransType.STOP,
            WorkshopTransaction.created_at >= today_start,
            WorkshopTransaction.deleted_at.is_(None),
        )
    )
    today = today_result.one()

    # Week stats
    week_result = await db.execute(
        select(
            func.coalesce(func.sum(WorkshopTransaction.actual_hours), 0).label("hours"),
            func.coalesce(func.sum(WorkshopTransaction.qty_completed), 0).label("pieces"),
        ).where(
            WorkshopTransaction.created_by == username,
            WorkshopTransaction.trans_type == WorkshopTransType.STOP,
            WorkshopTransaction.created_at >= week_start,
            WorkshopTransaction.deleted_at.is_(None),
        )
    )
    week = week_result.one()

    return {
        "today_hours": round(float(today.hours), 2),
        "today_pieces": int(today.pieces),
        "today_scrap": int(today.scrap),
        "week_hours": round(float(week.hours), 2),
        "week_pieces": int(week.pieces),
    }


async def get_available_workcenters(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get distinct work centers from workshop_job_routes with operation counts."""
    result = await db.execute(
        select(
            WorkshopJobRoute.wc,
            func.count(WorkshopJobRoute.id).label("oper_count"),
        ).where(
            WorkshopJobRoute.wc.isnot(None),
            WorkshopJobRoute.job_stat.in_(["R", "F", "S"]),  # Released, Firm, Started
        ).group_by(
            WorkshopJobRoute.wc
        ).order_by(
            WorkshopJobRoute.wc
        )
    )
    rows = result.all()
    return [{"wc": row.wc, "oper_count": row.oper_count} for row in rows]


def _tx_severity(status: WorkshopTxStatus) -> str:
    if status == WorkshopTxStatus.FAILED:
        return "error"
    if status in {WorkshopTxStatus.PENDING, WorkshopTxStatus.POSTING}:
        return "warning"
    return "info"


async def get_transaction_alerts(
    db: AsyncSession,
    username: str,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Unresolved workshop transactions for operator terminal (pending/posting/failed)."""
    unresolved_statuses = [
        WorkshopTxStatus.PENDING,
        WorkshopTxStatus.POSTING,
        WorkshopTxStatus.FAILED,
    ]

    result = await db.execute(
        select(WorkshopTransaction).where(
            WorkshopTransaction.created_by == username,
            WorkshopTransaction.status.in_(unresolved_statuses),
            WorkshopTransaction.deleted_at.is_(None),
        ).order_by(WorkshopTransaction.created_at.desc()).limit(limit)
    )
    txs = list(result.scalars().all())
    if not txs:
        return []

    active_jobs = await get_active_jobs(db, username)
    active_keys = {
        (job["job"], job.get("suffix") or "0", job["oper_num"])
        for job in active_jobs
    }

    alerts: List[Dict[str, Any]] = []
    for tx in txs:
        key = (tx.infor_job, tx.infor_suffix or "0", tx.oper_num)
        blocks_running = (
            tx.trans_type in {WorkshopTransType.STOP, WorkshopTransType.SETUP_END}
            and key in active_keys
        )
        alerts.append(
            {
                "id": tx.id,
                "job": tx.infor_job,
                "suffix": tx.infor_suffix or "0",
                "oper_num": tx.oper_num,
                "wc": tx.wc,
                "trans_type": tx.trans_type.value,
                "status": tx.status.value,
                "severity": _tx_severity(tx.status),
                "error_msg": tx.error_msg,
                "created_at": _to_utc_iso(tx.created_at),
                "updated_at": _to_utc_iso(tx.updated_at),
                "started_at": _to_utc_iso(tx.started_at),
                "finished_at": _to_utc_iso(tx.finished_at),
                "retry_allowed": tx.status in {WorkshopTxStatus.PENDING, WorkshopTxStatus.FAILED},
                "blocks_running": blocks_running,
            }
        )

    return alerts
