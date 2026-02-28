import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as materialsApi from '@/api/materials'
import type { MaterialItem } from '@/types/material-item'

export const useMaterialItemsStore = defineStore('materialItems', () => {
  const ui = useUiStore()

  const items = ref<MaterialItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const loadingMore = ref(false)
  const loaded = ref(false)

  // Server-side filters
  const search = ref('')
  const shapeFilter = ref('')
  const normQuery = ref('')
  const diameterMin = ref<number | undefined>(undefined)
  const diameterMax = ref<number | undefined>(undefined)
  const widthMin = ref<number | undefined>(undefined)
  const widthMax = ref<number | undefined>(undefined)
  const thicknessMin = ref<number | undefined>(undefined)
  const thicknessMax = ref<number | undefined>(undefined)
  const wallThicknessMin = ref<number | undefined>(undefined)
  const wallThicknessMax = ref<number | undefined>(undefined)

  const initialLoading = computed(() => loading.value && items.value.length === 0)
  const hasMore = computed(() => items.value.length < total.value)

  // Stale response protection — generation counter
  let fetchGeneration = 0

  function _buildParams(skip: number, limit: number): materialsApi.MaterialItemListParams {
    return {
      skip,
      limit,
      search: search.value || undefined,
      shape: shapeFilter.value || undefined,
      norm_query: normQuery.value || undefined,
      diameter_min: diameterMin.value,
      diameter_max: diameterMax.value,
      width_min: widthMin.value,
      width_max: widthMax.value,
      thickness_min: thicknessMin.value,
      thickness_max: thicknessMax.value,
      wall_thickness_min: wallThicknessMin.value,
      wall_thickness_max: wallThicknessMax.value,
    }
  }

  async function fetchItems(reset = false) {
    if (loaded.value && !reset) return
    loading.value = true
    if (reset) { items.value = []; loaded.value = false }
    const gen = ++fetchGeneration
    const params = _buildParams(0, 200)
    try {
      const result = await materialsApi.getItems(params)
      if (gen !== fetchGeneration) return // stale response — ignore
      items.value = result.items
      total.value = result.total
      loaded.value = true
    } catch {
      if (gen !== fetchGeneration) return
      ui.showError('Chyba při načítání polotovarů')
    } finally {
      if (gen === fetchGeneration) loading.value = false
    }
  }

  async function loadMoreItems() {
    if (loadingMore.value || !hasMore.value) return
    loadingMore.value = true
    try {
      const result = await materialsApi.getItems(_buildParams(items.value.length, 50))
      items.value.push(...result.items)
    } catch {
      // silent
    } finally {
      loadingMore.value = false
    }
  }

  return {
    items, total, loading, loadingMore, loaded, initialLoading, hasMore,
    search, shapeFilter, normQuery,
    diameterMin, diameterMax, widthMin, widthMax, thicknessMin, thicknessMax, wallThicknessMin, wallThicknessMax,
    fetchItems, loadMoreItems,
  }
})
