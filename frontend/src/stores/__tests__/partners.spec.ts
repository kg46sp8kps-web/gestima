/**
 * GESTIMA Partners Store Tests
 *
 * Tests partners CRUD operations, pagination, search, and filtering by type.
 */

import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePartnersStore } from '../partners'
import { useUiStore } from '../ui'
import * as partnersApi from '@/api/partners'
import type { Partner, PartnerCreate, PartnerUpdate } from '@/types/partner'

// Mock partners API
vi.mock('@/api/partners', () => ({
  getPartners: vi.fn(),
  searchPartners: vi.fn(),
  getPartner: vi.fn(),
  createPartner: vi.fn(),
  updatePartner: vi.fn(),
  deletePartner: vi.fn()
}))

// Helper to create valid Partner mock
function createMockPartner(overrides: Partial<Partner> = {}): Partner {
  return {
    id: 1,
    partner_number: 'P000001',
    company_name: 'Test Company',
    ico: '12345678',
    dic: 'CZ12345678',
    email: 'test@example.com',
    phone: '+420123456789',
    contact_person: 'John Doe',
    street: 'Test Street 123',
    city: 'Prague',
    postal_code: '10000',
    country: 'CZ',
    is_customer: true,
    is_supplier: false,
    notes: '',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides
  }
}

