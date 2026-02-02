/**
 * Widget Type Definitions
 *
 * Defines types for the customizable widget system.
 * Widgets are self-contained UI components that can be arranged in a grid layout.
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 * @see docs/guides/CUSTOMIZABLE-MODULE-GUIDE.md
 */

/**
 * Widget types - categorizes widgets by their purpose
 */
export type WidgetType =
  | 'info-card'        // Static information display
  | 'action-bar'       // Action buttons (Material, Operations, Pricing, Drawing)
  | 'form'             // Input form (edit mode)
  | 'chart'            // Data visualization (cost breakdown, time chart)
  | 'table'            // DataTable widget
  | 'empty'            // Empty state placeholder

/**
 * Widget definition - describes a widget's characteristics
 *
 * @example
 * ```typescript
 * const infoWidget: WidgetDefinition = {
 *   id: 'part-info',
 *   type: 'info-card',
 *   title: 'Part Information',
 *   component: 'PartInfoCard',
 *   minWidth: 2,
 *   minHeight: 2,
 *   defaultWidth: 2,
 *   defaultHeight: 3,
 *   resizable: true,
 *   removable: false,
 *   required: true
 * }
 * ```
 */
export interface WidgetDefinition {
  /**
   * Unique widget identifier
   * Used as key in layouts and localStorage
   */
  id: string

  /**
   * Widget type (for categorization and styling)
   */
  type: WidgetType

  /**
   * Display title (shown in widget header)
   */
  title: string

  /**
   * Component name (without .vue extension)
   * Loaded dynamically from frontend/src/components/widgets/
   *
   * @example 'PartInfoCard' loads PartInfoCard.vue
   */
  component: string

  /**
   * Minimum width in grid columns
   * @default 1
   */
  minWidth: number

  /**
   * Minimum height in grid rows
   * @default 1
   */
  minHeight: number

  /**
   * Default width in grid columns
   * Used when adding widget or resetting layout
   */
  defaultWidth: number

  /**
   * Default height in grid rows
   * Used when adding widget or resetting layout
   */
  defaultHeight: number

  /**
   * Can user resize this widget?
   * @default true
   */
  resizable: boolean

  /**
   * Can user remove this widget?
   * @default true
   */
  removable: boolean

  /**
   * Is this widget required (cannot be removed)?
   * Required widgets are always included in layout
   * @default false
   */
  required: boolean
}

/**
 * Widget layout - describes widget position in grid
 *
 * Grid system:
 * - X-axis: Column position (0-indexed, 0 = leftmost)
 * - Y-axis: Row position (0-indexed, 0 = topmost)
 * - W: Width in columns
 * - H: Height in rows
 *
 * @example
 * ```typescript
 * // Widget at top-left, 2 columns × 3 rows
 * { i: 'part-info', x: 0, y: 0, w: 2, h: 3 }
 *
 * // Widget at top-right, 2 columns × 1 row
 * { i: 'part-actions', x: 2, y: 0, w: 2, h: 1 }
 * ```
 */
export interface WidgetLayout {
  /**
   * Widget ID (must match WidgetDefinition.id)
   */
  i: string

  /**
   * X position (column, 0-indexed)
   */
  x: number

  /**
   * Y position (row, 0-indexed)
   */
  y: number

  /**
   * Width in grid columns
   */
  w: number

  /**
   * Height in grid rows
   */
  h: number

  /**
   * Minimum width in grid columns
   * @default undefined
   */
  minW?: number

  /**
   * Minimum height in grid rows
   * @default undefined
   */
  minH?: number

  /**
   * Maximum width in grid columns
   * @default undefined
   */
  maxW?: number

  /**
   * Maximum height in grid rows
   * @default undefined
   */
  maxH?: number

  /**
   * If true, widget cannot be moved or resized
   * @default false
   */
  static?: boolean

  /**
   * GridStack sizeToContent option
   * - false/undefined: No auto-height (fixed height from h)
   * - true: Auto-height to fit content (no limit)
   * - number: Soft max height in rows (allows shrinking below)
   *
   * @example
   * sizeToContent: 4  // Soft max 4 rows, allows shrinking to content
   *
   * @default undefined
   */
  sizeToContent?: boolean | number
}

