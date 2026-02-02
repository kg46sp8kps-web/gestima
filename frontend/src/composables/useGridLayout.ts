/**
 * useGridLayout - Composable for widget grid layout management
 *
 * Manages widget layout state, localStorage persistence, and default layouts.
 *
 * Features:
 * - Save/load layouts from localStorage
 * - Reset to default layout
 * - Add/remove widgets
 * - Density-aware defaults (compact vs comfortable)
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 * @example
 * ```typescript
 * const { layouts, updateLayout, resetToDefault } = useGridLayout(
 *   'part-detail',
 *   partDetailConfig
 * )
 * ```
 */

import { ref, computed, watch } from 'vue'
import type { WidgetLayout, ModuleLayoutConfig } from '@/types/widget'
import type { DensityMode } from '@/types/layout'

interface UseGridLayoutReturn {
  /**
   * Current widget layouts
   */
  layouts: ReturnType<typeof ref<WidgetLayout[]>>

  /**
   * Load layout from localStorage
   */
  loadLayout: () => void

  /**
   * Save layout to localStorage
   */
  saveLayout: () => void

  /**
   * Update layouts (from grid drag/resize)
   */
  updateLayout: (newLayouts: WidgetLayout[]) => void

  /**
   * Reset to default layout
   */
  resetToDefault: () => void

  /**
   * Add widget to layout
   */
  addWidget: (widgetId: string, position?: { x: number; y: number }) => void

  /**
   * Remove widget from layout
   */
  removeWidget: (widgetId: string) => void
}

export function useGridLayout(
  moduleKey: string,
  config: ModuleLayoutConfig
): UseGridLayoutReturn {
  const storageKey = `${moduleKey}-grid-layout`

  // Current layouts
  const layouts = ref<WidgetLayout[]>([])

  // Density mode (from design system)
  const densityMode = computed<DensityMode>(() => {
    const density = document.documentElement.dataset.density
    return (density === 'compact' || density === 'comfortable') ? density : 'compact'
  })

  // Default layout based on density
  const defaultLayout = computed<WidgetLayout[]>(() => {
    return densityMode.value === 'compact'
      ? config.defaultLayouts.compact
      : config.defaultLayouts.comfortable
  })

  /**
   * Load layout from localStorage
   */
  function loadLayout() {
    try {
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        const parsed = JSON.parse(stored) as WidgetLayout[]

        // Validate: Ensure all required widgets are present
        const requiredIds = config.widgets
          .filter(w => w.required)
          .map(w => w.id)

        const hasAllRequired = requiredIds.every(id =>
          parsed.some(l => l.i === id)
        )

        if (hasAllRequired) {
          layouts.value = parsed
          return
        }
      }
    } catch (error) {
      console.warn('Failed to load grid layout:', error)
    }

    // Fallback to default
    layouts.value = [...defaultLayout.value]
  }

  /**
   * Save layout to localStorage
   */
  function saveLayout() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(layouts.value))
    } catch (error) {
      console.warn('Failed to save grid layout:', error)
    }
  }

  /**
   * Update layouts (from grid drag/resize)
   */
  function updateLayout(newLayouts: WidgetLayout[]) {
    layouts.value = newLayouts
    saveLayout()
  }

  /**
   * Reset to default layout
   */
  function resetToDefault() {
    layouts.value = [...defaultLayout.value]
    saveLayout()
  }

  /**
   * Add widget to layout
   */
  function addWidget(widgetId: string, position?: { x: number; y: number }) {
    const widget = config.widgets.find(w => w.id === widgetId)
    if (!widget) {
      console.warn('Widget not found:', widgetId)
      return
    }

    // Check if already in layout
    if (layouts.value.some(l => l.i === widgetId)) {
      console.warn('Widget already in layout:', widgetId)
      return
    }

    // Find next available position (bottom of layout)
    const maxY = Math.max(...layouts.value.map(l => l.y + l.h), 0)

    const newLayout: WidgetLayout = {
      i: widget.id,
      x: position?.x ?? 0,
      y: position?.y ?? maxY,
      w: widget.defaultWidth,
      h: widget.defaultHeight,
      static: false
    }

    layouts.value.push(newLayout)
    saveLayout()
  }

  /**
   * Remove widget from layout
   */
  function removeWidget(widgetId: string) {
    // Check if widget is required
    const widget = config.widgets.find(w => w.id === widgetId)
    if (widget?.required) {
      console.warn('Cannot remove required widget:', widgetId)
      return
    }

    layouts.value = layouts.value.filter(l => l.i !== widgetId)
    saveLayout()
  }

  // Auto-save on changes
  watch(layouts, saveLayout, { deep: true })

  return {
    layouts,
    loadLayout,
    saveLayout,
    updateLayout,
    resetToDefault,
    addWidget,
    removeWidget
  }
}
