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

/** Czech date format: 21. 2. 2026 — supports ISO strings, Date objects, and Infor compact YYYYMMDD */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—'
  let d: Date
  if (typeof value === 'string') {
    const compact = value.trim().match(/^(\d{4})(\d{2})(\d{2})/)
    if (compact) {
      d = new Date(Number(compact[1]), Number(compact[2]) - 1, Number(compact[3]))
    } else {
      d = new Date(value)
    }
  } else {
    d = value
  }
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

/** Duration in mm:ss format: 1.5 → "01:30", 90 → "90:00" */
export function formatMinSec(minutes: number | null | undefined): string {
  if (minutes == null) return '—'
  const totalSec = Math.round(minutes * 60)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/** Infor date/time string → "DD.MM. HH:MM:SS" or time-only "HH:MM:SS" */
export function formatInforDate(value: string | null | undefined): string {
  if (!value) return '—'
  const raw = value.trim()
  if (!raw) return '—'

  const timeOnlyMatch = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/)
  if (timeOnlyMatch) {
    const hh = (timeOnlyMatch[1] ?? '0').padStart(2, '0')
    const mm = timeOnlyMatch[2] ?? '00'
    const ss = (timeOnlyMatch[3] ?? '00').padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  }

  try {
    const d = new Date(raw)
    if (isNaN(d.getTime())) return raw
    const day = d.getDate().toString().padStart(2, '0')
    const mon = (d.getMonth() + 1).toString().padStart(2, '0')
    const hh = d.getHours().toString().padStart(2, '0')
    const mm = d.getMinutes().toString().padStart(2, '0')
    const ss = d.getSeconds().toString().padStart(2, '0')
    return `${day}.${mon}. ${hh}:${mm}:${ss}`
  } catch {
    return raw
  }
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
