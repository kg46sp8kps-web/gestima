/** Czech currency format: 1 234,50 CZK */
export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return '—'
  return (
    new Intl.NumberFormat('cs-CZ', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value) + ' CZK'
  )
}

/** Czech number format: 1 234,5 */
export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value)
}

/** Czech date format: 21. 2. 2026 */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—'
  const d = typeof value === 'string' ? new Date(value) : value
  if (isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('cs-CZ', {
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
  }).format(d)
}

/** Price with 2 decimals: 1 234,50 */
export function formatPrice(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/** Duration in minutes to human readable: 90 → "1 h 30 min" */
export function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null) return '—'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h} h ${m} min` : `${h} h`
}

/** Percentage: 0.125 → "12,5 %" */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  return (
    new Intl.NumberFormat('cs-CZ', {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimals,
    }).format(value * 100) + ' %'
  )
}
