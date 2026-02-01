/**
 * Quotes Store - Manages quotes list, CRUD operations, and workflow
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Quote,
  QuoteWithItems,
  QuoteCreate,
  QuoteUpdate,
  QuoteItemCreate,
  QuoteItemUpdate,
  QuoteStatus,
  QuoteRequestReview,
  QuoteFromRequestCreate
} from '@/types/quote'
import * as quotesApi from '@/api/quotes'
import { useUiStore } from './ui'

export const useQuotesStore = defineStore('quotes', () => {
  const ui = useUiStore()

  // State
  const quotes = ref<Quote[]>([])
  const currentQuote = ref<QuoteWithItems | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const searchQuery = ref('')
  const skip = ref(0)
  const limit = ref(50)

  // AI Quote Request Parsing state
  const aiParsing = ref(false)
  const aiReview = ref<QuoteRequestReview | null>(null)

  // Computed - Filter by status
  const hasQuotes = computed(() => quotes.value.length > 0)
  const hasMore = computed(() => skip.value + limit.value < total.value)
  const currentPage = computed(() => Math.floor(skip.value / limit.value) + 1)
  const totalPages = computed(() => Math.ceil(total.value / limit.value))

  const draftQuotes = computed(() => quotes.value.filter((q) => q.status === 'draft'))
  const sentQuotes = computed(() => quotes.value.filter((q) => q.status === 'sent'))
  const approvedQuotes = computed(() => quotes.value.filter((q) => q.status === 'approved'))
  const rejectedQuotes = computed(() => quotes.value.filter((q) => q.status === 'rejected'))

  // Actions - List & CRUD
  async function fetchQuotes(status?: QuoteStatus) {
    loading.value = true
    try {
      const response = await quotesApi.getQuotes(skip.value, limit.value, status)
      quotes.value = response.quotes
      total.value = response.total
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání nabídek')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchQuote(quoteNumber: string) {
    loading.value = true
    try {
      currentQuote.value = await quotesApi.getQuote(quoteNumber)
      return currentQuote.value
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createQuote(data: QuoteCreate) {
    loading.value = true
    try {
      const newQuote = await quotesApi.createQuote(data)
      quotes.value.unshift(newQuote)
      total.value++
      ui.showSuccess('Nabídka vytvořena')
      return newQuote
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při vytváření nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updateQuote(quoteNumber: string, data: QuoteUpdate) {
    loading.value = true
    try {
      const updatedQuote = await quotesApi.updateQuote(quoteNumber, data)

      // Update in list
      const index = quotes.value.findIndex((q) => q.quote_number === quoteNumber)
      if (index !== -1) {
        quotes.value[index] = updatedQuote
      }

      // Update current quote
      if (currentQuote.value?.quote_number === quoteNumber) {
        // Preserve items from current quote
        currentQuote.value = {
          ...updatedQuote,
          items: currentQuote.value.items,
          partner: currentQuote.value.partner
        }
      }

      ui.showSuccess('Nabídka aktualizována')
      return updatedQuote
    } catch (error: any) {
      // Handle edit lock (HTTP 409)
      if (error.response?.status === 409) {
        ui.showError('Nelze editovat odeslanou nabídku')
      } else {
        ui.showError(error.message || 'Chyba při aktualizaci nabídky')
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deleteQuote(quoteNumber: string) {
    loading.value = true
    try {
      await quotesApi.deleteQuote(quoteNumber)

      // Remove from list
      const index = quotes.value.findIndex((q) => q.quote_number === quoteNumber)
      if (index !== -1) {
        quotes.value.splice(index, 1)
        total.value--
      }

      // Clear current quote if it was deleted
      if (currentQuote.value?.quote_number === quoteNumber) {
        currentQuote.value = null
      }

      ui.showSuccess('Nabídka smazána')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  // Actions - Workflow
  async function sendQuote(quoteNumber: string) {
    loading.value = true
    try {
      const result = await quotesApi.sendQuote(quoteNumber)

      // Refresh current quote to get updated status
      await fetchQuote(quoteNumber)

      // Update in list
      const index = quotes.value.findIndex((q) => q.quote_number === quoteNumber)
      if (index !== -1 && currentQuote.value) {
        quotes.value[index] = { ...currentQuote.value }
      }

      ui.showSuccess('Nabídka odeslána')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při odesílání nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function approveQuote(quoteNumber: string) {
    loading.value = true
    try {
      const result = await quotesApi.approveQuote(quoteNumber)

      // Refresh current quote to get updated status
      await fetchQuote(quoteNumber)

      // Update in list
      const index = quotes.value.findIndex((q) => q.quote_number === quoteNumber)
      if (index !== -1 && currentQuote.value) {
        quotes.value[index] = { ...currentQuote.value }
      }

      ui.showSuccess('Nabídka schválena')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při schvalování nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function rejectQuote(quoteNumber: string) {
    loading.value = true
    try {
      const result = await quotesApi.rejectQuote(quoteNumber)

      // Refresh current quote to get updated status
      await fetchQuote(quoteNumber)

      // Update in list
      const index = quotes.value.findIndex((q) => q.quote_number === quoteNumber)
      if (index !== -1 && currentQuote.value) {
        quotes.value[index] = { ...currentQuote.value }
      }

      ui.showSuccess('Nabídka odmítnuta')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při odmítání nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function cloneQuote(quoteNumber: string) {
    loading.value = true
    try {
      const newQuote = await quotesApi.cloneQuote(quoteNumber)
      quotes.value.unshift(newQuote)
      total.value++
      ui.showSuccess(`Nabídka duplikována: ${newQuote.quote_number}`)
      return newQuote
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při duplikaci nabídky')
      throw error
    } finally {
      loading.value = false
    }
  }

  // Actions - Quote Items
  async function addQuoteItem(quoteNumber: string, data: QuoteItemCreate) {
    loading.value = true
    try {
      const result = await quotesApi.addQuoteItem(quoteNumber, data)

      // Refresh current quote to get updated items and totals
      await fetchQuote(quoteNumber)

      ui.showSuccess('Položka přidána')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při přidávání položky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updateQuoteItem(itemId: number, data: QuoteItemUpdate) {
    loading.value = true
    try {
      const result = await quotesApi.updateQuoteItem(itemId, data)

      // Refresh current quote to get updated items and totals
      if (currentQuote.value) {
        await fetchQuote(currentQuote.value.quote_number)
      }

      ui.showSuccess('Položka aktualizována')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při aktualizaci položky')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deleteQuoteItem(itemId: number) {
    loading.value = true
    try {
      const result = await quotesApi.deleteQuoteItem(itemId)

      // Refresh current quote to get updated items and totals
      if (currentQuote.value) {
        await fetchQuote(currentQuote.value.quote_number)
      }

      ui.showSuccess('Položka smazána')
      return result
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání položky')
      throw error
    } finally {
      loading.value = false
    }
  }

  // Actions - AI Quote Request Parsing (ADR-028)
  async function parseQuoteRequestPDF(file: File) {
    aiParsing.value = true
    aiReview.value = null
    try {
      aiReview.value = await quotesApi.parseQuoteRequest(file)
      ui.showSuccess('PDF úspěšně zpracováno AI')
      return aiReview.value
    } catch (error: any) {
      // Handle specific error codes
      if (error.response?.status === 413) {
        ui.showError('PDF je příliš velké (max 10 MB)')
      } else if (error.response?.status === 429) {
        ui.showError('Překročen limit AI parsování (10/hod). Zkuste později.')
      } else if (error.response?.status === 500) {
        ui.showError('AI parsing selhal. Zkontrolujte kvalitu PDF.')
      } else {
        ui.showError(error.message || 'Chyba při parsování PDF')
      }
      throw error
    } finally {
      aiParsing.value = false
    }
  }

  async function createQuoteFromParsedRequest(data: QuoteFromRequestCreate) {
    loading.value = true
    try {
      const newQuote = await quotesApi.createQuoteFromRequest(data)
      quotes.value.unshift(newQuote)
      total.value++

      // Clear AI state
      aiReview.value = null

      ui.showSuccess(`Nabídka ${newQuote.quote_number} vytvořena z poptávky`)
      return newQuote
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při vytváření nabídky z poptávky')
      throw error
    } finally {
      loading.value = false
    }
  }

  function clearAiReview() {
    aiReview.value = null
  }

  // Pagination
  function setSearchQuery(query: string) {
    searchQuery.value = query
    skip.value = 0 // Reset to first page
  }

  function nextPage(status?: QuoteStatus) {
    if (hasMore.value) {
      skip.value += limit.value
      fetchQuotes(status)
    }
  }

  function prevPage(status?: QuoteStatus) {
    if (skip.value > 0) {
      skip.value = Math.max(0, skip.value - limit.value)
      fetchQuotes(status)
    }
  }

  function goToPage(page: number, status?: QuoteStatus) {
    skip.value = (page - 1) * limit.value
    fetchQuotes(status)
  }

  function setLimit(newLimit: number, status?: QuoteStatus) {
    limit.value = newLimit
    skip.value = 0
    fetchQuotes(status)
  }

  function reset() {
    quotes.value = []
    currentQuote.value = null
    total.value = 0
    searchQuery.value = ''
    skip.value = 0
    limit.value = 50
  }

  return {
    // State
    quotes,
    currentQuote,
    total,
    loading,
    searchQuery,
    skip,
    limit,
    aiParsing,
    aiReview,

    // Computed
    hasQuotes,
    hasMore,
    currentPage,
    totalPages,
    draftQuotes,
    sentQuotes,
    approvedQuotes,
    rejectedQuotes,

    // Actions - CRUD
    fetchQuotes,
    fetchQuote,
    createQuote,
    updateQuote,
    deleteQuote,

    // Actions - Workflow
    sendQuote,
    approveQuote,
    rejectQuote,
    cloneQuote,

    // Actions - Items
    addQuoteItem,
    updateQuoteItem,
    deleteQuoteItem,

    // Actions - AI Quote Request Parsing
    parseQuoteRequestPDF,
    createQuoteFromParsedRequest,
    clearAiReview,

    // Pagination
    setSearchQuery,
    nextPage,
    prevPage,
    goToPage,
    setLimit,
    reset
  }
})
