import type { DashboardOverviewResponse } from '@/types/accounting'

export type RagStatus = 'success' | 'warning' | 'danger'
export type TrendDirection = 'up' | 'down' | 'stable'

export interface InsightItem {
  text: string
  severity: RagStatus
}

export function growthRate(current: number, previous: number | null | undefined): number | null {
  if (previous == null || Math.abs(previous) < 0.01) return null
  return ((current - previous) / Math.abs(previous)) * 100
}

export function ragStatus(
  value: number,
  thresholds: { danger: number; warning: number },
  higherIsBetter: boolean = true
): RagStatus {
  if (higherIsBetter) {
    if (value <= thresholds.danger) return 'danger'
    if (value <= thresholds.warning) return 'warning'
    return 'success'
  }
  if (value >= thresholds.danger) return 'danger'
  if (value >= thresholds.warning) return 'warning'
  return 'success'
}

export function trendDirection(values: number[]): TrendDirection {
  if (values.length < 2) return 'stable'
  const recent = values.slice(-3)
  const first = recent[0] ?? 0
  const last = recent[recent.length - 1] ?? 0
  if (Math.abs(first) < 0.01) return last > 0 ? 'up' : 'stable'
  const change = ((last - first) / Math.abs(first)) * 100
  if (change > 3) return 'up'
  if (change < -3) return 'down'
  return 'stable'
}

export function formatGrowthPct(pct: number | null | undefined): string {
  if (pct == null) return 'N/A'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)} %`
}

export function generateOverviewInsights(data: DashboardOverviewResponse): InsightItem[] {
  const insights: InsightItem[] = []

  if (data.revenue_yoy_pct != null) {
    const dir = data.revenue_yoy_pct >= 0 ? 'vzrostly' : 'klesly'
    insights.push({
      text: `Trzby ${dir} o ${Math.abs(data.revenue_yoy_pct).toFixed(1)} % oproti minulemu roku`,
      severity: data.revenue_yoy_pct >= -5 ? 'success' : 'danger'
    })
  }

  if (data.ytd_margin_pct < 3) {
    const annualProfit = data.ytd_profit
    insights.push({
      text: `Marze ${data.ytd_margin_pct.toFixed(1)} % je pod 3 % — rocni zisk jen ${(annualProfit / 1000).toFixed(0)} tis. Kc`,
      severity: 'danger'
    })
  } else if (data.ytd_margin_pct < 5) {
    insights.push({
      text: `Marze ${data.ytd_margin_pct.toFixed(1)} % — blizi se k cili 5 %`,
      severity: 'warning'
    })
  }

  if (data.days_cash_on_hand != null) {
    if (data.days_cash_on_hand < 7) {
      insights.push({
        text: `Hotovost vystaci na ${data.days_cash_on_hand.toFixed(0)} dnu provozu — kriticke`,
        severity: 'danger'
      })
    } else if (data.days_cash_on_hand < 30) {
      insights.push({
        text: `Hotovost vystaci na ${data.days_cash_on_hand.toFixed(0)} dnu provozu`,
        severity: 'warning'
      })
    }
  }

  if (data.receivables_to_revenue_pct != null && data.receivables_to_revenue_pct > 15) {
    insights.push({
      text: `Pohledavky tvori ${data.receivables_to_revenue_pct.toFixed(1)} % trzeb — zakaznici plati pomalu`,
      severity: 'warning'
    })
  }

  return insights
}
