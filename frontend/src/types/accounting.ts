// Accounting types for CsiXls proxy endpoints

export interface BalanceCell {
  pocatecni: number
  konecny: number
}

export interface BalancePivotResponse {
  rok: number
  accounts: string[]
  account_names: Record<string, string>
  months: number[]
  cells: Record<string, Record<string, BalanceCell>> // ucet -> month -> cell
  total_records: number
  non_zero_accounts: number
}

export interface TurnoverRecord {
  ucet: string
  popis: string
  mesic: number
  md: number
  dal: number
  dAn1: string
  dAn2: string
  dAn3: string
  dAn4: string
}

export interface TurnoverResponse {
  rok: number
  records: TurnoverRecord[]
  total_records: number
  non_zero_records: number
  analytics: Record<string, string[]> // dimension -> unique values
}

export const MONTH_LABELS: Record<number, string> = {
  1: 'Led',
  2: 'Úno',
  3: 'Bře',
  4: 'Dub',
  5: 'Kvě',
  6: 'Čer',
  7: 'Čvc',
  8: 'Srp',
  9: 'Zář',
  10: 'Říj',
  11: 'Lis',
  12: 'Pro',
}

// Dashboard aggregated responses

export interface MonthlyPnL {
  mesic: number
  revenue: number
  expenses: number
  profit: number
}

export interface DashboardOverviewResponse {
  rok: number
  monthly: MonthlyPnL[]
  ytd_revenue: number
  ytd_expenses: number
  ytd_profit: number
  ytd_margin_pct: number
  cash_position: number
  inventory_total: number
  receivables: number
  payables: number
  // YoY comparison fields
  prev_ytd_revenue?: number | null
  prev_ytd_expenses?: number | null
  prev_ytd_profit?: number | null
  prev_ytd_margin_pct?: number | null
  prev_monthly?: MonthlyPnL[] | null
  revenue_yoy_pct?: number | null
  profit_yoy_pct?: number | null
  margin_delta_pp?: number | null
  days_cash_on_hand?: number | null
  receivables_to_revenue_pct?: number | null
  inventory_to_revenue_pct?: number | null
}

export interface CostCategory {
  category: string
  amount: number
  pct: number
}

export interface TopAccount {
  ucet: string
  popis: string
  total: number
}

export interface CostTypeMonthly {
  mesic: number
  MAT: number
  MZDY: number
  KOO: number
  VAR: number
  FIX: number
  Fstr: number
  Vstr: number
}

export interface DashboardCostsResponse {
  rok: number
  by_category: CostCategory[]
  top_accounts: TopAccount[]
  by_type_monthly: CostTypeMonthly[]
  // YoY comparison fields
  prev_by_category?: CostCategory[] | null
  total_expenses_yoy_pct?: number | null
}

export interface MachineCost {
  code: string
  label: string
  total: number
  monthly: number[]
}

export interface CostCenterSummary {
  code: string
  label: string
  total: number
}

export interface DashboardMachinesResponse {
  rok: number
  machines: MachineCost[]
  cost_centers: CostCenterSummary[]
}

export interface RevenueStream {
  category: string
  total: number
  monthly: number[]
}

export interface DashboardRevenueResponse {
  rok: number
  streams: RevenueStream[]
  ytd_total: number
  by_center: CostCenterSummary[]
  // YoY comparison fields
  prev_ytd_total?: number | null
  revenue_yoy_pct?: number | null
}

export interface AssetCategory {
  category: string
  total: number
}

export interface DashboardBalanceSheetResponse {
  rok: number
  assets: AssetCategory[]
  wip_monthly: number[]
  finished_monthly: number[]
  receivables_monthly: number[]
  payables_monthly: number[]
  cash_monthly: number[]
}

export const ACCOUNT_GROUPS = [
  { prefix: '0', label: 'Dlouh. majetek' },
  { prefix: '1', label: 'Zásoby' },
  { prefix: '2', label: 'Finanční účty' },
  { prefix: '3', label: 'Zúčtovací vzt.' },
  { prefix: '4', label: 'Kapitál' },
  { prefix: '5', label: 'Náklady' },
  { prefix: '6', label: 'Výnosy' },
  { prefix: '7', label: 'Závěrkové' },
  { prefix: '9', label: 'Interní' },
] as const
