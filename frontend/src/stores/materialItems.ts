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

  const initialLoading = computed(() => loading.value && items.value.length === 0)
  const hasMore = computed(() => items.value.length < total.value)

  async function fetchItems() {
    if (loaded.value) return
    loading.value = true
    try {
      const result = await materialsApi.getItems({ skip: 0, limit: 200 })
      items.value = result.items
      total.value = result.total
      loaded.value = true
    } catch {
      ui.showError('Chyba při načítání polotovarů')
    } finally {
      loading.value = false
    }
  }

  async function loadMoreItems() {
    if (loadingMore.value || !hasMore.value) return
    loadingMore.value = true
    try {
      const result = await materialsApi.getItems({ skip: items.value.length, limit: 50 })
      items.value.push(...result.items)
    } catch {
      // silent
    } finally {
      loadingMore.value = false
    }
  }

  return { items, total, loading, loadingMore, loaded, initialLoading, hasMore, fetchItems, loadMoreItems }
})
