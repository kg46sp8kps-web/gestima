/**
 * GESTIMA Parts Store Tests
 *
 * Tests parts CRUD operations, infinite scroll, search, and state management.
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
  getPart: vi.fn(),
  createPart: vi.fn(),
  updatePart: vi.fn(),
  duplicatePart: vi.fn(),
  deletePart: vi.fn()
}))

// Helper to create valid Part mock
function createMockPart(overrides: Partial<Part> = {}): Part {
  return {
    id: 1,
    part_number: '1000001',
    article_number: null,
    drawing_path: null,
    name: 'Test Part',
    customer_revision: null,
    revision: null,
    drawing_number: null,
    status: 'draft',
    source: 'manual',
    length: 0,
    notes: '',
    file_id: null,
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides
  }
}

// Helper to create API response
function createPartsResponse(parts: Part[], total?: number) {
  return {
    parts,
    total: total ?? parts.length,
    skip: 0,
    limit: 200
  }
}

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
      expect(store.loadingMore).toBe(false)
      expect(store.searchQuery).toBe('')
      expect(store.statusFilter).toBeUndefined()
      expect(store.hasParts).toBe(false)
      expect(store.hasMore).toBe(false)
      expect(store.initialLoading).toBe(false)
    })
  })

  // ==========================================================================
  // INITIAL LOADING (flicker prevention)
  // ==========================================================================

  describe('Initial Loading', () => {
    it('should be true only when loading AND parts are empty', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(createPartsResponse([createMockPart()])), 100))
      )

      // Before fetch: loading=false, parts=[] → initialLoading=false
      expect(store.initialLoading).toBe(false)

      // During first fetch: loading=true, parts=[] → initialLoading=true
      const promise = store.fetchParts()
      expect(store.initialLoading).toBe(true)

      await promise
      // After fetch: loading=false, parts=[1] → initialLoading=false
      expect(store.initialLoading).toBe(false)
    })

    it('should be false during refresh when parts exist', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse([createMockPart()]))

      // First load
      await store.fetchParts()
      expect(store.parts).toHaveLength(1)

      // Setup slow second fetch
      ;(partsApi.getParts as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(createPartsResponse([createMockPart({ id: 2 })])), 100))
      )

      // During refresh: loading=true but parts.length > 0 → initialLoading=false
      const promise = store.fetchParts()
      expect(store.loading).toBe(true)
      expect(store.initialLoading).toBe(false) // No flicker!

      await promise
    })
  })

  // ==========================================================================
  // FETCH PARTS (LIST)
  // ==========================================================================

  describe('Fetch Parts', () => {
    const mockParts: Part[] = [
      createMockPart({ id: 1, part_number: '1000001', name: 'Test Part 1' }),
      createMockPart({ id: 2, part_number: '1000002', name: 'Test Part 2' })
    ]

    it('should fetch parts successfully', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse(mockParts))

      await store.fetchParts()

      expect(partsApi.getParts).toHaveBeenCalledWith(0, 200, undefined, undefined, undefined)
      expect(store.parts).toEqual(mockParts)
      expect(store.total).toBe(2)
      expect(store.loading).toBe(false)
      expect(store.hasParts).toBe(true)
    })

    it('should set loading=true during fetch', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(createPartsResponse([])), 100))
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
      expect(uiStore.toasts[0]!.type).toBe('error')
    })

    it('should pass status filter to API', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse([]))

      store.setStatusFilter('active')
      await store.fetchParts()

      expect(partsApi.getParts).toHaveBeenCalledWith(0, 200, 'active', undefined, undefined)
    })

    it('should pass search query to API', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse([]))

      store.setSearchQuery('test')
      await store.fetchParts()

      expect(partsApi.getParts).toHaveBeenCalledWith(0, 200, undefined, 'test', undefined)
    })
  })

  // ==========================================================================
  // FETCH MORE (INFINITE SCROLL)
  // ==========================================================================

  describe('Fetch More', () => {
    it('should append parts to existing list', async () => {
      const store = usePartsStore()
      const firstBatch = [createMockPart({ id: 1 })]
      const secondBatch = [createMockPart({ id: 2 })]

      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse(firstBatch, 200))
      await store.fetchParts()
      expect(store.parts).toHaveLength(1)
      expect(store.hasMore).toBe(true)

      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse(secondBatch, 200))
      await store.fetchMore()
      expect(store.parts).toHaveLength(2)
    })

    it('should not fetch if no more items', async () => {
      const store = usePartsStore()
      ;(partsApi.getParts as Mock).mockResolvedValue(createPartsResponse([createMockPart()], 1))
      await store.fetchParts()

      expect(store.hasMore).toBe(false)
      await store.fetchMore()
      // getParts called only once (fetchParts), not again for fetchMore
      expect(partsApi.getParts).toHaveBeenCalledTimes(1)
    })
  })

  // ==========================================================================
  // FETCH SINGLE PART
  // ==========================================================================

  describe('Fetch Single Part', () => {
    const mockPart = createMockPart()

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
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // CREATE PART
  // ==========================================================================

  describe('Create Part', () => {
    it('should create part successfully', async () => {
      const store = usePartsStore()
      const createData: PartCreate = {
        article_number: 'ART-001',
        name: 'New Part'
      }
      const newPart = createMockPart({
        id: 10,
        part_number: '1000010',
        name: 'New Part',
        created_at: '2026-01-29T00:00:00Z',
        updated_at: '2026-01-29T00:00:00Z'
      })
      ;(partsApi.createPart as Mock).mockResolvedValue(newPart)

      const result = await store.createPart(createData)

      expect(partsApi.createPart).toHaveBeenCalledWith(createData, undefined)
      expect(result).toEqual(newPart)
      expect(store.parts[0]).toEqual(newPart) // Unshift to beginning
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle create error', async () => {
      const store = usePartsStore()
      ;(partsApi.createPart as Mock).mockRejectedValue(new Error('Duplicate'))

      await expect(store.createPart({ article_number: 'ART-002', name: 'Test' }))
        .rejects.toThrow('Duplicate')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // UPDATE PART
  // ==========================================================================

  describe('Update Part', () => {
    const existingPart = createMockPart({ name: 'Old Name' })

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
      expect(store.parts[0]!.name).toBe('New Name')
      expect(store.currentPart?.name).toBe('New Name')
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle update error', async () => {
      const store = usePartsStore()
      ;(partsApi.updatePart as Mock).mockRejectedValue(new Error('Version conflict'))

      await expect(
        store.updatePart('1000001', { name: 'Test', version: 1 })
      ).rejects.toThrow('Version conflict')
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // DUPLICATE PART
  // ==========================================================================

  describe('Duplicate Part', () => {
    it('should duplicate part successfully', async () => {
      const store = usePartsStore()
      const duplicatedPart = createMockPart({
        id: 20,
        part_number: '1000020',
        name: 'Copy of Test Part',
        created_at: '2026-01-29T00:00:00Z',
        updated_at: '2026-01-29T00:00:00Z'
      })
      ;(partsApi.duplicatePart as Mock).mockResolvedValue(duplicatedPart)

      const result = await store.duplicatePart('1000001')

      expect(partsApi.duplicatePart).toHaveBeenCalledWith('1000001')
      expect(result).toEqual(duplicatedPart)
      expect(store.parts[0]).toEqual(duplicatedPart)
      expect(store.total).toBe(1)
      expect(uiStore.toasts[0]!.message).toContain('1000020')
    })
  })

  // ==========================================================================
  // DELETE PART
  // ==========================================================================

  describe('Delete Part', () => {
    const partToDelete = createMockPart({ name: 'To Delete' })

    it('should delete part successfully', async () => {
      const store = usePartsStore()
      store.parts = [partToDelete]
      store.total = 1
      ;(partsApi.deletePart as Mock).mockResolvedValue(undefined)

      await store.deletePart('1000001')

      expect(partsApi.deletePart).toHaveBeenCalledWith('1000001')
      expect(store.parts).toHaveLength(0)
      expect(store.total).toBe(0)
      expect(uiStore.toasts[0]!.type).toBe('success')
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
      const otherPart = createMockPart({ id: 2, part_number: '1000002' })
      store.parts = [partToDelete, otherPart]
      store.currentPart = otherPart
      ;(partsApi.deletePart as Mock).mockResolvedValue(undefined)

      await store.deletePart('1000001')

      expect(store.currentPart).toEqual(otherPart)
    })
  })

  // ==========================================================================
  // RESET
  // ==========================================================================

  describe('Reset', () => {
    it('should reset store to initial state', () => {
      const store = usePartsStore()
      store.parts = [createMockPart()]
      store.currentPart = store.parts[0] ?? null
      store.total = 100
      store.searchQuery = 'test'

      store.reset()

      expect(store.parts).toEqual([])
      expect(store.currentPart).toBeNull()
      expect(store.total).toBe(0)
      expect(store.searchQuery).toBe('')
    })
  })
})
