/**
 * Design System Constants
 *
 * Centrální místo pro všechny design konstanty napříč systémem.
 * Použijte tyto hodnoty pro konzistentní UI.
 */

/**
 * Velikosti ikon (Lucide icons)
 *
 * @example
 * <CheckIcon :size="ICON_SIZE.STANDARD" />
 */
export const ICON_SIZE = {
  /** Standardní velikost pro ikony v tlačítkách, formulářích */
  STANDARD: 20,

  /** Malé ikony pro inline text, badges */
  SMALL: 16,

  /** Velké ikony pro headery, hlavní akce */
  LARGE: 24,

  /** Extra velké ikony pro empty states, ilustrace */
  XLARGE: 32,
} as const

/**
 * Velikosti tlačítek
 */
export const BUTTON_SIZE = {
  SMALL: 'sm',
  MEDIUM: 'md',
  LARGE: 'lg',
} as const
