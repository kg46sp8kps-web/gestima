/**
 * GESTIMA - Shared formatting utilities
 *
 * Eliminates 11× duplicated formatCurrency/formatPrice/formatDate functions.
 *
 * Usage:
 *   import { formatCurrency, formatPrice, formatDate } from '@/utils/formatters'
 */

/**
 * Format number as CZK currency (e.g. "1 234,50 CZK")
 */
export function formatCurrency(value: unknown): string {
  if (value == null || isNaN(Number(value))) return '0,00 CZK'
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK',
    minimumFractionDigits: 2,
  }).format(Number(value))
}

/**
 * Format number as price (e.g. "1 234,50") — without currency symbol
 */
export function formatPrice(value: unknown): string {
  if (value == null || isNaN(Number(value))) return '0,00'
  return Number(value).toLocaleString('cs-CZ', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/**
 * Format number as plain locale number (e.g. "1 234")
 */
export function formatNumber(value: unknown): string {
  const num = Number(value)
  if (!value || isNaN(num)) return '—'
  return new Intl.NumberFormat('cs-CZ').format(num)
}

/**
 * Format ISO date string to Czech date (e.g. "17. 02. 2026")
 */
export function formatDate(value: unknown): string {
  if (!value) return '—'
  const date = new Date(String(value))
  if (isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('cs-CZ', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}
