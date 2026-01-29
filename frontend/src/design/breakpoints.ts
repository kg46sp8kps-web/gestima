/**
 * GESTIMA Responsive Breakpoints
 * Optimized for ultrawide monitors (user requirement)
 */

export const breakpoints = {
  mobile: 640,      // Smartphone
  tablet: 1024,     // Tablet / small laptop
  desktop: 1280,    // Desktop (min-width existing: 1000px)
  wide: 1920,       // Full HD ultrawide
  ultra: 2560       // 2K/4K ultrawide
} as const;

/**
 * Max workspace panels per viewport
 */
export const maxPanelsByWidth = {
  [breakpoints.mobile]: 1,    // Mobile: single panel only
  [breakpoints.tablet]: 2,    // Tablet: dual split
  [breakpoints.desktop]: 4,   // Desktop: quad
  [breakpoints.wide]: 6,      // Ultrawide: hex (3x2 or 6x1)
  [breakpoints.ultra]: 10     // Ultra: max panels
} as const;

/**
 * Media query helpers
 */
export const mediaQueries = {
  mobile: `(max-width: ${breakpoints.tablet - 1}px)`,
  tablet: `(min-width: ${breakpoints.tablet}px) and (max-width: ${breakpoints.desktop - 1}px)`,
  desktop: `(min-width: ${breakpoints.desktop}px)`,
  wide: `(min-width: ${breakpoints.wide}px)`,
  ultra: `(min-width: ${breakpoints.ultra}px)`
} as const;