/**
 * Module layout configuration
 *
 * Complete definition of a module's widget system:
 * - Available widgets
 * - Grid configuration
 * - Default layouts per density mode
 *
 * @example
 * ```typescript
 * const partDetailConfig: ModuleLayoutConfig = {
 *   moduleKey: 'part-detail',
 *   cols: 4,
 *   rowHeight: 80,
 *   widgets: [
 *     { id: 'info', ... },
 *     { id: 'actions', ... }
 *   ],
 *   defaultLayouts: {
 *     compact: [
 *       { i: 'info', x: 0, y: 0, w: 2, h: 3 },
 *       { i: 'actions', x: 2, y: 0, w: 2, h: 1 }
 *     ],
 *     comfortable: [
 *       { i: 'info', x: 0, y: 0, w: 3, h: 4 },
 *       { i: 'actions', x: 3, y: 0, w: 1, h: 2 }
 *     ]
 *   }
 * }
 * ```
 */
export interface ModuleLayoutConfig {
  /**
   * Unique module identifier
   * Used as localStorage key prefix
   *
   * @example 'part-detail', 'quote-detail', 'pricing-detail'
   */
  moduleKey: string

  /**
   * Number of grid columns
   * Standard: 4 or 12
   *
   * @default 4
   */
  cols: number

  /**
   * Row height in pixels
   *
   * @default 80
   */
  rowHeight: number

  /**
   * Available widgets for this module
   * Defines all widgets that can be used
   */
  widgets: WidgetDefinition[]

  /**
   * Default layouts per density mode
   *
   * System automatically selects based on data-density attribute:
   * - compact: For 27"+ displays (2560x1440)
   * - comfortable: For laptops @ 1080p
   */
  defaultLayouts: {
    /**
     * Compact mode layout (more dense)
     */
    compact: WidgetLayout[]

    /**
     * Comfortable mode layout (more spacious)
     */
    comfortable: WidgetLayout[]
  }

  /**
   * Recommended window properties (optional)
   * Defines default window size when this module is opened
   */
  windowDefaults?: {
    /**
     * Default window width in pixels
     * @default 800
     */
    width?: number

    /**
     * Default window height in pixels
     * @default 600
     */
    height?: number

    /**
     * Minimum window width in pixels
     * @default 400
     */
    minWidth?: number

    /**
     * Minimum window height in pixels
     * @default 300
     */
    minHeight?: number

    /**
     * Default window title (can be overridden when opening)
     */
    title?: string
  }

  /**
   * Custom widget properties (from Visual Editor)
   * Stores styling, glue, tokens per widget
   * Key: widgetId, Value: WidgetProperties
   */
  widgetProperties?: Record<string, any>
}

/**
 * Widget props interface
 *
 * All widgets receive these props from CustomizableModule
 */
export interface WidgetProps {
  /**
   * Data context from parent module
   * Shape is module-specific (not enforced by type system)
   *
   * @example
   * ```typescript
   * // PartInfoCard receives:
   * context: { part: Part, linkingGroup: LinkingGroup }
   *
   * // QuoteDetailCard receives:
   * context: { quote: Quote, items: QuoteItem[] }
   * ```
   */
  context?: Record<string, any>
}

/**
 * Widget events interface
 *
 * All widgets can emit these events
 */
export interface WidgetEvents {
  /**
   * Generic action event
   * Used for all widget actions (open material, open operations, etc.)
   *
   * @param action - Action name (e.g., 'open-material', 'open-operations')
   * @param payload - Optional action payload (e.g., { drawingId: 123 })
   *
   * @example
   * ```typescript
   * // In widget:
   * emit('action', 'open-material')
   * emit('action', 'open-drawing', { drawingId: 123 })
   *
   * // In module:
   * function handleWidgetAction(widgetId: string, action: string, payload?: any) {
   *   if (action === 'open-material') {
   *     windowsStore.openWindow('part-material', ...)
   *   }
   * }
   * ```
   */
  'action': [action: string, payload?: any]
}

/**
 * Layout export/import format
 *
 * Used for exporting/importing user layouts as JSON
 */
export interface LayoutExport {
  /**
   * Module key (must match when importing)
   */
  moduleKey: string

  /**
   * Widget layouts
   */
  layouts: WidgetLayout[]

  /**
   * Export format version (for future compatibility)
   */
  version: number

  /**
   * Export timestamp
   */
  exportedAt: string

  /**
   * Optional metadata
   */
  metadata?: {
    /**
     * User-provided layout name
     */
    name?: string

    /**
     * User-provided description
     */
    description?: string

    /**
     * Density mode when exported
     */
    density?: 'compact' | 'comfortable'
  }
}
