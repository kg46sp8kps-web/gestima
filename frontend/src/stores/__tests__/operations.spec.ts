/**
 * GESTIMA Operations Store Tests
 *
 * Tests operations CRUD, work center integration, and computed totals.
 */

import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOperationsStore } from '../operations'
import { useUiStore } from '../ui'
import { operationsApi, workCentersApi } from '@/api/operations'
import type { Operation, WorkCenter, OperationCreate, OperationUpdate } from '@/types'

// Mock operations API
vi.mock('@/api/operations', () => ({
  operationsApi: {
    listByPart: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    changeMode: vi.fn()
  },
  workCentersApi: {
    list: vi.fn()
  }
}))

// Helper to create valid Operation mock
function createMockOperation(overrides: Partial<Operation> = {}): Operation {
  return {
    id: 1,
    part_id: 100,
    seq: 10,
    name: 'OP10 - Soustružení',
    type: 'turning',
    icon: '🔄',
    work_center_id: 1,
    cutting_mode: 'mid',
    setup_time_min: 15,
    operation_time_min: 5,
    setup_time_locked: false,
    operation_time_locked: false,
    is_coop: false,
    coop_type: null,
    coop_price: 0,
    coop_min_price: 0,
    coop_days: 0,
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides
  }
}

// Helper to create valid WorkCenter mock
function createMockWorkCenter(overrides: Partial<WorkCenter> = {}): WorkCenter {
  return {
    id: 1,
    number: 'WC-001',
    name: 'Soustruh 1',
    type: 'lathe',
    hourly_rate: 1200,
    is_active: true,
    ...overrides
  }
}

