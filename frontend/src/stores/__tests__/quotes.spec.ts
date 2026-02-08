/**
 * GESTIMA Quotes Store Tests
 *
 * Tests quotes CRUD operations, workflow actions, items management, and state.
 */

import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useQuotesStore } from '../quotes'
import { useUiStore } from '../ui'
import * as quotesApi from '@/api/quotes'
import type { Quote, QuoteWithItems, QuoteCreate, QuoteUpdate, QuoteItemCreate } from '@/types/quote'

// Mock quotes API
vi.mock('@/api/quotes', () => ({
  getQuotes: vi.fn(),
  getQuote: vi.fn(),
  createQuote: vi.fn(),
  updateQuote: vi.fn(),
  deleteQuote: vi.fn(),
  sendQuote: vi.fn(),
  approveQuote: vi.fn(),
  rejectQuote: vi.fn(),
  cloneQuote: vi.fn(),
  addQuoteItem: vi.fn(),
  updateQuoteItem: vi.fn(),
  deleteQuoteItem: vi.fn()
}))

// Helper to create valid Quote mock
function createMockQuote(overrides: Partial<Quote> = {}): Quote {
  return {
    id: 1,
    quote_number: 'Q-001',
    partner_id: null,
    title: 'Test Quote',
    description: '',
    customer_request_number: null,    status: 'draft',
    valid_until: null,
    sent_at: null,
    approved_at: null,
    rejected_at: null,
    subtotal: 1000,
    discount_percent: 0,
    discount_amount: 0,
    tax_percent: 21,
    tax_amount: 210,
    total: 1210,
    currency: 'CZK',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides
  }
}

function createMockQuoteWithItems(overrides: Partial<QuoteWithItems> = {}): QuoteWithItems {
  return {
    ...createMockQuote(),
    items: [],
    partner: undefined,
    ...overrides
  }
}

