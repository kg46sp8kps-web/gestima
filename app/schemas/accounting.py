"""GESTIMA - Accounting schemas (CsiXls proxy)"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    """Single record from ZustNaUctech endpoint."""
    rok: int = Field(..., ge=2000, le=2100)
    mesic: int = Field(..., ge=1, le=12)
    ucet: str = Field(..., min_length=1, max_length=10)
    popis: str = Field(..., min_length=1)
    pocatecni: float = Field(...)
    konecny: float = Field(...)


class AccountTurnover(BaseModel):
    """Single record from ZustNaDan endpoint."""
    rok: int = Field(..., ge=2000, le=2100)
    mesic: int = Field(..., ge=1, le=12)
    ucet: str = Field(..., min_length=1, max_length=10)
    popis: str = Field(..., min_length=1)
    md: float = Field(...)
    dal: float = Field(...)
    dAn1: str = Field(default="", max_length=50)
    dAn2: str = Field(default="", max_length=50)
    dAn3: str = Field(default="", max_length=50)
    dAn4: str = Field(default="", max_length=50)


class BalanceCell(BaseModel):
    """Single cell in balance pivot table."""
    pocatecni: float = Field(...)
    konecny: float = Field(...)


class BalancePivotResponse(BaseModel):
    """Pivoted balance response for frontend."""
    rok: int = Field(..., ge=2000, le=2100)
    accounts: List[str] = Field(default_factory=list)
    account_names: Dict[str, str] = Field(default_factory=dict)
    months: List[int] = Field(default_factory=list)
    cells: Dict[str, Dict[str, BalanceCell]] = Field(default_factory=dict)
    total_records: int = Field(..., ge=0)
    non_zero_accounts: int = Field(..., ge=0)


class TurnoverRecord(BaseModel):
    """Single turnover record for frontend (cleaned)."""
    ucet: str = Field(..., min_length=1, max_length=10)
    popis: str = Field(..., min_length=1)
    mesic: int = Field(..., ge=1, le=12)
    md: float = Field(...)
    dal: float = Field(...)
    dAn1: str = Field(default="", max_length=50)
    dAn2: str = Field(default="", max_length=50)
    dAn3: str = Field(default="", max_length=50)
    dAn4: str = Field(default="", max_length=50)


class TurnoverResponse(BaseModel):
    """Turnover response for frontend."""
    rok: int = Field(..., ge=2000, le=2100)
    records: List[TurnoverRecord] = Field(default_factory=list)
    total_records: int = Field(..., ge=0)
    non_zero_records: int = Field(..., ge=0)
    analytics: Dict[str, List[str]] = Field(default_factory=dict)


# Dashboard schemas

class MonthlyPnL(BaseModel):
    """Monthly profit and loss summary."""
    mesic: int = Field(..., ge=1, le=12)
    revenue: float = Field(default=0.0)
    expenses: float = Field(default=0.0)
    profit: float = Field(default=0.0)


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview with P&L and balance sheet metrics."""
    rok: int = Field(..., ge=2000, le=2100)
    monthly: List[MonthlyPnL] = Field(default_factory=list)
    ytd_revenue: float = Field(default=0.0)
    ytd_expenses: float = Field(default=0.0)
    ytd_profit: float = Field(default=0.0)
    ytd_margin_pct: float = Field(default=0.0)
    cash_position: float = Field(default=0.0)
    inventory_total: float = Field(default=0.0)
    receivables: float = Field(default=0.0)
    payables: float = Field(default=0.0)
    # YoY comparison fields
    prev_ytd_revenue: Optional[float] = Field(default=None, description="Previous year YTD revenue")
    prev_ytd_expenses: Optional[float] = Field(default=None, description="Previous year YTD expenses")
    prev_ytd_profit: Optional[float] = Field(default=None, description="Previous year YTD profit")
    prev_ytd_margin_pct: Optional[float] = Field(default=None, description="Previous year margin %")
    prev_monthly: Optional[List[MonthlyPnL]] = Field(default=None, description="Previous year monthly P&L")
    revenue_yoy_pct: Optional[float] = Field(default=None, description="Revenue YoY growth %")
    profit_yoy_pct: Optional[float] = Field(default=None, description="Profit YoY growth %")
    margin_delta_pp: Optional[float] = Field(default=None, description="Margin delta in percentage points")
    days_cash_on_hand: Optional[float] = Field(default=None, description="Days of expenses covered by cash")
    receivables_to_revenue_pct: Optional[float] = Field(default=None, description="Receivables as % of revenue")
    inventory_to_revenue_pct: Optional[float] = Field(default=None, description="Inventory as % of revenue")


