/**
 * Layout Type Definitions
 *
 * Defines types for layout system (split-pane, resize, etc.)
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 */

/**
 * Layout mode - vertical (side-by-side) or horizontal (stacked)
 */
export type LayoutMode = 'vertical' | 'horizontal'

/**
 * Density mode - from design system
 */
export type DensityMode = 'compact' | 'comfortable'

/**
 * Resize handle options
 */
export interface ResizeHandleOptions {
  /**
   * localStorage key for saving size
   */
  storageKey: string

  /**
   * Default panel size in pixels
   * @default 320
   */
  defaultSize?: number

  /**
   * Minimum panel size in pixels
   * @default 250
   */
  minSize?: number

  /**
   * Maximum panel size in pixels
   * @default 1000
   */
  maxSize?: number

  /**
   * Is vertical resize (side-by-side)?
   * If false, horizontal resize (stacked)
   * @default true
   */
  vertical?: boolean
}

/**
 * Panel configuration for SplitPane
 */
export interface SplitPaneConfig {
  /**
   * Is left/top panel collapsed?
   * @default false
   */
  leftCollapsed?: boolean

  /**
   * localStorage key for panel size
   */
  storageKey: string

  /**
   * Default panel size in pixels
   * @default 320
   */
  defaultSize?: number

  /**
   * Minimum panel size in pixels
   * @default 250
   */
  minSize?: number

  /**
   * Maximum panel size in pixels
   * @default 1000
   */
  maxSize?: number
}
