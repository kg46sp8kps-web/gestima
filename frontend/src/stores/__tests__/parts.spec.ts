/**
 * GESTIMA Parts Store Tests
 *
 * Tests parts CRUD operations, pagination, search, and state management.
 */

import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePartsStore } from '../parts'
import { useUiStore } from '../ui'
import * as partsApi from '@/api/parts'
import type { Part, PartCreate, PartUpdate } from '@/types/part'

// Mock parts API
vi.mock('@/api/parts', () => ({
  getParts: vi.fn(),
  searchParts: vi.fn(),
  getPart: vi.fn(),
  createPart: vi.fn(),
  updatePart: vi.fn(),
  duplicatePart: vi.fn(),
  deletePart: vi.fn()
}))

describe('Parts Store', () => {
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
      const store = usePartsStore()

      expect(store.parts).toEqual([])
      expect(store.currentPart).toBeNull()
      expect(store.total).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
      expect(store.hasParts).toBe(false)
      expect(store.hasMore).toBe(false)
      expect(store.currentPage).toBe(1)
      expect(store.totalPages).toBe(0)
    })
  })

  // ==========================================================================
  // FETCH PARTS (LIST)
  // ==========================================================================

  describe('Fetch Parts', () => {
    const mockParts: Part[] = [
      {
        id: 1,
        part_number: '1000001',
        name: 'Test Part 1',
        material_item_id: null,
        stock_type: 'bar',
        stock_diameter: null,
        stock_length: null,
        stock_width: null,
        stock_height: null,
        version: 1,
        created_at: '2026-01-01T00:00:00Z',
        created_by: 1
      },
      {
        id: 2,
        part_number: '1000002',
        name: 'Test Part 2',
        material_item_id: null,
        stock_type: 'sheet',
        stock_diameter: null,
        stock_length: null,
        stock_width: null,
        stock_height: null,
        version: 1,
        created_at: '2026-01-01T00:00:00Z',
        created_by: 1
      }
    ]

    it('should fetch parts successfully', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(mockParts)

      await store.fetchParts()

      expect(partsApi.getParts).toHaveBeenCalledWith(0, 50)
      expect(store.parts).toEqual(mockParts)
      expect(store.total).toBe(2)
      expect(store.loading).toBe(false)
      expect(store.hasParts).toBe(true)
    })

    it('should set loading=true during fetch', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), 100))
      )

      const promise = store.fetchParts()
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('should handle fetch error', async () => {
      const store = usePartsStore()
      const error = new Error('Network error')
      ;(partsApi.getParts as Mock).mockRejectedValue(error)

      await expect(store.fetchParts()).rejects.toThrow('Network error')
      expect(store.loading).toBe(false)
      expect(uiStore.toasts.length).toBeGreaterThan(0)
      expect(uiStore.toasts[0].type).toBe('error')
    })

    it('should use pagination parameters', async () => {
      const store = usePartsStore()
      store.skip = 50
      store.limit = 100
      ;(partsApi.getParts as Mock).mockResolvedValue([])

      await store.fetchParts()

      expect(partsApi.getParts).toHaveBeenCalledWith(50, 100)
    })
  })

  // ==========================================================================
  // SEARCH PARTS
  // ==========================================================================

  describe('Search Parts', () => {
    it('should search parts when searchQuery is set', async () => {
      const store = usePartsStore()
      const searchResponse = {
        parts: [
          {
            id: 1,
            part_number: '1000001',
            name: 'Searched Part',
            material_item_id: null,
            stock_type: 'bar' as const,
            stock_diameter: null,
            stock_length: null,
            stock_width: null,
            stock_height: null,
            version: 1,
            created_at: '2026-01-01T00:00:00Z',
            created_by: 1
          }
        ],
        total: 1,
        skip: 0,
        limit: 50
      }
      ;(partsApi.searchParts as Mock).mockResolvedValue(searchResponse)

      store.setSearchQuery('Searched')
      await store.fetchParts()

      expect(partsApi.searchParts).toHaveBeenCalledWith('Searched', 0, 50)
      expect(store.parts).toEqual(searchResponse.parts)
      expect(store.total).toBe(1)
    })

    it('should reset skip when setting search query', () => {
      const store = usePartsStore()
      store.skip = 100

      store.setSearchQuery('test')

      expect(store.skip).toBe(0)
      expect(store.searchQuery).toBe('test')
    })

    it('should NOT search when query is whitespace-only', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue([])

      store.setSearchQuery('   ')
      await store.fetchParts()

      expect(partsApi.searchParts).not.toHaveBeenCalled()
      expect(partsApi.getParts).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // FETCH SINGLE PART
  // ==========================================================================

  describe('Fetch Single Part', () => {
    const mockPart: Part = {
      id: 1,
      part_number: '1000001',
      name: 'Test Part',
      material_item_id: null,
      stock_type: 'bar',
      stock_diameter: null,
      stock_length: null,
      stock_width: null,
      stock_height: null,
      version: 1,
      created_at: '2026-01-01T00:00:00Z',
      created_by: 1
    }

    it('should fetch single part successfully', async () => {
      const store = usePartsStore()
      ;(partsApi.getPart as Mock).mockResolvedValue(mockPart)

      await store.fetchPart('1000001')

      expect(partsApi.getPart).toHaveBeenCalledWith('1000001')
      expect(store.currentPart).toEqual(mockPart)
    })

    it('should handle fetch error', async () => {
      const store = usePartsStore()
      ;(partsApi.getPart as Mock).mockRejectedValue(new Error('Not found'))

      await expect(store.fetchPart('9999999')).rejects.toThrow('Not found')
      expect(uiStore.toasts[0].type).toBe('error')
    })
  })

  // ==========================================================================
  // CREATE PART
  // ==========================================================================

  describe('Create Part', () => {
    it('should create part successfully', async () => {
      const store = usePartsStore()
      const createData: PartCreate = {
        name: 'New Part',
        stock_type: 'bar'
      }
      const newPart: Part = {
        id: 10,
        part_number: '1000010',
        name: 'New Part',
        material_item_id: null,
        stock_type: 'bar',
        stock_diameter: null,
        stock_length: null,
        stock_width: null,
        stock_height: null,
        version: 1,
        created_at: '2026-01-29T00:00:00Z',
        created_by: 1
      }
      ;(partsApi.createPart as Mock).mockResolvedValue(newPart)

      const result = await store.createPart(createData)

      expect(partsApi.createPart).toHaveBeenCalledWith(createData)
      expect(result).toEqual(newPart)
      expect(store.parts[0]).toEqual(newPart) // Unshift to beginning
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0].type).toBe('success')
    })

    it('should handle create error', async () => {
      const store = usePartsStore()
      ;(partsApi.createPart as Mock).mockRejectedValue(new Error('Duplicate'))

      await expect(store.createPart({ name: 'Test', stock_type: 'bar' }))
        .rejects.toThrow('Duplicate')
      expect(uiStore.toasts[0].type).toBe('error')
    })
  })

  // ==========================================================================
  // UPDATE PART
  // ==========================================================================

  describe('Update Part', () => {
    const existingPart: Part = {
      id: 1,
      part_number: '1000001',
      name: 'Old Name',
      material_item_id: null,
      stock_type: 'bar',
      stock_diameter: null,
      stock_length: null,
      stock_width: null,
      stock_height: null,
      version: 1,
      created_at: '2026-01-01T00:00:00Z',
      created_by: 1
    }

    it('should update part successfully', async () => {
      const store = usePartsStore()
      store.parts = [existingPart]
      store.currentPart = existingPart

      const updateData: PartUpdate = {
        name: 'New Name',
        version: 1
      }
      const updatedPart: Part = {
        ...existingPart,
        name: 'New Name',
        version: 2
      }
      ;(partsApi.updatePart as Mock).mockResolvedValue(updatedPart)

      await store.updatePart('1000001', updateData)

      expect(partsApi.updatePart).toHaveBeenCalledWith('1000001', updateData)
      expect(store.parts[0].name).toBe('New Name')
      expect(store.currentPart?.name).toBe('New Name')
      expect(uiStore.toasts[0].type).toBe('success')
    })

    it('should update only in list if part is in list', async () => {
      const store = usePartsStore()
      store.parts = [existingPart]
      store.currentPart = null // Not current

      const updatedPart = { ...existingPart, name: 'Updated' }
      ;(partsApi.updatePart as Mock).mockResolvedValue(updatedPart)

      await store.updatePart('1000001', { name: 'Updated', version: 1 })

      expect(store.parts[0].name).toBe('Updated')
      expect(store.currentPart).toBeNull()
    })

    it('should handle update error', async () => {
      const store = usePartsStore()
      ;(partsApi.updatePart as Mock).mockRejectedValue(new Error('Version conflict'))

      await expect(
        store.updatePart('1000001', { name: 'Test', version: 1 })
      ).rejects.toThrow('Version conflict')
      expect(uiStore.toasts[0].type).toBe('error')
    })
  })

  // ==========================================================================
  // DUPLICATE PART
  // ==========================================================================

  describe('Duplicate Part', () => {
    it('should duplicate part successfully', async () => {
      const store = usePartsStore()
      const duplicatedPart: Part = {
        id: 20,
        part_number: '1000020',
        name: 'Copy of Test Part',
        material_item_id: null,
        stock_type: 'bar',
        stock_diameter: null,
        stock_length: null,
        stock_width: null,
        stock_height: null,
        version: 1,
        created_at: '2026-01-29T00:00:00Z',
        created_by: 1
      }
      ;(partsApi.duplicatePart as Mock).mockResolvedValue(duplicatedPart)

      const result = await store.duplicatePart('1000001')

      expect(partsApi.duplicatePart).toHaveBeenCalledWith('1000001')
      expect(result).toEqual(duplicatedPart)
      expect(store.parts[0]).toEqual(duplicatedPart)
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0].message).toContain('1000020')
    })
  })

  // ==========================================================================
  // DELETE PART
  // ==========================================================================

  describe('Delete Part', () => {
    const partToDelete: Part = {
      id: 1,
      part_number: '1000001',
      name: 'To Delete',
      material_item_id: null,
      stock_type: 'bar',
      stock_diameter: null,
      stock_length: null,
      stock_width: null,
      stock_height: null,
      version: 1,
      created_at: '2026-01-01T00:00:00Z',
      created_by: 1
    }

    it('should delete part successfully', async () => {
      const store = usePartsStore()
      store.parts = [partToDelete]
      store.total = 1
      ;(partsApi.deletePart as Mock).mockResolvedValue(undefined)

      await store.deletePart('1000001')

      expect(partsApi.deletePart).toHaveBeenCalledWith('1000001')
      expect(store.parts).toHaveLength(0)
      expect(store.total).toBe(0)
      expect(uiStore.toasts[0].type).toBe('success')
    })

    it('should clear currentPart if deleted', async () => {
      const store = usePartsStore()
      store.parts = [partToDelete]
      store.currentPart = partToDelete
      ;(partsApi.deletePart as Mock).mockResolvedValue(undefined)

      await store.deletePart('1000001')

      expect(store.currentPart).toBeNull()
    })

    it('should NOT clear currentPart if different part deleted', async () => {
      const store = usePartsStore()
      const otherPart: Part = { ...partToDelete, id: 2, part_number: '1000002' }
      store.parts = [partToDelete, otherPart]
      store.currentPart = otherPart
      ;(partsApi.deletePart as Mock).mockResolvedValue(undefined)

      await store.deletePart('1000001')

      expect(store.currentPart).toEqual(otherPart)
    })
  })

  // ==========================================================================
  // PAGINATION
  // ==========================================================================

  describe('Pagination', () => {
    beforeEach(() => {
      ;(partsApi.getParts as Mock).mockResolvedValue([])
    })

    it('should calculate hasMore correctly', () => {
      const store = usePartsStore()
      store.skip = 0
      store.limit = 50
      store.total = 120

      expect(store.hasMore).toBe(true)

      store.skip = 100
      expect(store.hasMore).toBe(false)
    })

    it('should calculate currentPage correctly', () => {
      const store = usePartsStore()
      store.limit = 50

      store.skip = 0
      expect(store.currentPage).toBe(1)

      store.skip = 50
      expect(store.currentPage).toBe(2)

      store.skip = 100
      expect(store.currentPage).toBe(3)
    })

    it('should calculate totalPages correctly', () => {
      const store = usePartsStore()
      store.limit = 50

      store.total = 120
      expect(store.totalPages).toBe(3) // Math.ceil(120 / 50)

      store.total = 100
      expect(store.totalPages).toBe(2)

      store.total = 25
      expect(store.totalPages).toBe(1)
    })

    it('should go to next page', async () => {
      const store = usePartsStore()
      store.skip = 0
      store.limit = 50
      store.total = 150

      await store.nextPage()

      expect(store.skip).toBe(50)
      expect(partsApi.getParts).toHaveBeenCalled()
    })

    it('should NOT go to next page if no more', async () => {
      const store = usePartsStore()
      store.skip = 100
      store.limit = 50
      store.total = 120

      await store.nextPage()

      expect(store.skip).toBe(100) // No change
      expect(partsApi.getParts).not.toHaveBeenCalled()
    })

    it('should go to previous page', async () => {
      const store = usePartsStore()
      store.skip = 50
      store.limit = 50

      await store.prevPage()

      expect(store.skip).toBe(0)
      expect(partsApi.getParts).toHaveBeenCalled()
    })

    it('should NOT go to previous page if already first', async () => {
      const store = usePartsStore()
      store.skip = 0

      await store.prevPage()

      expect(store.skip).toBe(0)
      expect(partsApi.getParts).not.toHaveBeenCalled()
    })

    it('should go to specific page', async () => {
      const store = usePartsStore()
      store.limit = 50

      await store.goToPage(3)

      expect(store.skip).toBe(100) // (3-1) * 50
      expect(partsApi.getParts).toHaveBeenCalled()
    })

    it('should change limit and reset to first page', async () => {
      const store = usePartsStore()
      store.skip = 100

      await store.setLimit(100)

      expect(store.limit).toBe(100)
      expect(store.skip).toBe(0)
      expect(partsApi.getParts).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // RESET
  // ==========================================================================

  describe('Reset', () => {
    it('should reset store to initial state', () => {
      const store = usePartsStore()
      store.parts = [
        {
          id: 1,
          part_number: '1000001',
          name: 'Test',
          material_item_id: null,
          stock_type: 'bar',
          stock_diameter: null,
          stock_length: null,
          stock_width: null,
          stock_height: null,
          version: 1,
          created_at: '2026-01-01T00:00:00Z',
          created_by: 1
        }
      ]
      store.currentPart = store.parts[0]
      store.total = 100
      store.searchQuery = 'test'
      store.skip = 50
      store.limit = 100

      store.reset()

      expect(store.parts).toEqual([])
      expect(store.currentPart).toBeNull()
      expect(store.total).toBe(0)
      expect(store.searchQuery).toBe('')
      expect(store.skip).toBe(0)
      expect(store.limit).toBe(50)
    })
  })
})