describe('Operations Store', () => {
  let uiStore: ReturnType<typeof useUiStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    uiStore = useUiStore()
    vi.clearAllMocks()
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'debug').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  // ==========================================================================
  // INITIAL STATE
  // ==========================================================================

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const store = useOperationsStore()

      expect(store.operations).toEqual([])
      expect(store.workCenters).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.saving).toBe(false)
      expect(store.error).toBeNull()
      expect(store.expandedOps).toEqual({})
      expect(store.totalSetupTime).toBe(0)
      expect(store.totalOperationTime).toBe(0)
    })
  })

  // ==========================================================================
  // LOAD WORK CENTERS
  // ==========================================================================

  describe('Load Work Centers', () => {
    const mockWorkCenters: WorkCenter[] = [
      createMockWorkCenter({ id: 1, number: 'WC-001', name: 'Soustruh 1', type: 'lathe' }),
      createMockWorkCenter({ id: 2, number: 'WC-002', name: 'Fréza 1', type: 'mill', hourly_rate: 1500 })
    ]

    it('should load work centers successfully', async () => {
      const store = useOperationsStore()
      ;(workCentersApi.list as Mock).mockResolvedValue(mockWorkCenters)

      await store.loadWorkCenters()

      expect(workCentersApi.list).toHaveBeenCalled()
      expect(store.workCenters).toEqual(mockWorkCenters)
    })

    it('should handle load error silently', async () => {
      const store = useOperationsStore()
      ;(workCentersApi.list as Mock).mockRejectedValue(new Error('Network error'))

      await store.loadWorkCenters()

      expect(store.workCenters).toEqual([])
      expect(console.error).toHaveBeenCalled()
    })

    it('should filter active work centers', () => {
      const store = useOperationsStore()
      store.workCenters = [
        createMockWorkCenter({ id: 1, is_active: true }),
        createMockWorkCenter({ id: 2, is_active: false })
      ]

      expect(store.activeWorkCenters).toHaveLength(1)
      expect(store.activeWorkCenters[0]!.name).toBe('Soustruh 1')
    })
  })

  // ==========================================================================
  // LOAD OPERATIONS
  // ==========================================================================

  describe('Load Operations', () => {
    const mockOperations: Operation[] = [
      createMockOperation({ id: 1, seq: 10, name: 'OP10 - Soustružení' }),
      createMockOperation({ id: 2, seq: 20, name: 'OP20 - Frézování', type: 'milling', icon: '⚙️', work_center_id: 2, setup_time_min: 20, operation_time_min: 10 })
    ]

    it('should load operations successfully', async () => {
      const store = useOperationsStore()
      ;(operationsApi.listByPart as Mock).mockResolvedValue(mockOperations)

      await store.loadOperations(100)

      expect(operationsApi.listByPart).toHaveBeenCalledWith(100)
      expect(store.operations).toEqual(mockOperations)
      expect(store.loading).toBe(false)
    })

    it('should set loading=true during fetch', async () => {
      const store = useOperationsStore()
      ;(operationsApi.listByPart as Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), 100))
      )

      const promise = store.loadOperations(100)
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('should handle load error', async () => {
      const store = useOperationsStore()
      ;(operationsApi.listByPart as Mock).mockRejectedValue(new Error('Server error'))

      await store.loadOperations(100)

      expect(store.operations).toEqual([])
      expect(store.error).toBe('Chyba při načítání operací')
      expect(console.error).toHaveBeenCalled()
    })

    it('should clear operations if partId is falsy', async () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      await store.loadOperations(0)

      expect(store.operations).toEqual([])
      expect(operationsApi.listByPart).not.toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================

  describe('Computed Properties', () => {
    const mockOperations: Operation[] = [
      createMockOperation({ id: 1, seq: 20, setup_time_min: 10, operation_time_min: 5, is_coop: false }),
      createMockOperation({ id: 2, seq: 10, setup_time_min: 15, operation_time_min: 8, is_coop: true, coop_price: 500 })
    ]

    it('should sort operations by sequence', () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      expect(store.sortedOperations[0]!.seq).toBe(10)
      expect(store.sortedOperations[1]!.seq).toBe(20)
    })

    it('should filter internal operations', () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      expect(store.internalOperations).toHaveLength(1)
      expect(store.internalOperations[0]!.is_coop).toBe(false)
    })

    it('should filter cooperation operations', () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      expect(store.coopOperations).toHaveLength(1)
      expect(store.coopOperations[0]!.is_coop).toBe(true)
    })

    it('should calculate total setup time', () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      expect(store.totalSetupTime).toBe(25) // 10 + 15
    })

    it('should calculate total operation time', () => {
      const store = useOperationsStore()
      store.operations = mockOperations

      expect(store.totalOperationTime).toBe(13) // 5 + 8
    })
  })

  // ==========================================================================
  // ADD OPERATION
  // ==========================================================================

  describe('Add Operation', () => {
    it('should add operation successfully', async () => {
      const store = useOperationsStore()
      const newOp = createMockOperation({
        id: 10,
        work_center_id: null,
        name: 'OP10',
        type: 'generic',
        icon: '🔧',
        setup_time_min: 0,
        operation_time_min: 0
      })
      ;(operationsApi.create as Mock).mockResolvedValue(newOp)

      const result = await store.addOperation(100)

      expect(operationsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          part_id: 100,
          seq: 10,
          name: 'OP10',
          type: 'generic'
        })
      )
      expect(result).toEqual(newOp)
      expect(store.operations).toHaveLength(1)
      expect(store.operations[0]).toEqual(newOp)
      expect(store.expandedOps[10]).toBe(true)
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should calculate next sequence from existing operations', async () => {
      const store = useOperationsStore()
      store.operations = [
        createMockOperation({ id: 1, seq: 10 }),
        createMockOperation({ id: 2, seq: 20 })
      ]
      ;(operationsApi.create as Mock).mockResolvedValue(
        createMockOperation({ id: 3, seq: 30, name: 'OP30', type: 'generic', icon: '🔧' })
      )

      await store.addOperation(100)

      expect(operationsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({ seq: 30 })
      )
    })

    it('should handle add error', async () => {
      const store = useOperationsStore()
      ;(operationsApi.create as Mock).mockRejectedValue(new Error('Server error'))

      const result = await store.addOperation(100)

      expect(result).toBeNull()
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // UPDATE OPERATION
  // ==========================================================================

  describe('Update Operation', () => {
    const existingOp = createMockOperation({ setup_time_min: 10, operation_time_min: 5 })

    it('should update operation successfully', async () => {
      const store = useOperationsStore()
      store.operations = [existingOp]

      const updatedOp = { ...existingOp, setup_time_min: 20, version: 2 }
      ;(operationsApi.update as Mock).mockResolvedValue(updatedOp)

      await store.updateOperation(1, { setup_time_min: 20 })

      expect(operationsApi.update).toHaveBeenCalledWith(1, {
        setup_time_min: 20,
        version: 1
      })
      expect(store.operations[0]!.setup_time_min).toBe(20)
    })

    it('should handle version conflict (409)', async () => {
      const store = useOperationsStore()
      store.operations = [existingOp]
      ;(operationsApi.update as Mock).mockRejectedValue({ status: 409 })
      ;(operationsApi.listByPart as Mock).mockResolvedValue([existingOp])

      await store.updateOperation(1, { setup_time_min: 20 })

      expect(uiStore.toasts[0]!.type).toBe('warning')
      expect(uiStore.toasts[0]!.message).toContain('Konflikt')
    })

    it('should handle operation not found', async () => {
      const store = useOperationsStore()

      const result = await store.updateOperation(999, { setup_time_min: 20 })

      expect(result).toBeNull()
      expect(uiStore.toasts[0]!.message).toContain('nenalezena')
    })
  })

  // ==========================================================================
  // DELETE OPERATION
  // ==========================================================================

  describe('Delete Operation', () => {
    it('should delete operation successfully', async () => {
      const store = useOperationsStore()
      store.operations = [createMockOperation()]
      store.expandedOps = { 1: true }
      ;(operationsApi.delete as Mock).mockResolvedValue(undefined)

      const result = await store.deleteOperation(1)

      expect(operationsApi.delete).toHaveBeenCalledWith(1)
      expect(result).toBe(true)
      expect(store.operations).toHaveLength(0)
      expect(store.expandedOps[1]).toBeUndefined()
      expect(uiStore.toasts[0]!.type).toBe('success')
    })

    it('should handle delete error', async () => {
      const store = useOperationsStore()
      ;(operationsApi.delete as Mock).mockRejectedValue(new Error('Server error'))

      const result = await store.deleteOperation(1)

      expect(result).toBe(false)
      expect(uiStore.toasts[0]!.type).toBe('error')
    })
  })

  // ==========================================================================
  // UI HELPERS
  // ==========================================================================

  describe('UI Helpers', () => {
    it('should toggle expand state', () => {
      const store = useOperationsStore()

      store.toggleExpand(1)
      expect(store.isExpanded(1)).toBe(true)

      store.toggleExpand(1)
      expect(store.isExpanded(1)).toBe(false)
    })

    it('should get work center name', () => {
      const store = useOperationsStore()
      store.workCenters = [createMockWorkCenter()]

      expect(store.getWorkCenterName(1)).toBe('Soustruh 1')
      expect(store.getWorkCenterName(999)).toBe('-')
      expect(store.getWorkCenterName(null)).toBe('-')
    })

    it('should clear operations', () => {
      const store = useOperationsStore()
      store.operations = [createMockOperation()]
      store.expandedOps = { 1: true }
      store.error = 'Some error'

      store.clearOperations()

      expect(store.operations).toEqual([])
      expect(store.expandedOps).toEqual({})
      expect(store.error).toBeNull()
    })
  })
})
