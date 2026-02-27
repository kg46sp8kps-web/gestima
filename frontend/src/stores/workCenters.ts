import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as wcApi from '@/api/work-centers'
import type { WorkCenter } from '@/types/work-center'

export const useWorkCentersStore = defineStore('workCenters', () => {
  const ui = useUiStore()

  const items = ref<WorkCenter[]>([])
  const loading = ref(false)
  const loaded = ref(false)

  async function fetchIfNeeded(): Promise<void> {
    if (loaded.value) return
    loading.value = true
    try {
      items.value = (await wcApi.getAll()).filter(w => w.is_active)
      loaded.value = true
    } catch {
      ui.showError('Chyba při načítání pracovišť')
    } finally {
      loading.value = false
    }
  }

  return { items, loading, loaded, fetchIfNeeded }
})
