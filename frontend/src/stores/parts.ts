/**
 * Parts Store - Manages parts list and CRUD operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Part, PartCreate, PartUpdate } from '@/types/part'
import * as partsApi from '@/api/parts'
import { useUiStore } from './ui'

export const usePartsStore = defineStore('parts', () => {
  const ui = useUiStore()

  // State
  const parts = ref<Part[]>([])
  const currentPart = ref<Part | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const searchQuery = ref('')
  const skip = ref(0)
  const limit = ref(50)

  // Computed
  const hasParts = computed(() => parts.value.length > 0)
  const hasMore = computed(() => skip.value + limit.value < total.value)
  const currentPage = computed(() => Math.floor(skip.value / limit.value) + 1)
  const totalPages = computed(() => Math.ceil(total.value / limit.value))

  // Actions
  async function fetchParts() {
    loading.value = true
    try {
      if (searchQuery.value.trim()) {
        const response = await partsApi.searchParts(
          searchQuery.value,
          skip.value,
          limit.value
        )
        parts.value = response.parts
        total.value = response.total
      } else {
        const data = await partsApi.getParts(skip.value, limit.value)
        parts.value = data
        total.value = data.length // Simple pagination without total count
      }
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání dílů')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchPart(partNumber: string) {
    loading.value = true
    try {
      currentPart.value = await partsApi.getPart(partNumber)
      return currentPart.value
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání dílu')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createPart(data: PartCreate) {
    loading.value = true
    try {
      const newPart = await partsApi.createPart(data)
      parts.value.unshift(newPart)
      total.value++
      ui.showSuccess('Díl vytvořen')
      return newPart
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při vytváření dílu')
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

      ui.showSuccess('Díl aktualizován')
      return updatedPart
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při aktualizaci dílu')
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
      ui.showSuccess(`Díl duplikován: ${newPart.part_number}`)
      return newPart
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při duplikaci dílu')
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

      ui.showSuccess('Díl smazán')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání dílu')
      throw error
    } finally {
      loading.value = false
    }
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
    skip.value = 0 // Reset to first page
  }

  function nextPage() {
    if (hasMore.value) {
      skip.value += limit.value
      fetchParts()
    }
  }

  function prevPage() {
    if (skip.value > 0) {
      skip.value = Math.max(0, skip.value - limit.value)
      fetchParts()
    }
  }

  function goToPage(page: number) {
    skip.value = (page - 1) * limit.value
    fetchParts()
  }

  function setLimit(newLimit: number) {
    limit.value = newLimit
    skip.value = 0
    fetchParts()
  }

  function reset() {
    parts.value = []
    currentPart.value = null
    total.value = 0
    searchQuery.value = ''
    skip.value = 0
    limit.value = 50
  }

  return {
    // State
    parts,
    currentPart,
    total,
    loading,
    searchQuery,
    skip,
    limit,
    // Computed
    hasParts,
    hasMore,
    currentPage,
    totalPages,
    // Actions
    fetchParts,
    fetchPart,
    createPart,
    updatePart,
    duplicatePart,
    deletePart,
    setSearchQuery,
    nextPage,
    prevPage,
    goToPage,
    setLimit,
    reset
  }
})
