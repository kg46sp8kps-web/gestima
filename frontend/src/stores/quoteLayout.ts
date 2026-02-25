import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Per-tile layout mode for the Quotes module.
 * Keyed by leafId so multiple quote tiles can have independent layouts.
 */
export const useQuoteLayoutStore = defineStore('quoteLayout', () => {
  const modes = ref<Record<string, 'vertical' | 'horizontal'>>({})

  function getMode(leafId: string): 'vertical' | 'horizontal' {
    return modes.value[leafId] ?? 'vertical'
  }

  function toggle(leafId: string) {
    modes.value = {
      ...modes.value,
      [leafId]: getMode(leafId) === 'vertical' ? 'horizontal' : 'vertical',
    }
  }

  function cleanup(leafId: string) {
    const next = { ...modes.value }
    delete next[leafId]
    modes.value = next
  }

  return { getMode, toggle, cleanup }
})
