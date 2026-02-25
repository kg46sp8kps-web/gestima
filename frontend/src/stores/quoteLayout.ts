import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'gestima:quote-layout-default'

function loadDefault(): 'vertical' | 'horizontal' {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'horizontal' ? 'horizontal' : 'vertical'
}

/**
 * Per-tile layout mode for the Quotes module.
 * Keyed by leafId so multiple quote tiles can have independent layouts.
 * The last toggled mode is persisted to localStorage as global default.
 */
export const useQuoteLayoutStore = defineStore('quoteLayout', () => {
  const defaultMode = ref<'vertical' | 'horizontal'>(loadDefault())
  const modes = ref<Record<string, 'vertical' | 'horizontal'>>({})

  function getMode(leafId: string): 'vertical' | 'horizontal' {
    return modes.value[leafId] ?? defaultMode.value
  }

  function toggle(leafId: string) {
    const next = getMode(leafId) === 'vertical' ? 'horizontal' : 'vertical'
    modes.value = { ...modes.value, [leafId]: next }
    defaultMode.value = next
    localStorage.setItem(STORAGE_KEY, next)
  }

  function cleanup(leafId: string) {
    const next = { ...modes.value }
    delete next[leafId]
    modes.value = next
  }

  return { getMode, toggle, cleanup }
})