describe('Quotes Store', () => {
  let uiStore: ReturnType<typeof useUiStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    uiStore = useUiStore()
    vi.clearAllMocks()

    // Mock console methods
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  // ==========================================================================
  // INITIAL STATE
  // ==========================================================================

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const store = useQuotesStore()

      expect(store.quotes).toEqual([])
      expect(store.currentQuote).toBeNull()
      expect(store.total).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
      expect(store.hasQuotes).toBe(false)
      expect(store.hasMore).toBe(false)
      expect(store.currentPage).toBe(1)
      expect(store.totalPages).toBe(0)
    })

    it('should have empty status filters', () => {
      const store = useQuotesStore()

      expect(store.draftQuotes).toEqual([])
      expect(store.sentQuotes).toEqual([])
      expect(store.approvedQuotes).toEqual([])
      expect(store.rejectedQuotes).toEqual([])
    })
  })

  // ==========================================================================
  // FETCH QUOTES (LIST)
  // ==========================================================================

  describe('Fetch Quotes', () => {
    const mockQuotes: Quote[] = [
      createMockQuote({ id: 1, quote_number: 'Q-001', status: 'draft' }),
      createMockQuote({ id: 2, quote_number: 'Q-002', status: 'sent' })
    ]

    it('should fetch quotes successfully', async () => {
      const store = useQuotesStore()
      ;(quotesApi.getQuotes as Mock).mockResolvedValue({
        quotes: mockQuotes,
        total: 2,
        skip: 0,
        limit: 50
      })

      await store.fetchQuotes()

      expect(quotesApi.getQuotes).toHaveBeenCalledWith(0, 50, undefined)
      expect(store.quotes).toEqual(mockQuotes)
      expect(store.total).toBe(2)
      expect(store.loading).toBe(false)
      expect(store.hasQuotes).toBe(true)
    })

    it('should fetch quotes with status filter', async () => {
      const store = useQuotesStore()
      const draftQuotes = [mockQuotes[0]!]
      ;(quotesApi.getQuotes as Mock).mockResolvedValue({
        quotes: draftQuotes,
        total: 1,
        skip: 0,
        limit: 50
      })

      await store.fetchQuotes('draft')

      expect(quotesApi.getQuotes).toHaveBeenCalledWith(0, 50, 'draft')
      expect(store.quotes).toEqual(draftQuotes)
      expect(store.total).toBe(1)
    })

    it('should set loading=true during fetch', async () => {
      const store = useQuotesStore()
      ;(quotesApi.getQuotes as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ quotes: [], total: 0, skip: 0, limit: 50 }), 100))
      )

      const promise = store.fetchQuotes()
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('should handle fetch error', async () => {
      const store = useQuotesStore()
      const error = new Error('Network error')
      ;(quotesApi.getQuotes as Mock).mockRejectedValue(error)

      await expect(store.fetchQuotes()).rejects.toThrow('Network error')
      expect(store.loading).toBe(false)
      expect(uiStore.toasts.length).toBeGreaterThan(0)
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // FETCH SINGLE QUOTE
  // ==========================================================================

  describe('Fetch Single Quote', () => {
    const mockQuote = createMockQuoteWithItems()

    it('should fetch single quote successfully', async () => {
      const store = useQuotesStore()
      ;(quotesApi.getQuote as Mock).mockResolvedValue(mockQuote)

      await store.fetchQuote('Q-001')

      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001')
      expect(store.currentQuote).toEqual(mockQuote)
    })

    it('should handle fetch error', async () => {
      const store = useQuotesStore()
      ;(quotesApi.getQuote as Mock).mockRejectedValue(new Error('Not found'))

      await expect(store.fetchQuote('Q-999')).rejects.toThrow('Not found')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // CREATE QUOTE
  // ==========================================================================

  describe('Create Quote', () => {
    it('should create quote successfully', async () => {
      const store = useQuotesStore()
      const createData: QuoteCreate = {
        title: 'New Quote',
        partner_id: 1
      }
      const newQuote = createMockQuote({
        id: 10,
        quote_number: 'Q-010',
        title: 'New Quote',
        partner_id: 1
      })
      ;(quotesApi.createQuote as Mock).mockResolvedValue(newQuote)

      const result = await store.createQuote(createData)

      expect(quotesApi.createQuote).toHaveBeenCalledWith(createData)
      expect(result).toEqual(newQuote)
      expect(store.quotes[0]).toEqual(newQuote) // Unshift to beginning
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle create error', async () => {
      const store = useQuotesStore()
      ;(quotesApi.createQuote as Mock).mockRejectedValue(new Error('Validation error'))

      await expect(store.createQuote({ title: 'Test' }))
        .rejects.toThrow('Validation error')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // UPDATE QUOTE
  // ==========================================================================

  describe('Update Quote', () => {
    const existingQuote = createMockQuoteWithItems({ title: 'Old Title', status: 'draft' })

    it('should update quote successfully', async () => {
      const store = useQuotesStore()
      store.quotes = [existingQuote]
      store.currentQuote = existingQuote

      const updateData: QuoteUpdate = {
        title: 'New Title',
        version: 1
      }
      const updatedQuote: Quote = {
        ...existingQuote,
        title: 'New Title',
        version: 2
      }
      ;(quotesApi.updateQuote as Mock).mockResolvedValue(updatedQuote)

      await store.updateQuote('Q-001', updateData)

      expect(quotesApi.updateQuote).toHaveBeenCalledWith('Q-001', updateData)
      expect(store.quotes[0]!.title).toBe('New Title')
      expect(store.currentQuote?.title).toBe('New Title')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle edit lock (HTTP 409)', async () => {
      const store = useQuotesStore()
      const error: any = new Error('Edit locked')
      error.response = { status: 409 }
      ;(quotesApi.updateQuote as Mock).mockRejectedValue(error)

      await expect(
        store.updateQuote('Q-001', { title: 'Test', version: 1 })
      ).rejects.toThrow('Edit locked')
      expect(uiStore.toasts[0]!.message).toContain('Nelze editovat')
    })

    it('should handle update error', async () => {
      const store = useQuotesStore()
      ;(quotesApi.updateQuote as Mock).mockRejectedValue(new Error('Version conflict'))

      await expect(
        store.updateQuote('Q-001', { title: 'Test', version: 1 })
      ).rejects.toThrow('Version conflict')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // DELETE QUOTE
  // ==========================================================================

  describe('Delete Quote', () => {
    const quoteToDelete = createMockQuote({ title: 'To Delete' })

    it('should delete quote successfully', async () => {
      const store = useQuotesStore()
      store.quotes = [quoteToDelete]
      store.total = 1
      ;(quotesApi.deleteQuote as Mock).mockResolvedValue(undefined)

      await store.deleteQuote('Q-001')

      expect(quotesApi.deleteQuote).toHaveBeenCalledWith('Q-001')
      expect(store.quotes).toHaveLength(0)
      expect(store.total).toBe(0)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should clear currentQuote if deleted', async () => {
      const store = useQuotesStore()
      store.quotes = [quoteToDelete]
      store.currentQuote = createMockQuoteWithItems(quoteToDelete)
      ;(quotesApi.deleteQuote as Mock).mockResolvedValue(undefined)

      await store.deleteQuote('Q-001')

      expect(store.currentQuote).toBeNull()
    })
  })

  // ==========================================================================
  // WORKFLOW ACTIONS
  // ==========================================================================

  describe('Workflow Actions', () => {
    const draftQuote = createMockQuoteWithItems({ status: 'draft' })

    it('should send quote (DRAFT -> SENT)', async () => {
      const store = useQuotesStore()
      store.quotes = [draftQuote]
      ;(quotesApi.sendQuote as Mock).mockResolvedValue({ message: 'Sent', version: 2 })
      const sentQuote = { ...draftQuote, status: 'sent' as const, version: 2 }
      ;(quotesApi.getQuote as Mock).mockResolvedValue(sentQuote)

      await store.sendQuote('Q-001')

      expect(quotesApi.sendQuote).toHaveBeenCalledWith('Q-001')
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001') // Refresh
      expect(store.currentQuote?.status).toBe('sent')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should approve quote (SENT -> APPROVED)', async () => {
      const store = useQuotesStore()
      const sentQuote = createMockQuoteWithItems({ status: 'sent' })
      store.quotes = [sentQuote]
      ;(quotesApi.approveQuote as Mock).mockResolvedValue({ message: 'Approved', version: 2 })
      const approvedQuote = { ...sentQuote, status: 'approved' as const, version: 2 }
      ;(quotesApi.getQuote as Mock).mockResolvedValue(approvedQuote)

      await store.approveQuote('Q-001')

      expect(quotesApi.approveQuote).toHaveBeenCalledWith('Q-001')
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001')
      expect(store.currentQuote?.status).toBe('approved')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should reject quote (SENT -> REJECTED)', async () => {
      const store = useQuotesStore()
      const sentQuote = createMockQuoteWithItems({ status: 'sent' })
      store.quotes = [sentQuote]
      ;(quotesApi.rejectQuote as Mock).mockResolvedValue({ message: 'Rejected', version: 2 })
      const rejectedQuote = { ...sentQuote, status: 'rejected' as const, version: 2 }
      ;(quotesApi.getQuote as Mock).mockResolvedValue(rejectedQuote)

      await store.rejectQuote('Q-001')

      expect(quotesApi.rejectQuote).toHaveBeenCalledWith('Q-001')
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001')
      expect(store.currentQuote?.status).toBe('rejected')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })
  })

  // ==========================================================================
  // CLONE QUOTE
  // ==========================================================================

  describe('Clone Quote', () => {
    it('should clone quote successfully', async () => {
      const store = useQuotesStore()
      const clonedQuote = createMockQuote({
        id: 20,
        quote_number: 'Q-020',
        title: 'Test Quote (kópia)',
        status: 'draft'
      })
      ;(quotesApi.cloneQuote as Mock).mockResolvedValue(clonedQuote)

      const result = await store.cloneQuote('Q-001')

      expect(quotesApi.cloneQuote).toHaveBeenCalledWith('Q-001')
      expect(result).toEqual(clonedQuote)
      expect(store.quotes[0]).toEqual(clonedQuote)
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0]!.message).toContain('Q-020')
    })
  })

  // ==========================================================================
  // QUOTE ITEMS
  // ==========================================================================

  describe('Quote Items', () => {
    const quoteWithItems = createMockQuoteWithItems({
      items: [
        {
          id: 1,
          quote_id: 1,
          seq: 1,
          part_id: 10,
          part_number: 'P-001',
          part_name: 'Test Part',
          quantity: 5,
          unit_price: 100,
          line_total: 500,
          notes: '',
          version: 1
        }
      ]
    })

    it('should add quote item and refresh quote', async () => {
      const store = useQuotesStore()
      store.currentQuote = quoteWithItems
      ;(quotesApi.addQuoteItem as Mock).mockResolvedValue({
        message: 'Item added',
        item_id: 2,
        version: 2
      })
      ;(quotesApi.getQuote as Mock).mockResolvedValue(quoteWithItems)

      const itemData: QuoteItemCreate = {
        part_id: 20,
        quantity: 10
      }

      await store.addQuoteItem('Q-001', itemData)

      expect(quotesApi.addQuoteItem).toHaveBeenCalledWith('Q-001', itemData)
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001') // Refresh for totals
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should update quote item and refresh quote', async () => {
      const store = useQuotesStore()
      store.currentQuote = quoteWithItems
      ;(quotesApi.updateQuoteItem as Mock).mockResolvedValue({
        message: 'Item updated',
        version: 2
      })
      ;(quotesApi.getQuote as Mock).mockResolvedValue(quoteWithItems)

      await store.updateQuoteItem(1, { quantity: 10, version: 1 })

      expect(quotesApi.updateQuoteItem).toHaveBeenCalledWith(1, { quantity: 10, version: 1 })
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should delete quote item and refresh quote', async () => {
      const store = useQuotesStore()
      store.currentQuote = quoteWithItems
      ;(quotesApi.deleteQuoteItem as Mock).mockResolvedValue({
        message: 'Item deleted',
        version: 2
      })
      ;(quotesApi.getQuote as Mock).mockResolvedValue({
        ...quoteWithItems,
        items: []
      })

      await store.deleteQuoteItem(1)

      expect(quotesApi.deleteQuoteItem).toHaveBeenCalledWith(1)
      expect(quotesApi.getQuote).toHaveBeenCalledWith('Q-001')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })
  })

  // ==========================================================================
  // STATUS FILTERS
  // ==========================================================================

  describe('Status Filters', () => {
    it('should filter quotes by status', () => {
      const store = useQuotesStore()
      store.quotes = [
        createMockQuote({ quote_number: 'Q-001', status: 'draft' }),
        createMockQuote({ quote_number: 'Q-002', status: 'sent' }),
        createMockQuote({ quote_number: 'Q-003', status: 'approved' }),
        createMockQuote({ quote_number: 'Q-004', status: 'rejected' }),
        createMockQuote({ quote_number: 'Q-005', status: 'draft' })
      ]

      expect(store.draftQuotes).toHaveLength(2)
      expect(store.sentQuotes).toHaveLength(1)
      expect(store.approvedQuotes).toHaveLength(1)
      expect(store.rejectedQuotes).toHaveLength(1)

      expect(store.draftQuotes[0]!.quote_number).toBe('Q-001')
      expect(store.sentQuotes[0]!.quote_number).toBe('Q-002')
      expect(store.approvedQuotes[0]!.quote_number).toBe('Q-003')
      expect(store.rejectedQuotes[0]!.quote_number).toBe('Q-004')
    })
  })

  // ==========================================================================
  // PAGINATION
  // ==========================================================================

  describe('Pagination', () => {
    beforeEach(() => {
      ;(quotesApi.getQuotes as Mock).mockResolvedValue({
        quotes: [],
        total: 0,
        skip: 0,
        limit: 50
      })
    })

    it('should calculate hasMore correctly', () => {
      const store = useQuotesStore()
      store.skip = 0
      store.limit = 50
      store.total = 120

      expect(store.hasMore).toBe(true)

      store.skip = 100
      expect(store.hasMore).toBe(false)
    })

    it('should go to next page', async () => {
      const store = useQuotesStore()
      store.skip = 0
      store.limit = 50
      store.total = 150

      await store.nextPage()

      expect(store.skip).toBe(50)
      expect(quotesApi.getQuotes).toHaveBeenCalled()
    })

    it('should go to previous page', async () => {
      const store = useQuotesStore()
      store.skip = 50
      store.limit = 50

      await store.prevPage()

      expect(store.skip).toBe(0)
      expect(quotesApi.getQuotes).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // RESET
  // ==========================================================================

  describe('Reset', () => {
    it('should reset store to initial state', () => {
      const store = useQuotesStore()
      store.quotes = [createMockQuote()]
      store.currentQuote = createMockQuoteWithItems()
      store.total = 100
      store.searchQuery = 'test'
      store.skip = 50
      store.limit = 100

      store.reset()

      expect(store.quotes).toEqual([])
      expect(store.currentQuote).toBeNull()
      expect(store.total).toBe(0)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
    })
  })
})