class CostCategory(BaseModel):
    """Cost by category (expense account prefix)."""
    category: str = Field(..., min_length=1)
    amount: float = Field(default=0.0)
    pct: float = Field(default=0.0)


class TopAccount(BaseModel):
    """Top account by total amount."""
    ucet: str = Field(..., min_length=1)
    popis: str = Field(default="")
    total: float = Field(default=0.0)


class CostTypeMonthly(BaseModel):
    """Monthly costs by type (dAn2 classification)."""
    mesic: int = Field(..., ge=1, le=12)
    MAT: float = Field(default=0.0)
    MZDY: float = Field(default=0.0)
    KOO: float = Field(default=0.0)
    VAR: float = Field(default=0.0)
    FIX: float = Field(default=0.0)
    Fstr: float = Field(default=0.0)
    Vstr: float = Field(default=0.0)


class DashboardCostsResponse(BaseModel):
    """Dashboard costs breakdown."""
    rok: int = Field(..., ge=2000, le=2100)
    by_category: List[CostCategory] = Field(default_factory=list)
    top_accounts: List[TopAccount] = Field(default_factory=list)
    by_type_monthly: List[CostTypeMonthly] = Field(default_factory=list)
    # YoY comparison fields
    prev_by_category: Optional[List[CostCategory]] = Field(default=None, description="Previous year costs by category")
    total_expenses_yoy_pct: Optional[float] = Field(default=None, description="Total expenses YoY growth %")


class MachineCost(BaseModel):
    """Machine cost summary (by dAn3)."""
    code: str = Field(..., min_length=1)
    label: str = Field(default="")
    total: float = Field(default=0.0)
    monthly: List[float] = Field(default_factory=list)


class CostCenterSummary(BaseModel):
    """Cost center summary (by dAn1)."""
    code: str = Field(..., min_length=1)
    label: str = Field(default="")
    total: float = Field(default=0.0)


class DashboardMachinesResponse(BaseModel):
    """Dashboard machines and cost centers breakdown."""
    rok: int = Field(..., ge=2000, le=2100)
    machines: List[MachineCost] = Field(default_factory=list)
    cost_centers: List[CostCenterSummary] = Field(default_factory=list)


class RevenueStream(BaseModel):
    """Revenue stream by category."""
    category: str = Field(..., min_length=1)
    total: float = Field(default=0.0)
    monthly: List[float] = Field(default_factory=list)


class DashboardRevenueResponse(BaseModel):
    """Dashboard revenue breakdown."""
    rok: int = Field(..., ge=2000, le=2100)
    streams: List[RevenueStream] = Field(default_factory=list)
    ytd_total: float = Field(default=0.0)
    by_center: List[CostCenterSummary] = Field(default_factory=list)
    # YoY comparison fields
    prev_ytd_total: Optional[float] = Field(default=None, description="Previous year YTD total revenue")
    revenue_yoy_pct: Optional[float] = Field(default=None, description="Revenue YoY growth %")


class AssetCategory(BaseModel):
    """Asset category summary."""
    category: str = Field(..., min_length=1)
    total: float = Field(default=0.0)


class DashboardBalanceSheetResponse(BaseModel):
    """Dashboard balance sheet metrics."""
    rok: int = Field(..., ge=2000, le=2100)
    assets: List[AssetCategory] = Field(default_factory=list)
    wip_monthly: List[float] = Field(default_factory=list)
    finished_monthly: List[float] = Field(default_factory=list)
    receivables_monthly: List[float] = Field(default_factory=list)
    payables_monthly: List[float] = Field(default_factory=list)
    cash_monthly: List[float] = Field(default_factory=list)
