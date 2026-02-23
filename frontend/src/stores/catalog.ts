import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ContextGroup, CatalogFocusItem } from '@/types/workspace'

export const useCatalogStore = defineStore('catalog', () => {
  const focusByCtx = ref<Partial<Record<ContextGroup, CatalogFocusItem>>>({})

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

  return {
    focusByCtx,
    focusItem,
    getFocusedItem,
    clearFocus,
  }
})
