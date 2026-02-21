"""GESTIMA - Accounting Router (CsiXls Proxy)

Read-only proxy for CsiXls API — account balances and turnovers.
No database storage, in-memory caching only.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.dependencies import require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.accounting import (
    AccountBalance,
    AccountTurnover,
    AssetCategory,
    BalanceCell,
    BalancePivotResponse,
    CostCategory,
    CostCenterSummary,
    CostTypeMonthly,
    DashboardBalanceSheetResponse,
    DashboardCostsResponse,
    DashboardMachinesResponse,
    DashboardOverviewResponse,
    DashboardRevenueResponse,
    MachineCost,
    MonthlyPnL,
    RevenueStream,
    TopAccount,
    TurnoverRecord,
    TurnoverResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounting", tags=["Accounting"])

# Simple in-memory cache (TTL-based)
_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


async def _fetch_csixls(endpoint: str) -> List[Dict[str, Any]]:
    """Fetch raw data from CsiXls API."""
    if not settings.CSIXLS_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="CsiXls API not configured. Set CSIXLS_API_TOKEN in .env",
        )

    url = f"{settings.CSIXLS_API_URL}/{endpoint}"
    headers = {"Kovo-Xls-Token": settings.CSIXLS_API_TOKEN}

    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("CsiXls API error: %s for %s", e.response.status_code, url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"CsiXls API error: {e.response.status_code}",
        )
    except Exception as e:
        logger.error("CsiXls API connection failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CsiXls API connection failed",
        )


def _get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if time.time() - cached_time < _CACHE_TTL_SECONDS:
            return cached_data
    return None


def _set_cached(key: str, data: Any) -> None:
    """Store value in cache."""
    _cache[key] = (time.time(), data)


@router.get("/balances", response_model=BalancePivotResponse)
async def get_balances(
    rok: int = 2026,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> BalancePivotResponse:
    """
    Account balances pivot table (ZustNaUctech).

    Returns accounts × months matrix with pocatecni/konecny values.
    Cached for 1 hour.
    """
    cache_key = f"balances_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    raw_data = await _fetch_csixls(f"ZustNaUctech/{rok}")

    # Build pivot
    cells: Dict[str, Dict[str, BalanceCell]] = {}
    account_names: Dict[str, str] = {}

    for record in raw_data:
        item = AccountBalance(**record)
        account_names[item.ucet] = item.popis
        if item.ucet not in cells:
            cells[item.ucet] = {}
        cells[item.ucet][str(item.mesic)] = BalanceCell(
            pocatecni=item.pocatecni,
            konecny=item.konecny,
        )

    accounts = sorted(account_names.keys())
    non_zero = sum(
        1
        for ucet in accounts
        if any(
            c.konecny != 0.0 or c.pocatecni != 0.0
            for c in cells.get(ucet, {}).values()
        )
    )

    result = BalancePivotResponse(
        rok=rok,
        accounts=accounts,
        account_names=account_names,
        months=list(range(1, 13)),
        cells=cells,
        total_records=len(raw_data),
        non_zero_accounts=non_zero,
    )
    _set_cached(cache_key, result)
    return result


@router.get("/turnovers", response_model=TurnoverResponse)
async def get_turnovers(
    rok: int = 2026,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> TurnoverResponse:
    """
    Account turnovers with analytics dimensions (ZustNaDan).

    Returns flat records with Md/Dal and dAn1-4 analytics.
    Cached for 1 hour.
    """
    cache_key = f"turnovers_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    raw_data = await _fetch_csixls(f"ZustNaDan/{rok}")

    records: List[TurnoverRecord] = []
    analytics: Dict[str, set[str]] = {
        "dAn1": set(),
        "dAn2": set(),
        "dAn3": set(),
    }
    non_zero = 0

    for record in raw_data:
        item = AccountTurnover(**record)
        # Clean whitespace from analytics
        d1 = item.dAn1.strip()
        d2 = item.dAn2.strip()
        d3 = item.dAn3.strip()
        d4 = item.dAn4.strip()

        if d1:
            analytics["dAn1"].add(d1)
        if d2:
            analytics["dAn2"].add(d2)
        if d3:
            analytics["dAn3"].add(d3)

        is_nonzero = abs(item.md) > 0.001 or abs(item.dal) > 0.001
        if is_nonzero:
            non_zero += 1

        records.append(
            TurnoverRecord(
                ucet=item.ucet,
                popis=item.popis,
                mesic=item.mesic,
                md=item.md,
                dal=item.dal,
                dAn1=d1,
                dAn2=d2,
                dAn3=d3,
                dAn4=d4,
            )
        )

    result = TurnoverResponse(
        rok=rok,
        records=records,
        total_records=len(raw_data),
        non_zero_records=non_zero,
        analytics={k: sorted(v) for k, v in analytics.items()},
    )
    _set_cached(cache_key, result)
    return result


@router.post("/refresh", response_model=dict)
async def refresh_cache(
    rok: int = 2026,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> Dict[str, str]:
    """Force refresh cached data for given year."""
    keys_to_remove = [k for k in _cache if k.endswith(f"_{rok}")]
    for key in keys_to_remove:
        del _cache[key]
    return {"message": f"Cache cleared for year {rok}"}


# Dashboard constants

COST_CENTER_LABELS: Dict[str, str] = {
    "100": "Výroba",
    "110": "Výroba II",
    "120": "Údržba",
    "130": "Řízení",
    "140": "Kontrola",
    "150": "Technologie",
    "160": "Expedice",
    "170": "Nástrojárna",
    "180": "Správa budov",
    "190": "Pomocné",
    "210": "Kooperace",
    "250": "Služby",
    "310": "Sklad",
    "320": "Pronájem",
    "410": "Finance",
    "500": "Správa",
    "510": "Management",
    "520": "Personální",
    "610": "Kooperace ext.",
    "620": "Nákup",
    "999": "Pomocné",
}

EXPENSE_CATEGORIES: Dict[str, str] = {
    "501": "Spotřeba materiálu",
    "502": "Spotřeba energií",
    "504": "Prodané zboží",
    "511": "Opravy a údržba",
    "512": "Cestovné",
    "513": "Reprezentace",
    "518": "Ostatní služby",
    "521": "Mzdové náklady",
    "522": "Mzdy společníků",
    "524": "Sociální pojištění",
    "527": "Pojištění zaměstnanců",
    "531": "Silniční daň",
    "538": "Ostatní daně",
    "541": "ZC prodaného DM",
    "543": "Dary",
    "548": "Ostatní provozní",
    "551": "Odpisy",
    "562": "Úroky",
    "563": "Kurzové ztráty",
    "568": "Ostatní finanční",
    "581": "Změna stavu NV",
    "583": "Změna stavu výrobků",
}


# Dashboard helpers


def _aggregate_pnl(turnover_data: List[Dict[str, Any]]) -> Tuple[List[MonthlyPnL], float, float, float, float]:
    """
    Aggregate P&L from turnover data.

    Returns:
        Tuple of (monthly_pnl, ytd_revenue, ytd_expenses, ytd_profit, ytd_margin_pct)
    """
    monthly_dict: Dict[int, Dict[str, float]] = {m: {"revenue": 0.0, "expenses": 0.0} for m in range(1, 13)}

    for record in turnover_data:
        item = AccountTurnover(**record)
        ucet = item.ucet.strip()
        mesic = item.mesic

        # Exclude 58x internal transfers from P&L
        if ucet.startswith("58"):
            continue

        if ucet.startswith("6"):
            # Revenue (6xx accounts) - dal side
            monthly_dict[mesic]["revenue"] += item.dal
        elif ucet.startswith("5"):
            # Expenses (5xx accounts) - md side
            monthly_dict[mesic]["expenses"] += item.md

    monthly_pnl: List[MonthlyPnL] = []
    ytd_revenue = 0.0
    ytd_expenses = 0.0

    for mesic in range(1, 13):
        revenue = monthly_dict[mesic]["revenue"]
        expenses = monthly_dict[mesic]["expenses"]
        profit = revenue - expenses

        ytd_revenue += revenue
        ytd_expenses += expenses

        monthly_pnl.append(
            MonthlyPnL(
                mesic=mesic,
                revenue=revenue,
                expenses=expenses,
                profit=profit,
            )
        )

    ytd_profit = ytd_revenue - ytd_expenses
    ytd_margin_pct = (ytd_profit / ytd_revenue * 100.0) if ytd_revenue > 0 else 0.0

    return monthly_pnl, ytd_revenue, ytd_expenses, ytd_profit, ytd_margin_pct


def _safe_pct_change(current: float, previous: float) -> Optional[float]:
    """
    Calculate percentage change. Returns None if previous is 0.
    """
    if abs(previous) < 0.01:
        return None
    return ((current - previous) / abs(previous)) * 100.0


# Dashboard endpoints


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    rok: int = Query(default=datetime.now().year, ge=2000, le=2100),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> DashboardOverviewResponse:
    """
    Dashboard overview with monthly P&L and key balance sheet metrics.

    Revenue from 6xx accounts, expenses from 5xx accounts (excluding 58x internal transfers).
    Includes YoY comparison with previous year data.
    Cached for 1 hour.
    """
    cache_key = f"dashboard_overview_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        # Fetch current and previous year data in parallel
        curr_balance: Optional[List[Dict[str, Any]]] = None
        curr_turnover: Optional[List[Dict[str, Any]]] = None
        prev_balance: Optional[List[Dict[str, Any]]] = None
        prev_turnover: Optional[List[Dict[str, Any]]] = None

        try:
            (curr_balance, curr_turnover), (prev_balance, prev_turnover) = await asyncio.gather(
                asyncio.gather(
                    _fetch_csixls(f"ZustNaUctech/{rok}"),
                    _fetch_csixls(f"ZustNaDan/{rok}"),
                ),
                asyncio.gather(
                    _fetch_csixls(f"ZustNaUctech/{rok - 1}"),
                    _fetch_csixls(f"ZustNaDan/{rok - 1}"),
                ),
            )
        except Exception:
            # If previous year fails (403 etc), still return current year
            curr_balance = await _fetch_csixls(f"ZustNaUctech/{rok}")
            curr_turnover = await _fetch_csixls(f"ZustNaDan/{rok}")
            prev_balance = None
            prev_turnover = None

        # Aggregate current year P&L
        monthly_pnl, ytd_revenue, ytd_expenses, ytd_profit, ytd_margin_pct = _aggregate_pnl(curr_turnover)

        # Aggregate previous year P&L if available
        prev_monthly: Optional[List[MonthlyPnL]] = None
        prev_ytd_revenue: Optional[float] = None
        prev_ytd_expenses: Optional[float] = None
        prev_ytd_profit: Optional[float] = None
        prev_ytd_margin_pct: Optional[float] = None

        if prev_turnover is not None:
            prev_monthly, prev_ytd_revenue, prev_ytd_expenses, prev_ytd_profit, prev_ytd_margin_pct = _aggregate_pnl(prev_turnover)

        # Calculate YoY metrics
        revenue_yoy_pct: Optional[float] = None
        profit_yoy_pct: Optional[float] = None
        margin_delta_pp: Optional[float] = None

        if prev_ytd_revenue is not None:
            revenue_yoy_pct = _safe_pct_change(ytd_revenue, prev_ytd_revenue)
        if prev_ytd_profit is not None:
            profit_yoy_pct = _safe_pct_change(ytd_profit, prev_ytd_profit)
        if prev_ytd_margin_pct is not None:
            margin_delta_pp = ytd_margin_pct - prev_ytd_margin_pct

        # Extract balance sheet metrics from latest non-zero month
        cash_position = 0.0
        inventory_total = 0.0
        receivables = 0.0
        payables = 0.0

        for record in curr_balance:
            item = AccountBalance(**record)
            ucet = item.ucet.strip()
            konecny = item.konecny

            if konecny == 0.0:
                continue

            # Cash (2xx accounts)
            if ucet.startswith("2"):
                cash_position += konecny
            # Inventory (1xx accounts)
            elif ucet.startswith("1"):
                inventory_total += konecny
            # Receivables (311xxx accounts)
            elif ucet.startswith("311"):
                receivables += konecny
            # Payables (321xxx accounts)
            elif ucet.startswith("321"):
                payables += abs(konecny)

        # Calculate efficiency ratios
        days_cash_on_hand: Optional[float] = None
        receivables_to_revenue_pct: Optional[float] = None
        inventory_to_revenue_pct: Optional[float] = None

        # Calculate elapsed months (month with latest data)
        elapsed_months = max([pnl.mesic for pnl in monthly_pnl if pnl.revenue > 0 or pnl.expenses > 0], default=datetime.now().month)

        if ytd_expenses > 0 and elapsed_months > 0:
            avg_monthly_expenses = ytd_expenses / elapsed_months
            if avg_monthly_expenses > 0:
                days_cash_on_hand = (cash_position / avg_monthly_expenses) * 30.0

        if ytd_revenue > 0:
            receivables_to_revenue_pct = (receivables / ytd_revenue) * 100.0
            inventory_to_revenue_pct = (inventory_total / ytd_revenue) * 100.0

        result = DashboardOverviewResponse(
            rok=rok,
            monthly=monthly_pnl,
            ytd_revenue=ytd_revenue,
            ytd_expenses=ytd_expenses,
            ytd_profit=ytd_profit,
            ytd_margin_pct=ytd_margin_pct,
            cash_position=cash_position,
            inventory_total=inventory_total,
            receivables=receivables,
            payables=payables,
            # YoY fields
            prev_ytd_revenue=prev_ytd_revenue,
            prev_ytd_expenses=prev_ytd_expenses,
            prev_ytd_profit=prev_ytd_profit,
            prev_ytd_margin_pct=prev_ytd_margin_pct,
            prev_monthly=prev_monthly,
            revenue_yoy_pct=revenue_yoy_pct,
            profit_yoy_pct=profit_yoy_pct,
            margin_delta_pp=margin_delta_pp,
            days_cash_on_hand=days_cash_on_hand,
            receivables_to_revenue_pct=receivables_to_revenue_pct,
            inventory_to_revenue_pct=inventory_to_revenue_pct,
        )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error("Dashboard overview aggregation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard aggregation failed: {str(e)}",
        )


@router.get("/dashboard/costs", response_model=DashboardCostsResponse)
async def get_dashboard_costs(
    rok: int = Query(default=datetime.now().year, ge=2000, le=2100),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> DashboardCostsResponse:
    """
    Dashboard costs breakdown by category, top accounts, and cost type.

    Uses turnover data (ZustNaDan) for 5xx accounts (excluding 58x internal transfers).
    Includes YoY comparison with previous year data.
    Cached for 1 hour.
    """
    cache_key = f"dashboard_costs_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        # Fetch current and previous year data in parallel
        curr_turnover: Optional[List[Dict[str, Any]]] = None
        prev_turnover: Optional[List[Dict[str, Any]]] = None

        try:
            curr_turnover, prev_turnover = await asyncio.gather(
                _fetch_csixls(f"ZustNaDan/{rok}"),
                _fetch_csixls(f"ZustNaDan/{rok - 1}"),
            )
        except Exception:
            # If previous year fails, still return current year
            curr_turnover = await _fetch_csixls(f"ZustNaDan/{rok}")
            prev_turnover = None

        # Helper to aggregate costs by category
        def _aggregate_costs(turnover_data: List[Dict[str, Any]]) -> Tuple[Dict[str, float], float]:
            category_totals: Dict[str, float] = {}
            for record in turnover_data:
                item = AccountTurnover(**record)
                ucet = item.ucet.strip()

                # Only process 5xx accounts (excluding 58x)
                if not ucet.startswith("5") or ucet.startswith("58"):
                    continue

                amount = item.md - item.dal
                prefix = ucet[:3] if len(ucet) >= 3 else ucet
                if prefix in EXPENSE_CATEGORIES:
                    category_totals[prefix] = category_totals.get(prefix, 0.0) + amount

            total = sum(category_totals.values())
            return category_totals, total

        # Aggregate current year
        category_totals, total_expenses = _aggregate_costs(curr_turnover)

        # Track account totals and type monthly for current year
        account_totals: Dict[str, Tuple[str, float]] = {}  # ucet -> (popis, total)
        type_monthly: Dict[int, Dict[str, float]] = {
            m: {
                "MAT": 0.0,
                "MZDY": 0.0,
                "KOO": 0.0,
                "VAR": 0.0,
                "FIX": 0.0,
                "Fstr": 0.0,
                "Vstr": 0.0,
            }
            for m in range(1, 13)
        }

        for record in curr_turnover:
            item = AccountTurnover(**record)
            ucet = item.ucet.strip()

            # Only process 5xx accounts (excluding 58x)
            if not ucet.startswith("5") or ucet.startswith("58"):
                continue

            amount = item.md - item.dal
            mesic = item.mesic
            dAn2 = item.dAn2.strip()

            # Account totals for top accounts
            if ucet not in account_totals:
                account_totals[ucet] = (item.popis, 0.0)
            account_totals[ucet] = (account_totals[ucet][0], account_totals[ucet][1] + amount)

            # Type monthly aggregation (by dAn2)
            if dAn2 in type_monthly[mesic]:
                type_monthly[mesic][dAn2] += amount

        # Build category list with percentages
        by_category: List[CostCategory] = []
        for prefix in sorted(category_totals.keys()):
            amount = category_totals[prefix]
            pct = (amount / total_expenses * 100.0) if total_expenses > 0 else 0.0
            by_category.append(
                CostCategory(
                    category=EXPENSE_CATEGORIES.get(prefix, prefix),
                    amount=amount,
                    pct=pct,
                )
            )

        # Aggregate previous year if available
        prev_by_category: Optional[List[CostCategory]] = None
        prev_total_expenses: Optional[float] = None
        total_expenses_yoy_pct: Optional[float] = None

        if prev_turnover is not None:
            prev_category_totals, prev_total_expenses = _aggregate_costs(prev_turnover)
            prev_by_category = []
            for prefix in sorted(prev_category_totals.keys()):
                amount = prev_category_totals[prefix]
                pct = (amount / prev_total_expenses * 100.0) if prev_total_expenses > 0 else 0.0
                prev_by_category.append(
                    CostCategory(
                        category=EXPENSE_CATEGORIES.get(prefix, prefix),
                        amount=amount,
                        pct=pct,
                    )
                )
            total_expenses_yoy_pct = _safe_pct_change(total_expenses, prev_total_expenses)

        # Top 10 accounts
        top_accounts: List[TopAccount] = []
        sorted_accounts = sorted(account_totals.items(), key=lambda x: x[1][1], reverse=True)[:10]
        for ucet, (popis, total) in sorted_accounts:
            top_accounts.append(TopAccount(ucet=ucet, popis=popis, total=total))

        # Monthly by type
        by_type_monthly: List[CostTypeMonthly] = []
        for mesic in range(1, 13):
            by_type_monthly.append(
                CostTypeMonthly(
                    mesic=mesic,
                    MAT=type_monthly[mesic]["MAT"],
                    MZDY=type_monthly[mesic]["MZDY"],
                    KOO=type_monthly[mesic]["KOO"],
                    VAR=type_monthly[mesic]["VAR"],
                    FIX=type_monthly[mesic]["FIX"],
                    Fstr=type_monthly[mesic]["Fstr"],
                    Vstr=type_monthly[mesic]["Vstr"],
                )
            )

        result = DashboardCostsResponse(
            rok=rok,
            by_category=by_category,
            top_accounts=top_accounts,
            by_type_monthly=by_type_monthly,
            # YoY fields
            prev_by_category=prev_by_category,
            total_expenses_yoy_pct=total_expenses_yoy_pct,
        )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error("Dashboard costs aggregation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard costs aggregation failed: {str(e)}",
        )


@router.get("/dashboard/machines", response_model=DashboardMachinesResponse)
async def get_dashboard_machines(
    rok: int = Query(default=datetime.now().year, ge=2000, le=2100),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> DashboardMachinesResponse:
    """
    Dashboard machines and cost centers breakdown.

    Groups by dAn3 (machine code) and dAn1 (cost center).
    Uses turnover data for 5xx accounts (excluding 58x).
    Cached for 1 hour.
    """
    cache_key = f"dashboard_machines_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        turnover_data = await _fetch_csixls(f"ZustNaDan/{rok}")

        # Aggregate by machine (dAn3)
        machine_totals: Dict[str, Dict[str, float]] = {}  # code -> {total, monthly[1-12]}
        # Aggregate by cost center (dAn1)
        center_totals: Dict[str, float] = {}

        for record in turnover_data:
            item = AccountTurnover(**record)
            ucet = item.ucet.strip()

            # Only process 5xx accounts (excluding 58x)
            if not ucet.startswith("5") or ucet.startswith("58"):
                continue

            amount = abs(item.md - item.dal)
            mesic = item.mesic
            dAn3 = item.dAn3.strip()
            dAn1 = item.dAn1.strip()

            # Machine aggregation (skip empty dAn3)
            if dAn3:
                if dAn3 not in machine_totals:
                    machine_totals[dAn3] = {"total": 0.0, **{str(m): 0.0 for m in range(1, 13)}}
                machine_totals[dAn3]["total"] += amount
                machine_totals[dAn3][str(mesic)] += amount

            # Cost center aggregation
            if dAn1:
                center_totals[dAn1] = center_totals.get(dAn1, 0.0) + amount

        # Top 15 machines
        machines: List[MachineCost] = []
        sorted_machines = sorted(machine_totals.items(), key=lambda x: x[1]["total"], reverse=True)[:15]
        for code, data in sorted_machines:
            monthly = [data[str(m)] for m in range(1, 13)]
            machines.append(
                MachineCost(
                    code=code,
                    label=code,  # Could be enhanced with machine names lookup
                    total=data["total"],
                    monthly=monthly,
                )
            )

        # Cost centers
        cost_centers: List[CostCenterSummary] = []
        for code in sorted(center_totals.keys()):
            cost_centers.append(
                CostCenterSummary(
                    code=code,
                    label=COST_CENTER_LABELS.get(code, code),
                    total=center_totals[code],
                )
            )

        result = DashboardMachinesResponse(
            rok=rok,
            machines=machines,
            cost_centers=cost_centers,
        )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error("Dashboard machines aggregation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard machines aggregation failed: {str(e)}",
        )


@router.get("/dashboard/revenue", response_model=DashboardRevenueResponse)
async def get_dashboard_revenue(
    rok: int = Query(default=datetime.now().year, ge=2000, le=2100),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> DashboardRevenueResponse:
    """
    Dashboard revenue breakdown by streams and cost centers.

    Groups 6xx accounts into revenue streams (products, rental, services, other).
    Uses turnover data (dal side for revenue).
    Includes YoY comparison with previous year data.
    Cached for 1 hour.
    """
    cache_key = f"dashboard_revenue_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        # Fetch current and previous year data in parallel
        curr_turnover: Optional[List[Dict[str, Any]]] = None
        prev_turnover: Optional[List[Dict[str, Any]]] = None

        try:
            curr_turnover, prev_turnover = await asyncio.gather(
                _fetch_csixls(f"ZustNaDan/{rok}"),
                _fetch_csixls(f"ZustNaDan/{rok - 1}"),
            )
        except Exception:
            # If previous year fails, still return current year
            curr_turnover = await _fetch_csixls(f"ZustNaDan/{rok}")
            prev_turnover = None

        # Helper to aggregate revenue
        def _aggregate_revenue(turnover_data: List[Dict[str, Any]]) -> float:
            total = 0.0
            for record in turnover_data:
                item = AccountTurnover(**record)
                ucet = item.ucet.strip()

                # Only process 6xx accounts (revenue)
                if not ucet.startswith("6"):
                    continue

                total += item.dal
            return total

        # Define revenue streams
        stream_mapping: Dict[str, str] = {
            "601000": "Vlastní výrobky",
            "602010": "Pronájem",
            "602000": "Služby",
        }

        # Aggregate by stream and month (current year)
        stream_totals: Dict[str, Dict[str, float]] = {
            "Vlastní výrobky": {"total": 0.0, **{str(m): 0.0 for m in range(1, 13)}},
            "Pronájem": {"total": 0.0, **{str(m): 0.0 for m in range(1, 13)}},
            "Služby": {"total": 0.0, **{str(m): 0.0 for m in range(1, 13)}},
            "Ostatní výnosy": {"total": 0.0, **{str(m): 0.0 for m in range(1, 13)}},
        }

        # Aggregate by cost center
        center_totals: Dict[str, float] = {}

        ytd_total = 0.0

        for record in curr_turnover:
            item = AccountTurnover(**record)
            ucet = item.ucet.strip()

            # Only process 6xx accounts (revenue)
            if not ucet.startswith("6"):
                continue

            amount = item.dal
            mesic = item.mesic
            dAn1 = item.dAn1.strip()

            ytd_total += amount

            # Determine stream
            stream = stream_mapping.get(ucet, "Ostatní výnosy")
            stream_totals[stream]["total"] += amount
            stream_totals[stream][str(mesic)] += amount

            # Cost center aggregation
            if dAn1:
                center_totals[dAn1] = center_totals.get(dAn1, 0.0) + amount

        # Build streams list
        streams: List[RevenueStream] = []
        for category, data in stream_totals.items():
            if data["total"] > 0:  # Only include non-zero streams
                monthly = [data[str(m)] for m in range(1, 13)]
                streams.append(
                    RevenueStream(
                        category=category,
                        total=data["total"],
                        monthly=monthly,
                    )
                )

        # Cost centers
        by_center: List[CostCenterSummary] = []
        for code in sorted(center_totals.keys()):
            by_center.append(
                CostCenterSummary(
                    code=code,
                    label=COST_CENTER_LABELS.get(code, code),
                    total=center_totals[code],
                )
            )

        # Aggregate previous year if available
        prev_ytd_total: Optional[float] = None
        revenue_yoy_pct: Optional[float] = None

        if prev_turnover is not None:
            prev_ytd_total = _aggregate_revenue(prev_turnover)
            revenue_yoy_pct = _safe_pct_change(ytd_total, prev_ytd_total)

        result = DashboardRevenueResponse(
            rok=rok,
            streams=streams,
            ytd_total=ytd_total,
            by_center=by_center,
            # YoY fields
            prev_ytd_total=prev_ytd_total,
            revenue_yoy_pct=revenue_yoy_pct,
        )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error("Dashboard revenue aggregation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard revenue aggregation failed: {str(e)}",
        )


@router.get("/dashboard/balance-sheet", response_model=DashboardBalanceSheetResponse)
async def get_dashboard_balance_sheet(
    rok: int = Query(default=datetime.now().year, ge=2000, le=2100),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> DashboardBalanceSheetResponse:
    """
    Dashboard balance sheet metrics.

    Asset categories and monthly trends for key accounts (WIP, finished goods, receivables, payables, cash).
    Uses balance data (ZustNaUctech).
    Cached for 1 hour.
    """
    cache_key = f"dashboard_balance_sheet_{rok}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        balance_data = await _fetch_csixls(f"ZustNaUctech/{rok}")

        # Asset categories
        asset_categories: Dict[str, float] = {
            "Dlouhodobý majetek": 0.0,
            "Zásoby": 0.0,
            "Finanční majetek": 0.0,
            "Pohledávky": 0.0,
            "Závazky": 0.0,
        }

        # Monthly trends
        wip_monthly: List[float] = [0.0] * 12
        finished_monthly: List[float] = [0.0] * 12
        receivables_monthly: List[float] = [0.0] * 12
        payables_monthly: List[float] = [0.0] * 12
        cash_monthly: List[float] = [0.0] * 12

        for record in balance_data:
            item = AccountBalance(**record)
            ucet = item.ucet.strip()
            mesic = item.mesic
            konecny = item.konecny

            # Asset categories (use latest konecny)
            if ucet.startswith("0"):
                asset_categories["Dlouhodobý majetek"] += konecny
            elif ucet.startswith("1"):
                asset_categories["Zásoby"] += konecny
            elif ucet.startswith("2"):
                asset_categories["Finanční majetek"] += konecny
                cash_monthly[mesic - 1] += konecny
            elif ucet.startswith("31"):
                asset_categories["Pohledávky"] += konecny
            elif ucet.startswith("32") or ucet.startswith("33"):
                asset_categories["Závazky"] += abs(konecny)

            # Monthly trends (specific accounts)
            if ucet.startswith("121"):  # WIP
                wip_monthly[mesic - 1] += konecny
            elif ucet.startswith("123"):  # Finished goods
                finished_monthly[mesic - 1] += konecny
            elif ucet.startswith("311"):  # Receivables
                receivables_monthly[mesic - 1] += konecny
            elif ucet.startswith("321"):  # Payables
                payables_monthly[mesic - 1] += abs(konecny)

        # Build assets list
        assets: List[AssetCategory] = []
        for category, total in asset_categories.items():
            if abs(total) > 0.01:  # Only include non-zero categories
                assets.append(AssetCategory(category=category, total=total))

        result = DashboardBalanceSheetResponse(
            rok=rok,
            assets=assets,
            wip_monthly=wip_monthly,
            finished_monthly=finished_monthly,
            receivables_monthly=receivables_monthly,
            payables_monthly=payables_monthly,
            cash_monthly=cash_monthly,
        )

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error("Dashboard balance sheet aggregation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard balance sheet aggregation failed: {str(e)}",
        )
