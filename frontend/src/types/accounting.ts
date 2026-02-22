export interface MonthlyPnL {
  mesic: number
  revenue: number
  expenses: number
  profit: number
}

export interface DashboardOverview {
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
  // YoY
  prev_ytd_revenue: number | null
  prev_ytd_expenses: number | null
  prev_ytd_profit: number | null
  prev_ytd_margin_pct: number | null
  revenue_yoy_pct: number | null
  profit_yoy_pct: number | null
  margin_delta_pp: number | null
  days_cash_on_hand: number | null
  receivables_to_revenue_pct: number | null
  inventory_to_revenue_pct: number | null
}
