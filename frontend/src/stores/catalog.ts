import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ContextGroup, CatalogFocusItem } from '@/types/workspace'
import type { PriorityTier } from '@/types/production-planner'

export const useCatalogStore = defineStore('catalog', () => {
  const focusByCtx = ref<Partial<Record<ContextGroup, CatalogFocusItem>>>({})

  /** Cross-tile tier change notification (no re-fetch needed) */
  const lastTierChange = ref<{ job: string; suffix: string; tier: PriorityTier } | null>(null)

  function focusItem(item: CatalogFocusItem, ctx: ContextGroup) {
    focusByCtx.value = { ...focusByCtx.value, [ctx]: item }
  }

  function getFocusedItem(ctx: ContextGroup): CatalogFocusItem | null {
    return focusByCtx.value[ctx] ?? null
  }

  function clearFocus(ctx: ContextGroup) {
    const copy = { ...focusByCtx.value }
    delete copy[ctx]
    focusByCtx.value = copy
  }

  function notifyTierChange(job: string, suffix: string, tier: PriorityTier) {
    lastTierChange.value = { job, suffix, tier }
  }

  return {
    focusByCtx,
    lastTierChange,
    focusItem,
    getFocusedItem,
    clearFocus,
    notifyTierChange,
  }
})
