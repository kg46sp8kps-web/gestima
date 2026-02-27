import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as partnersApi from '@/api/partners'
import type { Partner } from '@/types/partner'

export const usePartnersStore = defineStore('partners', () => {
  const ui = useUiStore()

  const items = ref<Partner[]>([])
  const loading = ref(false)
  const loaded = ref(false)

  async function fetchIfNeeded(): Promise<void> {
    if (loaded.value) return
    loading.value = true
    try {
      items.value = await partnersApi.getAll()
      loaded.value = true
    } catch {
      ui.showError('Chyba při načítání partnerů')
    } finally {
      loading.value = false
    }
  }

  return { items, loading, loaded, fetchIfNeeded }
})
