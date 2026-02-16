/**
 * Parts Store - Manages parts list with infinite scroll (lazy loading)
 *
 * fetchParts() = reset + load first batch
 * fetchMore()  = append next batch (called by IntersectionObserver in UI)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Part, PartCreate, PartUpdate } from '@/types/part'
import * as partsApi from '@/api/parts'
import { useUiStore } from './ui'

const PAGE_SIZE = 200   // First load — enough rows to fill any screen
const BATCH_SIZE = 50   // Incremental loads — small + fast for smooth scroll

export const usePartsStore = defineStore('parts', () => {
  const ui = useUiStore()

  // State
  const parts = ref<Part[]>([])
  const currentPart = ref<Part | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const loadingMore = ref(false)
  const searchQuery = ref('')
  const statusFilter = ref<string | undefined>(undefined)

  // True only on first load when parts list is empty (shows skeleton/spinner)
  // After first load, refreshes happen silently in background
  const initialLoading = computed(() => loading.value && parts.value.length === 0)

  // Computed
  const hasParts = computed(() => parts.value.length > 0)
  const hasMore = computed(() => parts.value.length < total.value)
  const allLoaded = computed(() => !hasMore.value && total.value > 0)

  // Legacy computed (kept for backwards compat)
  const skip = computed(() => parts.value.length)
  const limit = ref(PAGE_SIZE)
  const currentPage = computed(() => Math.floor(parts.value.length / PAGE_SIZE) + 1)
  const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))

  /**
   * Fetch parts — resets list and loads first batch.
   * Called on mount, filter change, search change.
   */
  async function fetchParts() {
    loading.value = true
    try {
      const response = await partsApi.getParts(
        0,
        PAGE_SIZE,
        statusFilter.value,
        searchQuery.value.trim() || undefined
      )
      parts.value = response.parts
      total.value = response.total
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri nacitani dilu')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch more parts — appends next batch.
   * Called by IntersectionObserver when user scrolls to bottom.
   */
  async function fetchMore() {
    if (loadingMore.value || !hasMore.value) return
    loadingMore.value = true
    try {
      const response = await partsApi.getParts(
        parts.value.length,
        BATCH_SIZE,
        statusFilter.value,
        searchQuery.value.trim() || undefined
      )
      parts.value.push(...response.parts)
      total.value = response.total
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri nacitani dalsich dilu')
    } finally {
      loadingMore.value = false
    }
  }

  async function fetchPart(partNumber: string) {
    loading.value = true
    try {
      currentPart.value = await partsApi.getPart(partNumber)
      return currentPart.value
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri nacitani dilu')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createPart(
    data: PartCreate,
    copyFrom?: {
      sourcePartNumber: string
      copyOperations: boolean
      copyMaterial: boolean
      copyBatches: boolean
    }
  ) {
    loading.value = true
    try {
      const newPart = await partsApi.createPart(data, copyFrom)
      parts.value.unshift(newPart)
      total.value++
      ui.showSuccess(copyFrom ? 'Dil zkopirovan' : 'Dil vytvoren')
      return newPart
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri vytvareni dilu')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updatePart(partNumber: string, data: PartUpdate) {
    loading.value = true
    try {
      const updatedPart = await partsApi.updatePart(partNumber, data)

      // Update in list
      const index = parts.value.findIndex(p => p.part_number === partNumber)
      if (index !== -1) {
        parts.value[index] = updatedPart
      }

      // Update current part
      if (currentPart.value?.part_number === partNumber) {
        currentPart.value = updatedPart
      }

      ui.showSuccess('Dil aktualizovan')
      return updatedPart
    } catch (error: any) {
      // Handle version conflict - auto-reload data
      if (error.response?.status === 409) {
        await fetchPart(partNumber)
        ui.showWarning('Data byla zmenena. Nactena aktualni verze - zkuste zmenu znovu.')
      } else {
        ui.showError(error.message || 'Chyba pri aktualizaci dilu')
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function duplicatePart(partNumber: string) {
    loading.value = true
    try {
      const newPart = await partsApi.duplicatePart(partNumber)
      parts.value.unshift(newPart)
      total.value++
      ui.showSuccess(`Dil duplikovan: ${newPart.part_number}`)
      return newPart
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri duplikaci dilu')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deletePart(partNumber: string) {
    loading.value = true
    try {
      await partsApi.deletePart(partNumber)

      // Remove from list
      const index = parts.value.findIndex(p => p.part_number === partNumber)
      if (index !== -1) {
        parts.value.splice(index, 1)
        total.value--
      }

      // Clear current part if it was deleted
      if (currentPart.value?.part_number === partNumber) {
        currentPart.value = null
      }

      ui.showSuccess('Dil smazan')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba pri mazani dilu')
      throw error
    } finally {
      loading.value = false
    }
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
  }

  function setStatusFilter(status: string | undefined) {
    statusFilter.value = status
  }

  // Legacy pagination methods (kept for backwards compat)
  function nextPage() {
    if (hasMore.value) fetchMore()
  }

  function prevPage() { /* no-op in infinite scroll */ }
  function goToPage(_page: number) { /* no-op in infinite scroll */ }
  function setLimit(_newLimit: number) { /* no-op in infinite scroll */ }

  function reset() {
    parts.value = []
    currentPart.value = null
    total.value = 0
    searchQuery.value = ''
    statusFilter.value = undefined
  }

  return {
    // State
    parts,
    currentPart,
    total,
    loading,
    loadingMore,
    searchQuery,
    statusFilter,
    skip,
    limit,
    // Computed
    hasParts,
    hasMore,
    allLoaded,
    initialLoading,
    currentPage,
    totalPages,
    // Actions
    fetchParts,
    fetchMore,
    fetchPart,
    createPart,
    updatePart,
    duplicatePart,
    deletePart,
    setSearchQuery,
    setStatusFilter,
    nextPage,
    prevPage,
    goToPage,
    setLimit,
    reset
  }
})
