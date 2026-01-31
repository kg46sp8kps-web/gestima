/**
 * Partners Store - Manages partners list and CRUD operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Partner, PartnerCreate, PartnerUpdate } from '@/types/partner'
import * as partnersApi from '@/api/partners'
import { useUiStore } from './ui'

export const usePartnersStore = defineStore('partners', () => {
  const ui = useUiStore()

  // State
  const partners = ref<Partner[]>([])
  const currentPartner = ref<Partner | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const searchQuery = ref('')
  const skip = ref(0)
  const limit = ref(50)

  // Computed
  const hasPartners = computed(() => partners.value.length > 0)
  const hasMore = computed(() => skip.value + limit.value < total.value)
  const currentPage = computed(() => Math.floor(skip.value / limit.value) + 1)
  const totalPages = computed(() => Math.ceil(total.value / limit.value))

  // Filter by type
  const customers = computed(() => partners.value.filter(p => p.is_customer))
  const suppliers = computed(() => partners.value.filter(p => p.is_supplier))

  // Actions
  async function fetchPartners(partnerType?: 'customer' | 'supplier') {
    loading.value = true
    try {
      if (searchQuery.value.trim()) {
        const response = await partnersApi.searchPartners(
          searchQuery.value,
          skip.value,
          limit.value
        )
        partners.value = response.partners
        total.value = response.total
      } else {
        const data = await partnersApi.getPartners(skip.value, limit.value, partnerType)
        partners.value = data
        total.value = data.length
      }
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání partnerů')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchPartner(partnerNumber: string) {
    loading.value = true
    try {
      currentPartner.value = await partnersApi.getPartner(partnerNumber)
      return currentPartner.value
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání partnera')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createPartner(data: PartnerCreate) {
    loading.value = true
    try {
      const newPartner = await partnersApi.createPartner(data)
      partners.value.unshift(newPartner)
      total.value++
      ui.showSuccess('Partner vytvořen')
      return newPartner
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při vytváření partnera')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updatePartner(partnerNumber: string, data: PartnerUpdate) {
    loading.value = true
    try {
      const updatedPartner = await partnersApi.updatePartner(partnerNumber, data)

      // Update in list
      const index = partners.value.findIndex(p => p.partner_number === partnerNumber)
      if (index !== -1) {
        partners.value[index] = updatedPartner
      }

      // Update current partner
      if (currentPartner.value?.partner_number === partnerNumber) {
        currentPartner.value = updatedPartner
      }

      ui.showSuccess('Partner aktualizován')
      return updatedPartner
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při aktualizaci partnera')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deletePartner(partnerNumber: string) {
    loading.value = true
    try {
      await partnersApi.deletePartner(partnerNumber)

      // Remove from list
      const index = partners.value.findIndex(p => p.partner_number === partnerNumber)
      if (index !== -1) {
        partners.value.splice(index, 1)
        total.value--
      }

      // Clear current partner if it was deleted
      if (currentPartner.value?.partner_number === partnerNumber) {
        currentPartner.value = null
      }

      ui.showSuccess('Partner smazán')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání partnera')
      throw error
    } finally {
      loading.value = false
    }
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
    skip.value = 0
  }

  function nextPage() {
    if (hasMore.value) {
      skip.value += limit.value
      fetchPartners()
    }
  }

  function prevPage() {
    if (skip.value > 0) {
      skip.value = Math.max(0, skip.value - limit.value)
      fetchPartners()
    }
  }

  function goToPage(page: number) {
    skip.value = (page - 1) * limit.value
    fetchPartners()
  }

  function setLimit(newLimit: number) {
    limit.value = newLimit
    skip.value = 0
    fetchPartners()
  }

  function reset() {
    partners.value = []
    currentPartner.value = null
    total.value = 0
    searchQuery.value = ''
    skip.value = 0
    limit.value = 50
  }

  return {
    // State
    partners,
    currentPartner,
    total,
    loading,
    searchQuery,
    skip,
    limit,
    // Computed
    hasPartners,
    hasMore,
    currentPage,
    totalPages,
    customers,
    suppliers,
    // Actions
    fetchPartners,
    fetchPartner,
    createPartner,
    updatePartner,
    deletePartner,
    setSearchQuery,
    nextPage,
    prevPage,
    goToPage,
    setLimit,
    reset
  }
})