describe('Partners Store', () => {
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
      const store = usePartnersStore()

      expect(store.partners).toEqual([])
      expect(store.currentPartner).toBeNull()
      expect(store.total).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
      expect(store.hasPartners).toBe(false)
      expect(store.hasMore).toBe(false)
      expect(store.currentPage).toBe(1)
      expect(store.totalPages).toBe(0)
      expect(store.customers).toEqual([])
      expect(store.suppliers).toEqual([])
    })
  })

  // ==========================================================================
  // FETCH PARTNERS (LIST)
  // ==========================================================================

  describe('Fetch Partners', () => {
    const mockPartners: Partner[] = [
      createMockPartner({ id: 1, partner_number: 'P000001', company_name: 'Customer A', is_customer: true, is_supplier: false }),
      createMockPartner({ id: 2, partner_number: 'P000002', company_name: 'Supplier B', is_customer: false, is_supplier: true })
    ]

    it('should fetch partners successfully', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartners as Mock).mockResolvedValue(mockPartners)

      await store.fetchPartners()

      expect(partnersApi.getPartners).toHaveBeenCalledWith(0, 50, undefined)
      expect(store.partners).toEqual(mockPartners)
      expect(store.total).toBe(2)
      expect(store.loading).toBe(false)
      expect(store.hasPartners).toBe(true)
    })

    it('should fetch partners with type filter', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartners as Mock).mockResolvedValue(mockPartners)

      await store.fetchPartners('customer')

      expect(partnersApi.getPartners).toHaveBeenCalledWith(0, 50, 'customer')
    })

    it('should set loading=true during fetch', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartners as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), 100))
      )

      const promise = store.fetchPartners()
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('should handle fetch error', async () => {
      const store = usePartnersStore()
      const error = new Error('Network error')
      ;(partnersApi.getPartners as Mock).mockRejectedValue(error)

      await expect(store.fetchPartners()).rejects.toThrow('Network error')
      expect(store.loading).toBe(false)
      expect(uiStore.toasts.length).toBeGreaterThan(0)
      expect(uiStore.toasts[0]!.type).toBe('error')
    })

    it('should use pagination parameters', async () => {
      const store = usePartnersStore()
      store.skip = 50
      store.limit = 100
      ;(partnersApi.getPartners as Mock).mockResolvedValue([])

      await store.fetchPartners()

      expect(partnersApi.getPartners).toHaveBeenCalledWith(50, 100, undefined)
    })
  })

  // ==========================================================================
  // COMPUTED FILTERS
  // ==========================================================================

  describe('Computed Filters', () => {
    const mockPartners: Partner[] = [
      createMockPartner({ id: 1, partner_number: 'P000001', company_name: 'Customer A', is_customer: true, is_supplier: false }),
      createMockPartner({ id: 2, partner_number: 'P000002', company_name: 'Supplier B', is_customer: false, is_supplier: true }),
      createMockPartner({ id: 3, partner_number: 'P000003', company_name: 'Both C', is_customer: true, is_supplier: true })
    ]

    it('should filter customers correctly', () => {
      const store = usePartnersStore()
      store.partners = mockPartners

      expect(store.customers).toHaveLength(2)
      expect(store.customers.map(p => p.partner_number)).toEqual(['P000001', 'P000003'])
    })

    it('should filter suppliers correctly', () => {
      const store = usePartnersStore()
      store.partners = mockPartners

      expect(store.suppliers).toHaveLength(2)
      expect(store.suppliers.map(p => p.partner_number)).toEqual(['P000002', 'P000003'])
    })
  })

  // ==========================================================================
  // SEARCH PARTNERS
  // ==========================================================================

  describe('Search Partners', () => {
    it('should search partners when searchQuery is set', async () => {
      const store = usePartnersStore()
      const searchResponse = {
        partners: [createMockPartner({ company_name: 'Searched Company' })],
        total: 1
      }
      ;(partnersApi.searchPartners as Mock).mockResolvedValue(searchResponse)

      store.setSearchQuery('Searched')
      await store.fetchPartners()

      expect(partnersApi.searchPartners).toHaveBeenCalledWith('Searched', 0, 50)
      expect(store.partners).toEqual(searchResponse.partners)
      expect(store.total).toBe(1)
    })

    it('should reset skip when setting search query', () => {
      const store = usePartnersStore()
      store.skip = 100

      store.setSearchQuery('test')

      expect(store.skip).toBe(0)
      expect(store.searchQuery).toBe('test')
    })

    it('should NOT search when query is whitespace-only', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartners as Mock).mockResolvedValue([])

      store.setSearchQuery('   ')
      await store.fetchPartners()

      expect(partnersApi.searchPartners).not.toHaveBeenCalled()
      expect(partnersApi.getPartners).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // FETCH SINGLE PARTNER
  // ==========================================================================

  describe('Fetch Single Partner', () => {
    const mockPartner = createMockPartner()

    it('should fetch single partner successfully', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartner as Mock).mockResolvedValue(mockPartner)

      await store.fetchPartner('P000001')

      expect(partnersApi.getPartner).toHaveBeenCalledWith('P000001')
      expect(store.currentPartner).toEqual(mockPartner)
    })

    it('should handle fetch error', async () => {
      const store = usePartnersStore()
      ;(partnersApi.getPartner as Mock).mockRejectedValue(new Error('Not found'))

      await expect(store.fetchPartner('P999999')).rejects.toThrow('Not found')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // CREATE PARTNER
  // ==========================================================================

  describe('Create Partner', () => {
    it('should create partner successfully', async () => {
      const store = usePartnersStore()
      const createData: PartnerCreate = {
        company_name: 'New Company',
        is_customer: true,
        is_supplier: false,
        country: 'CZ'
      }
      const newPartner = createMockPartner({
        id: 10,
        partner_number: 'P000010',
        company_name: 'New Company',
        created_at: '2026-01-29T00:00:00Z',
        updated_at: '2026-01-29T00:00:00Z'
      })
      ;(partnersApi.createPartner as Mock).mockResolvedValue(newPartner)

      const result = await store.createPartner(createData)

      expect(partnersApi.createPartner).toHaveBeenCalledWith(createData)
      expect(result).toEqual(newPartner)
      expect(store.partners[0]).toEqual(newPartner) // Unshift to beginning
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle create error', async () => {
      const store = usePartnersStore()
      ;(partnersApi.createPartner as Mock).mockRejectedValue(new Error('Duplicate'))

      await expect(store.createPartner({ company_name: 'Test', is_customer: true, is_supplier: false }))
        .rejects.toThrow('Duplicate')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // UPDATE PARTNER
  // ==========================================================================

  describe('Update Partner', () => {
    const existingPartner = createMockPartner({ company_name: 'Old Name' })

    it('should update partner successfully', async () => {
      const store = usePartnersStore()
      store.partners = [existingPartner]
      store.currentPartner = existingPartner

      const updateData: PartnerUpdate = {
        company_name: 'New Name',
        version: 1
      }
      const updatedPartner: Partner = {
        ...existingPartner,
        company_name: 'New Name',
        version: 2
      }
      ;(partnersApi.updatePartner as Mock).mockResolvedValue(updatedPartner)

      await store.updatePartner('P000001', updateData)

      expect(partnersApi.updatePartner).toHaveBeenCalledWith('P000001', updateData)
      expect(store.partners[0]!.company_name).toBe('New Name')
      expect(store.currentPartner?.company_name).toBe('New Name')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should update only in list if partner is in list', async () => {
      const store = usePartnersStore()
      store.partners = [existingPartner]
      store.currentPartner = null

      const updatedPartner = { ...existingPartner, company_name: 'Updated' }
      ;(partnersApi.updatePartner as Mock).mockResolvedValue(updatedPartner)

      await store.updatePartner('P000001', { company_name: 'Updated', version: 1 })

      expect(store.partners[0]!.company_name).toBe('Updated')
      expect(store.currentPartner).toBeNull()
    })

    it('should handle update error', async () => {
      const store = usePartnersStore()
      ;(partnersApi.updatePartner as Mock).mockRejectedValue(new Error('Version conflict'))

      await expect(
        store.updatePartner('P000001', { company_name: 'Test', version: 1 })
      ).rejects.toThrow('Version conflict')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // DELETE PARTNER
  // ==========================================================================

  describe('Delete Partner', () => {
    const partnerToDelete = createMockPartner({ company_name: 'To Delete' })

    it('should delete partner successfully', async () => {
      const store = usePartnersStore()
      store.partners = [partnerToDelete]
      store.total = 1
      ;(partnersApi.deletePartner as Mock).mockResolvedValue(undefined)

      await store.deletePartner('P000001')

      expect(partnersApi.deletePartner).toHaveBeenCalledWith('P000001')
      expect(store.partners).toHaveLength(0)
      expect(store.total).toBe(0)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should clear currentPartner if deleted', async () => {
      const store = usePartnersStore()
      store.partners = [partnerToDelete]
      store.currentPartner = partnerToDelete
      ;(partnersApi.deletePartner as Mock).mockResolvedValue(undefined)

      await store.deletePartner('P000001')

      expect(store.currentPartner).toBeNull()
    })

    it('should NOT clear currentPartner if different partner deleted', async () => {
      const store = usePartnersStore()
      const otherPartner = createMockPartner({ id: 2, partner_number: 'P000002' })
      store.partners = [partnerToDelete, otherPartner]
      store.currentPartner = otherPartner
      ;(partnersApi.deletePartner as Mock).mockResolvedValue(undefined)

      await store.deletePartner('P000001')

      expect(store.currentPartner).toEqual(otherPartner)
    })
  })

  // ==========================================================================
  // PAGINATION
  // ==========================================================================

  describe('Pagination', () => {
    beforeEach(() => {
      ;(partnersApi.getPartners as Mock).mockResolvedValue([])
    })

    it('should calculate hasMore correctly', () => {
      const store = usePartnersStore()
      store.skip = 0
      store.limit = 50
      store.total = 120

      expect(store.hasMore).toBe(true)

      store.skip = 100
      expect(store.hasMore).toBe(false)
    })

    it('should calculate currentPage correctly', () => {
      const store = usePartnersStore()
      store.limit = 50

      store.skip = 0
      expect(store.currentPage).toBe(1)

      store.skip = 50
      expect(store.currentPage).toBe(2)

      store.skip = 100
      expect(store.currentPage).toBe(3)
    })

    it('should calculate totalPages correctly', () => {
      const store = usePartnersStore()
      store.limit = 50

      store.total = 120
      expect(store.totalPages).toBe(3)

      store.total = 100
      expect(store.totalPages).toBe(2)

      store.total = 25
      expect(store.totalPages).toBe(1)
    })

    it('should go to next page', async () => {
      const store = usePartnersStore()
      store.skip = 0
      store.limit = 50
      store.total = 150

      await store.nextPage()

      expect(store.skip).toBe(50)
      expect(partnersApi.getPartners).toHaveBeenCalled()
    })

    it('should NOT go to next page if no more', async () => {
      const store = usePartnersStore()
      store.skip = 100
      store.limit = 50
      store.total = 120

      await store.nextPage()

      expect(store.skip).toBe(100)
      expect(partnersApi.getPartners).not.toHaveBeenCalled()
    })

    it('should go to previous page', async () => {
      const store = usePartnersStore()
      store.skip = 50
      store.limit = 50

      await store.prevPage()

      expect(store.skip).toBe(0)
      expect(partnersApi.getPartners).toHaveBeenCalled()
    })

    it('should NOT go to previous page if already first', async () => {
      const store = usePartnersStore()
      store.skip = 0

      await store.prevPage()

      expect(store.skip).toBe(0)
      expect(partnersApi.getPartners).not.toHaveBeenCalled()
    })

    it('should go to specific page', async () => {
      const store = usePartnersStore()
      store.limit = 50

      await store.goToPage(3)

      expect(store.skip).toBe(100) // (3-1) * 50
      expect(partnersApi.getPartners).toHaveBeenCalled()
    })

    it('should change limit and reset to first page', async () => {
      const store = usePartnersStore()
      store.skip = 100

      await store.setLimit(100)

      expect(store.limit).toBe(100)
      expect(store.skip).toBe(0)
      expect(partnersApi.getPartners).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // RESET
  // ==========================================================================

  describe('Reset', () => {
    it('should reset store to initial state', () => {
      const store = usePartnersStore()
      store.partners = [createMockPartner()]
      store.currentPartner = store.partners[0] ?? null
      store.total = 100
      store.searchQuery = 'test'
      store.skip = 50
      store.limit = 100

      store.reset()

      expect(store.partners).toEqual([])
      expect(store.currentPartner).toBeNull()
      expect(store.total).toBe(0)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
    })
  })
})
