"""GESTIMA — Norm Performance Service

Výpočet plnění norem zaměstnanců:
  - get_norm_summary(): agregované % plnění pro dashboard dlaždice
  - get_norm_details(): per-operace detail pro drill-down overlay

Zdroj skutečných dat: infor_job_transactions (SLJobTrans mirror)
Zdroj plánovaných dat: workshop_job_routes (SLJobRoutes Type='J')

Vzorce:
  planned_min_per_piece = 60 / DerRunMchHrs  (pokud DerRunMchHrs > 0)
  planned_setup_min = JshSetupHrs * 60
  planned_run_min = planned_min_per_piece * qty_complete
  run_fulfillment_pct = (planned_run_min / actual_run_min) * 100
  >100% = rychlejší než norma, <100% = pomalejší
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.infor_job_transaction import InforJobTransaction
from app.models.workshop_job_route import WorkshopJobRoute

logger = logging.getLogger(__name__)

Period = Literal["day", "week", "month"]


def _period_range(period: Period) -> tuple[str, str]:
    """Return (start_date, end_date) as YYYY-MM-DD strings for given period."""
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")

    if period == "day":
        return today, today
    elif period == "week":
        monday = now - timedelta(days=now.weekday())
        return monday.strftime("%Y-%m-%d"), today
    else:  # month
        first_of_month = now.replace(day=1)
        return first_of_month.strftime("%Y-%m-%d"), today


async def _fetch_transactions(
    db: AsyncSession,
    emp_num: str,
    period: Optional[Period] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[InforJobTransaction]:
    """Fetch job transactions for employee within period or custom date range."""
    if date_from and date_to:
        start_date, end_date = date_from, date_to
    elif period:
        start_date, end_date = _period_range(period)
    else:
        start_date, end_date = _period_range("day")

    result = await db.execute(
        select(InforJobTransaction).where(
            InforJobTransaction.emp_num == emp_num,
            InforJobTransaction.trans_date >= start_date,
            InforJobTransaction.trans_date <= end_date + "Z",  # include full last day
            InforJobTransaction.trans_type.in_(["R", "S"]),  # only Run + Setup, skip C (Complete)
        )
    )
    return list(result.scalars().all())


async def _fetch_route_map(
    db: AsyncSession, keys: List[tuple[str, str, str]]
) -> Dict[tuple[str, str, str], WorkshopJobRoute]:
    """Batch fetch workshop_job_routes for given (job, suffix, oper_num) keys."""
    if not keys:
        return {}

    result = await db.execute(select(WorkshopJobRoute))
    route_map: Dict[tuple[str, str, str], WorkshopJobRoute] = {}
    for r in result.scalars().all():
        route_map[(r.job, r.suffix, r.oper_num)] = r

    # Filter to only requested keys
    return {k: route_map[k] for k in keys if k in route_map}


def _calc_planned(route: WorkshopJobRoute | None, qty: float) -> Dict[str, float | None]:
    """Calculate planned times from route norms."""
    if not route:
        return {
            "planned_min_per_piece": None,
            "planned_setup_min": None,
            "planned_run_min": None,
        }

    der_run = route.der_run_mch_hrs
    planned_min_per_piece = None
    planned_run_min = None

    if der_run and der_run > 0:
        planned_min_per_piece = round(60.0 / der_run, 2)
        planned_run_min = round(planned_min_per_piece * qty, 2) if qty else None

    planned_setup_min = None
    if route.jsh_setup_hrs is not None:
        planned_setup_min = round(route.jsh_setup_hrs * 60.0, 2)

    return {
        "planned_min_per_piece": planned_min_per_piece,
        "planned_setup_min": planned_setup_min,
        "planned_run_min": planned_run_min,
    }


def _compute_summary(txs: List[InforJobTransaction], route_map: Dict) -> Dict[str, Any]:
    """Shared summary computation from transactions + route map."""
    total_actual_run = 0.0
    total_planned_run = 0.0
    total_actual_setup = 0.0
    total_planned_setup = 0.0
    total_qty = 0
    total_scrap = 0

    for tx in txs:
        qty = tx.qty_complete or 0
        actual_run = (tx.run_hrs_t or 0) * 60.0
        actual_setup = (tx.setup_hrs_t or 0) * 60.0

        key = (tx.job, tx.suffix or "0", tx.oper_num or "")
        route = route_map.get(key)
        planned = _calc_planned(route, qty)

        total_actual_run += actual_run
        total_actual_setup += actual_setup
        total_qty += int(qty)
        total_scrap += int(tx.qty_scrapped or 0)

        if planned["planned_run_min"] is not None:
            total_planned_run += planned["planned_run_min"]
        if planned["planned_setup_min"] is not None:
            total_planned_setup += planned["planned_setup_min"]

    run_pct = None
    if total_actual_run > 0 and total_planned_run > 0:
        run_pct = round((total_planned_run / total_actual_run) * 100, 1)

    setup_pct = None
    if total_actual_setup > 0 and total_planned_setup > 0:
        setup_pct = round((total_planned_setup / total_actual_setup) * 100, 1)

    # Combined overall fulfillment (run + setup together)
    total_actual_all = total_actual_run + total_actual_setup
    total_planned_all = total_planned_run + total_planned_setup
    overall_pct = None
    if total_actual_all > 0 and total_planned_all > 0:
        overall_pct = round((total_planned_all / total_actual_all) * 100, 1)

    return {
        "run_fulfillment_pct": run_pct,
        "setup_fulfillment_pct": setup_pct,
        "overall_fulfillment_pct": overall_pct,
        "total_actual_run_min": round(total_actual_run, 1),
        "total_planned_run_min": round(total_planned_run, 1),
        "total_actual_setup_min": round(total_actual_setup, 1),
        "total_planned_setup_min": round(total_planned_setup, 1),
        "total_qty": total_qty,
        "total_scrap": total_scrap,
        "operation_count": len(txs),
    }


_EMPTY_SUMMARY: Dict[str, Any] = {
    "run_fulfillment_pct": None,
    "setup_fulfillment_pct": None,
    "overall_fulfillment_pct": None,
    "total_actual_run_min": 0,
    "total_planned_run_min": 0,
    "total_actual_setup_min": 0,
    "total_planned_setup_min": 0,
    "total_qty": 0,
    "total_scrap": 0,
    "operation_count": 0,
}


async def get_norm_summary(
    db: AsyncSession,
    emp_num: str,
    period: Optional[Period] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregated norm fulfillment for dashboard tiles."""
    txs = await _fetch_transactions(db, emp_num, period=period, date_from=date_from, date_to=date_to)

    if not txs:
        return dict(_EMPTY_SUMMARY)

    tx_keys = list({(tx.job, tx.suffix or "0", tx.oper_num or "") for tx in txs})
    route_map = await _fetch_route_map(db, tx_keys)

    return _compute_summary(txs, route_map)


