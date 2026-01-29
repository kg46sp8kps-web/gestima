/**
 * GESTIMA Design Tokens
 * Based on existing Alpine.js CSS, extended with light mode
 */

export const designTokens = {
  // Typography
  fontFamily: {
    base: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif',
    mono: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace'
  },

  fontSize: {
    xs: '0.75rem',   // 12px - table headers
    sm: '0.8rem',    // 13px - default body
    md: '0.875rem',  // 14px - normal text
    lg: '1rem',      // 16px - headings
    xl: '1.125rem'   // 18px - large headings
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700
  },

  // Spacing (consistent scale)
  spacing: {
    xs: '0.25rem',   // 4px
    sm: '0.5rem',    // 8px
    md: '1rem',      // 16px
    lg: '1.5rem',    // 24px
    xl: '2rem',      // 32px
    xxl: '3rem'      // 48px
  },

  // Border radius
  radius: {
    sm: '3px',
    md: '5px',
    lg: '8px',
    full: '9999px'
  },

  // Transitions (subtle = responsive feel!)
  transition: {
    fast: '100ms',
    normal: '150ms',
    slow: '200ms',
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)' // Material Design standard easing
  },

  // Shadows
  shadow: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
    md: '0 4px 6px rgba(0, 0, 0, 0.4)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.5)'
  }
} as const;

/**
 * Theme colors - DARK (existing)
 */
export const darkTheme = {
  // Backgrounds
  bg: {
    primary: '#0d0d0d',
    secondary: '#161616',
    tertiary: '#1f1f1f',
    card: '#1a1a1a',
    cardHover: '#222222',
    input: '#111111',
    panel: '#141414'
  },

  // Text
  text: {
    primary: '#f5f5f5',
    secondary: '#9ca3af',
    muted: '#6b7280',
    disabled: '#4b5563'
  },

  // Borders
  border: {
    default: '#2a2a2a',
    light: '#3a3a3a',
    focus: '#4a4a4a'
  },

  // Accents (semantic colors)
  accent: {
    red: '#d62828',
    redDark: '#9b1c1c',
    redLight: '#ef4444',
    blue: '#3b82f6',
    blueHover: '#2563eb',
    green: '#22c55e',
    greenSoft: '#16a34a',
    yellow: '#eab308',
    orange: '#f97316',
    purple: '#8b5cf6',
    pink: '#ec4899'
  },

  // Semantic (aliasy pro clarity)
  primary: '#3b82f6',
  primaryHover: '#2563eb',
  success: '#22c55e',
  successHover: '#16a34a',
  error: '#d62828',
  errorHover: '#b91c1c',
  warning: '#eab308',
  info: '#3b82f6'
} as const;

/**
 * Theme colors - LIGHT (new!)
 */
export const lightTheme = {
  // Backgrounds
  bg: {
    primary: '#ffffff',
    secondary: '#f8fafc',
    tertiary: '#f1f5f9',
    card: '#ffffff',
    cardHover: '#f8fafc',
    input: '#ffffff',
    panel: '#f8fafc'
  },

  // Text
  text: {
    primary: '#0f172a',
    secondary: '#64748b',
    muted: '#94a3b8',
    disabled: '#cbd5e1'
  },

  // Borders
  border: {
    default: '#e2e8f0',
    light: '#cbd5e1',
    focus: '#94a3b8'
  },

  // Accents (same hues, adjusted for light bg)
  accent: {
    red: '#dc2626',
    redDark: '#991b1b',
    redLight: '#ef4444',
    blue: '#2563eb',
    blueHover: '#1d4ed8',
    green: '#16a34a',
    greenSoft: '#15803d',
    yellow: '#ca8a04',
    orange: '#ea580c',
    purple: '#7c3aed',
    pink: '#db2777'
  },

  // Semantic
  primary: '#2563eb',
  primaryHover: '#1d4ed8',
  success: '#16a34a',
  successHover: '#15803d',
  error: '#dc2626',
  errorHover: '#b91c1c',
  warning: '#ca8a04',
  info: '#2563eb'
} as const;

export type Theme = typeof darkTheme;
export type ThemeMode = 'dark' | 'light';
