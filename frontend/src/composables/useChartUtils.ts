/**
 * Chart utilities for Gestima accounting dashboards
 * Shared helpers for SVG chart components
 */

/**
 * Generate SVG path for sparkline chart
 * Extracted from AccountingSummaryCards.vue
 */
export function sparklinePath(data: number[], width: number = 120, height: number = 32): string {
  if (data.length < 2) return ''

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const padding = 2

  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding)
    const y = padding + (1 - (v - min) / range) * (height - 2 * padding)
    return `${x},${y}`
  })

  return 'M' + points.join(' L')
}

/**
 * Format Czech currency with thousands separator
 */
export function formatCzk(value: number): string {
  return new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 0 }).format(value) + ' Kč'
}

/**
 * Format large numbers as millions or thousands
 */
export function formatMillions(value: number): string {
  if (Math.abs(value) >= 1_000_000) return (value / 1_000_000).toFixed(1) + ' M'
  if (Math.abs(value) >= 1_000) return (value / 1_000).toFixed(0) + ' tis'
  return value.toFixed(0)
}

/**
 * Format percentage value
 */
export function formatPct(value: number): string {
  return value.toFixed(1) + ' %'
}

/**
 * Czech month abbreviations (short form)
 */
export const MONTH_SHORT = ['Led', 'Úno', 'Bře', 'Dub', 'Kvě', 'Čvn', 'Čvc', 'Srp', 'Zář', 'Říj', 'Lis', 'Pro']

/**
 * Chart color palette - 10 distinct colors from design system
 * Material, Machining, Setup, Cooperation, Danger, Info, Tools, Rent, Teal, Purple
 */
export const CHART_COLORS = [
  '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#f43f5e',
  '#06b6d4', '#84cc16', '#ec4899', '#14b8a6', '#a855f7'
]

/**
 * Calculate Y-axis ticks for charts
 * Returns [0, tick1, tick2, tick3, max] evenly spaced
 */
export function calculateYTicks(max: number, count: number = 5): number[] {
  if (max === 0) return Array(count).fill(0)
  const step = max / (count - 1)
  return Array.from({ length: count }, (_, i) => step * i)
}

/**
 * Round number to nice human-readable value (for axis ticks)
 */
export function roundToNice(value: number): number {
  if (value === 0) return 0
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)))
  const normalized = value / magnitude

  let nice: number
  if (normalized <= 1) nice = 1
  else if (normalized <= 2) nice = 2
  else if (normalized <= 5) nice = 5
  else nice = 10

  return nice * magnitude
}