async def get_norm_details(
    db: AsyncSession,
    emp_num: str,
    period: Optional[Period] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Per-operation detail for drill-down overlay."""
    txs = await _fetch_transactions(db, emp_num, period=period, date_from=date_from, date_to=date_to)

    if not txs:
        return []

    tx_keys = list({(tx.job, tx.suffix or "0", tx.oper_num or "") for tx in txs})
    route_map = await _fetch_route_map(db, tx_keys)

    details: List[Dict[str, Any]] = []

    for tx in txs:
        qty = tx.qty_complete or 0
        actual_run_min = round((tx.run_hrs_t or 0) * 60.0, 2)
        actual_setup_min = round((tx.setup_hrs_t or 0) * 60.0, 2)

        key = (tx.job, tx.suffix or "0", tx.oper_num or "")
        route = route_map.get(key)
        planned = _calc_planned(route, qty)

        run_pct = None
        if actual_run_min > 0 and planned["planned_run_min"] is not None and planned["planned_run_min"] > 0:
            run_pct = round((planned["planned_run_min"] / actual_run_min) * 100, 1)

        setup_pct = None
        if actual_setup_min > 0 and planned["planned_setup_min"] is not None and planned["planned_setup_min"] > 0:
            setup_pct = round((planned["planned_setup_min"] / actual_setup_min) * 100, 1)

        # Combined overall for this transaction
        total_actual = actual_run_min + actual_setup_min
        total_planned = (planned["planned_run_min"] or 0) + (planned["planned_setup_min"] or 0)
        overall_pct = None
        if total_actual > 0 and total_planned > 0:
            overall_pct = round((total_planned / total_actual) * 100, 1)

        details.append({
            "trans_date": tx.trans_date,
            "job": tx.job,
            "suffix": tx.suffix or "0",
            "oper_num": tx.oper_num,
            "wc": tx.wc,
            "trans_type": tx.trans_type,
            "der_job_item": route.der_job_item if route else None,
            "job_description": route.job_description if route else None,
            "qty_complete": int(qty),
            "qty_scrapped": int(tx.qty_scrapped or 0),
            "actual_run_min": actual_run_min,
            "actual_setup_min": actual_setup_min,
            "planned_min_per_piece": planned["planned_min_per_piece"],
            "planned_setup_min": planned["planned_setup_min"],
            "planned_run_min": planned["planned_run_min"],
            "run_fulfillment_pct": run_pct,
            "setup_fulfillment_pct": setup_pct,
            "overall_fulfillment_pct": overall_pct,
        })

    # Sort by trans_date desc, then job
    details.sort(key=lambda d: (d["trans_date"] or "", d["job"] or ""), reverse=True)

    return details
