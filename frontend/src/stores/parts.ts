import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import { useCatalogStore } from './catalog'
import * as partsApi from '@/api/parts'
import type { Part, PartCreate, PartUpdate, PartListParams, PartStatus } from '@/types/part'
import type { ContextGroup } from '@/types/workspace'

export const usePartsStore = defineStore('parts', () => {
  const ui = useUiStore()

  const items = ref<Part[]>([])
  const total = ref(0)
  const loading = ref(false)
  const search = ref('')
  const statusFilter = ref<PartStatus | ''>('')

  const hasParts = computed(() => items.value.length > 0)

  function getFocusedPart(ctx: ContextGroup): Part | null {
    const catalog = useCatalogStore()
    const focused = catalog.getFocusedItem(ctx)
    if (!focused || focused.type !== 'part') return null
    return items.value.find(p => p.part_number === focused.number) ?? null
  }

  function getFocusedPartNumber(ctx: ContextGroup): string | null {
    const catalog = useCatalogStore()
    const focused = catalog.getFocusedItem(ctx)
    if (!focused || focused.type !== 'part') return null
    return focused.number
  }

  function focusPart(partNumber: string, ctx: ContextGroup) {
    const catalog = useCatalogStore()
    catalog.focusItem({ type: 'part', number: partNumber }, ctx)
  }

  async function fetchAll(params?: PartListParams) {
    loading.value = true
    try {
      const result = await partsApi.getAll({
        limit: 500,
        search: search.value || undefined,
        status: statusFilter.value || undefined,
        ...params,
      })
      items.value = result.parts
      total.value = result.total
    } catch {
      ui.showError('Chyba při načítání dílů')
    } finally {
      loading.value = false
    }
  }

  async function refreshPart(partNumber: string): Promise<void> {
    try {
      const updated = await partsApi.getByNumber(partNumber)
      const idx = items.value.findIndex(p => p.part_number === partNumber)
      if (idx >= 0) {
        items.value[idx] = updated
      }
    } catch {
      // Silent — part may have been deleted
    }
  }

  async function createPart(payload: PartCreate): Promise<Part | null> {
    ui.startLoading()
    try {
      const part = await partsApi.create(payload)
      items.value.unshift(part)
      total.value++
      ui.showSuccess('Díl vytvořen')
      return part
    } catch {
      ui.showError('Chyba při vytváření dílu')
      return null
    } finally {
      ui.stopLoading()
    }
  }

  async function updatePart(partNumber: string, payload: PartUpdate): Promise<Part | null> {
    ui.startLoading()
    try {
      const updated = await partsApi.update(partNumber, payload)
      const idx = items.value.findIndex(p => p.part_number === partNumber)
      if (idx >= 0) items.value[idx] = updated
      ui.showSuccess('Díl uložen')
      return updated
    } catch {
      ui.showError('Chyba při ukládání dílu')
      return null
    } finally {
      ui.stopLoading()
    }
  }

  async function duplicatePart(partNumber: string): Promise<Part | null> {
    ui.startLoading()
    try {
      const copy = await partsApi.duplicate(partNumber)
      items.value.unshift(copy)
      total.value++
      ui.showSuccess('Díl duplikován')
      return copy
    } catch {
      ui.showError('Chyba při duplikaci dílu')
      return null
    } finally {
      ui.stopLoading()
    }
  }

  return {
    items,
    total,
    loading,
    search,
    statusFilter,
    hasParts,
    getFocusedPart,
    getFocusedPartNumber,
    focusPart,
    fetchAll,
    refreshPart,
    createPart,
    updatePart,
    duplicatePart,
  }
})
