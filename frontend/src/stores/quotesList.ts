import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as quotesApi from '@/api/quotes'
import type { QuoteListItem } from '@/types/quote'

export const useQuotesListStore = defineStore('quotesList', () => {
  const ui = useUiStore()

  const items = ref<QuoteListItem[]>([])
  const loaded = ref(false)

  async function fetchIfNeeded(): Promise<void> {
    if (loaded.value) return
    try {
      items.value = await quotesApi.getAll()
      loaded.value = true
    } catch {
      ui.showError('Chyba při načítání nabídek')
    }
  }

  function setItems(data: QuoteListItem[]) {
    items.value = data
    loaded.value = true
  }

  return { items, loaded, fetchIfNeeded, setItems }
})
