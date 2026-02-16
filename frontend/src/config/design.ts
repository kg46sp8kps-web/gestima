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
  /** Standardní velikost pro ikony v tlačítkách, formulářích (matches DS --icon-size: 18px) */
  STANDARD: 18,

  /** Malé ikony pro inline text, badges */
  SMALL: 14,

  /** Velké ikony pro headery, hlavní akce */
  LARGE: 22,

  /** Extra velké ikony pro empty states, ilustrace */
  XLARGE: 32,

  /** Hero ikony pro prázdné stavy, velké ilustrace */
  HERO: 48,
} as const

/**
 * Velikosti tlačítek
 */
export const BUTTON_SIZE = {
  SMALL: 'sm',
  MEDIUM: 'md',
  LARGE: 'lg',
} as const
