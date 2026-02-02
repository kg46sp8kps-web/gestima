/**
 * usePartLayoutSettings - Composable for module layout settings
 *
 * Features:
 * - Toggle between vertical (stacked) and horizontal (side-by-side) layouts
 * - localStorage persistence per module
 * - Default: vertical layout
 */

import { ref, onMounted, type Ref } from 'vue'

export type LayoutMode = 'horizontal' | 'vertical'

const DEFAULT_LAYOUT: LayoutMode = 'vertical' // vertical = side-by-side (default)

// Store separate state for each module
const layoutStates = new Map<string, { mode: Ref<LayoutMode>, initialized: boolean }>()

export function usePartLayoutSettings(moduleKey: string) {
  // Get or create state for this module
  if (!layoutStates.has(moduleKey)) {
    layoutStates.set(moduleKey, {
      mode: ref<LayoutMode>(DEFAULT_LAYOUT),
      initialized: false
    })
  }

  const state = layoutStates.get(moduleKey)!
  const layoutMode = state.mode
  const storageKey = `${moduleKey}-layout-mode`

  // Load from localStorage only once per module
  onMounted(() => {
    if (!state.initialized) {
      const stored = localStorage.getItem(storageKey)
      if (stored === 'vertical' || stored === 'horizontal') {
        layoutMode.value = stored
      }
      state.initialized = true
    }
  })

  function setLayoutMode(mode: LayoutMode) {
    layoutMode.value = mode
    localStorage.setItem(storageKey, mode)
  }

  function toggleLayout() {
    const newMode = layoutMode.value === 'vertical' ? 'horizontal' : 'vertical'
    setLayoutMode(newMode)
  }

  return {
    layoutMode,
    setLayoutMode,
    toggleLayout
  }
}
