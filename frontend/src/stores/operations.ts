/**
 * GESTIMA - Operations Pinia Store
 * MULTI-CONTEXT PATTERN: Supports per-linkingGroup contexts for multi-window workflow
 *
 * Manages operations for parts.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { operationsApi, workCentersApi } from '@/api/operations'
import { useUiStore } from './ui'
import { useBatchesStore } from './batches'
import type {
  Operation,
  OperationCreate,
  OperationUpdate,
  WorkCenter,
  WorkCenterCreate,
  WorkCenterUpdate,
  CuttingMode,
  OperationType
} from '@/types'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import type { LinkingGroup } from './windows'

/**
 * Per-window context state
 */
interface OperationsContext {
  currentPartId: number | null
  operations: Operation[]
  loading: boolean
  error: string | null
  expandedOps: Record<number, boolean>
}

export const useOperationsStore = defineStore('operations', () => {
  // ═══════════════════════════════════════════════════════════════════════════
  // State - Multi-context pattern
  // ═══════════════════════════════════════════════════════════════════════════

  const contexts = ref<Map<string, OperationsContext>>(new Map())

  /**
   * Get or create context for a linking group
   */
  function getOrCreateContext(linkingGroup: LinkingGroup): OperationsContext {
    const key = linkingGroup || 'unlinked'
    if (!contexts.value.has(key)) {
      contexts.value.set(key, {
        currentPartId: null,
        operations: [],
        loading: false,
        error: null,
        expandedOps: {}
      })
    }
    return contexts.value.get(key)!
  }

  /**
   * Get context (for direct access in components)
   */
  function getContext(linkingGroup: LinkingGroup): OperationsContext {
    return getOrCreateContext(linkingGroup)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // State - Global (shared across all windows)
  // ═══════════════════════════════════════════════════════════════════════════

  const workCenters = ref<WorkCenter[]>([])
  const saving = ref(false)

  // ═══════════════════════════════════════════════════════════════════════════
  // Getters - Per-context
  // ═══════════════════════════════════════════════════════════════════════════

  /** Operations sorted by sequence */
  function getSortedOperations(linkingGroup: LinkingGroup): Operation[] {
    const ctx = getOrCreateContext(linkingGroup)
    return [...ctx.operations].sort((a, b) => a.seq - b.seq)
  }

  /** Internal operations (not coop) */
  function getInternalOperations(linkingGroup: LinkingGroup): Operation[] {
    return getSortedOperations(linkingGroup).filter(op => !op.is_coop)
  }

  /** Cooperation operations */
  function getCoopOperations(linkingGroup: LinkingGroup): Operation[] {
    return getSortedOperations(linkingGroup).filter(op => op.is_coop)
  }

  /** Total setup time in minutes */
  function getTotalSetupTime(linkingGroup: LinkingGroup): number {
    const ctx = getOrCreateContext(linkingGroup)
    return ctx.operations.reduce((sum, op) => sum + (op.setup_time_min || 0), 0)
  }

  /** Total operation time in minutes */
  function getTotalOperationTime(linkingGroup: LinkingGroup): number {
    const ctx = getOrCreateContext(linkingGroup)
    return ctx.operations.reduce((sum, op) => sum + (op.operation_time_min || 0), 0)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Getters - Global
  // ═══════════════════════════════════════════════════════════════════════════

  /** Active work centers only */
  const activeWorkCenters = computed(() =>
    workCenters.value.filter(wc => wc.is_active)
  )

  // ═══════════════════════════════════════════════════════════════════════════
  // Actions
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Load work centers (for dropdown)
   */
  async function loadWorkCenters(): Promise<void> {
    try {
      workCenters.value = await workCentersApi.list()
    } catch (err) {
      console.error('[operations] Failed to load work centers:', err)
    }
  }

  /**
   * Load operations for a part
   */
  async function loadOperations(partId: number, linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)

    if (!partId) {
      ctx.operations = []
      ctx.currentPartId = null
      return
    }

    ctx.currentPartId = partId
    ctx.loading = true
    ctx.error = null

    try {
      ctx.operations = await operationsApi.listByPart(partId)
      console.debug(`[operations] Loaded ${ctx.operations.length} operations for part ${partId}`)
    } catch (err) {
      console.error('[operations] Load error:', err)
      ctx.error = 'Chyba při načítání operací'
      ctx.operations = []
    } finally {
      ctx.loading = false
    }
  }

  /**
   * Add new operation
   */
  async function addOperation(partId: number, linkingGroup: LinkingGroup): Promise<Operation | null> {
    const ui = useUiStore()
    const ctx = getOrCreateContext(linkingGroup)

    try {
      // Calculate next sequence number
      const nextSeq = ctx.operations.length > 0
        ? Math.max(...ctx.operations.map(o => o.seq)) + 10
        : 10

      const payload: OperationCreate = {
        part_id: partId,
        seq: nextSeq,
        name: `OP${nextSeq}`,
        type: 'generic',
        icon: 'wrench',
        setup_time_min: 0,
        operation_time_min: 0,
        is_coop: false,
        coop_price: 0
      }

      const newOp = await operationsApi.create(payload)
      ctx.operations.push(newOp)

      // Expand new operation
      ctx.expandedOps[newOp.id] = true

      // Trigger batch recalculation for live pricing updates
      try {
        const batchesStore = useBatchesStore()
        await batchesStore.recalculateBatches(linkingGroup, partId, true)
      } catch (e) {
        // Ignore - batches context may not be initialized
      }

      ui.showToast('Operace přidána', 'success')
      return newOp

    } catch (err) {
      console.error('[operations] Add error:', err)
      ui.showToast('Chyba při přidávání operace', 'error')
      return null
    }
  }

  /**
   * Update operation (with optimistic locking)
   */
  async function updateOperation(operationId: number, updates: Partial<OperationUpdate>, linkingGroup: LinkingGroup): Promise<Operation | null> {
    const ui = useUiStore()
    const ctx = getOrCreateContext(linkingGroup)

    // Find current operation
    const current = ctx.operations.find(o => o.id === operationId)
    if (!current) {
      ui.showToast('Operace nenalezena', 'error')
      return null
    }

    saving.value = true

    try {
      const payload: OperationUpdate = {
        ...updates,
        version: current.version
      }

      const updated = await operationsApi.update(operationId, payload)

      // Update local state
      const idx = ctx.operations.findIndex(o => o.id === operationId)
      if (idx !== -1) {
        ctx.operations[idx] = updated
      }

      // Trigger batch recalculation for live pricing updates
      if (ctx.currentPartId) {
        try {
          const batchesStore = useBatchesStore()
          await batchesStore.recalculateBatches(linkingGroup, ctx.currentPartId, true)
        } catch (e) {
          // Ignore - batches context may not be initialized
        }
      }

      return updated

    } catch (err: any) {
      console.error('[operations] Update error:', err)

      // Handle version conflict - auto-reload data
      if (err?.status === 409) {
        // Auto-reload operations to get fresh data
        if (ctx.currentPartId) {
          await loadOperations(ctx.currentPartId, linkingGroup)
        }
        ui.showToast('Data byla změněna. Načtena aktuální verze - zkuste změnu znovu.', 'warning')
      } else {
        ui.showToast('Chyba při ukládání', 'error')
      }
      return null
    } finally {
      saving.value = false
    }
  }

  /**
   * Delete operation
   */
  async function deleteOperation(operationId: number, linkingGroup: LinkingGroup): Promise<boolean> {
    const ui = useUiStore()
    const ctx = getOrCreateContext(linkingGroup)

    try {
      await operationsApi.delete(operationId)

      // Remove from local state
      ctx.operations = ctx.operations.filter(o => o.id !== operationId)
      delete ctx.expandedOps[operationId]

      // Trigger batch recalculation for live pricing updates
      if (ctx.currentPartId) {
        try {
          const batchesStore = useBatchesStore()
          await batchesStore.recalculateBatches(linkingGroup, ctx.currentPartId, true)
        } catch (e) {
          // Ignore - batches context may not be initialized
        }
      }

      ui.showToast('Operace smazána', 'success')
      return true

    } catch (err) {
      console.error('[operations] Delete error:', err)
      ui.showToast('Chyba při mazání operace', 'error')
      return false
    }
  }

  /**
   * Change cutting mode
   */
  async function changeMode(operationId: number, mode: CuttingMode, linkingGroup: LinkingGroup): Promise<Operation | null> {
    const ui = useUiStore()
    const ctx = getOrCreateContext(linkingGroup)

    // Find current operation
    const current = ctx.operations.find(o => o.id === operationId)
    if (!current) return null

    try {
      const updated = await operationsApi.changeMode(operationId, {
        cutting_mode: mode,
        version: current.version
      })

      // Update local state
      const idx = ctx.operations.findIndex(o => o.id === operationId)
      if (idx !== -1) {
        ctx.operations[idx] = updated
      }

      // Trigger batch recalculation for live pricing updates
      if (ctx.currentPartId) {
        try {
          const batchesStore = useBatchesStore()
          await batchesStore.recalculateBatches(linkingGroup, ctx.currentPartId, true)
        } catch (e) {
          // Ignore - batches context may not be initialized
        }
      }

      ui.showToast(`Režim nastaven na ${mode.toUpperCase()}`, 'success')
      return updated

    } catch (err) {
      console.error('[operations] Change mode error:', err)
      ui.showToast('Chyba při změně režimu', 'error')
      return null
    }
  }

  /**
   * Toggle cooperation mode
   */
  async function toggleCoopMode(operationId: number, linkingGroup: LinkingGroup): Promise<Operation | null> {
    const ctx = getOrCreateContext(linkingGroup)
    const current = ctx.operations.find(o => o.id === operationId)
    if (!current) return null

    return updateOperation(operationId, {
      is_coop: !current.is_coop
    }, linkingGroup)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UI Helpers
  // ═══════════════════════════════════════════════════════════════════════════

  function toggleExpand(operationId: number, linkingGroup: LinkingGroup): void {
    const ctx = getOrCreateContext(linkingGroup)
    ctx.expandedOps[operationId] = !ctx.expandedOps[operationId]
  }

  function isExpanded(operationId: number, linkingGroup: LinkingGroup): boolean {
    const ctx = getOrCreateContext(linkingGroup)
    return !!ctx.expandedOps[operationId]
  }

  function getWorkCenterName(workCenterId: number | null): string {
    if (!workCenterId) return '-'
    const wc = workCenters.value.find(w => w.id === workCenterId)
    return wc ? wc.name : '-'
  }

  /**
   * Get operation type info from work center
   */
  function getOperationTypeFromWorkCenter(workCenterId: number | null): { type: OperationType; icon: string; label: string } {
    const defaultType = { type: 'generic' as OperationType, icon: 'wrench', label: 'Operace' }

    if (!workCenterId) {
      return defaultType
    }
    const wc = workCenters.value.find(w => w.id === workCenterId)
    if (!wc) {
      return defaultType
    }
    return OPERATION_TYPE_MAP[wc.work_center_type] ?? defaultType
  }

  /**
   * Create new work center
   */
  async function createWorkCenter(data: WorkCenterCreate): Promise<WorkCenter> {
    saving.value = true
    try {
      const created = await workCentersApi.create(data)
      workCenters.value.push(created)
      return created
    } finally {
      saving.value = false
    }
  }

  /**
   * Update work center by number
   */
  async function updateWorkCenter(workCenterNumber: string, data: WorkCenterUpdate): Promise<WorkCenter> {
    saving.value = true
    try {
      const updated = await workCentersApi.update(workCenterNumber, data)
      const index = workCenters.value.findIndex(wc => wc.work_center_number === workCenterNumber)
      if (index !== -1) {
        workCenters.value[index] = updated
      }
      return updated
    } finally {
      saving.value = false
    }
  }

  /**
   * Delete work center by number
   */
  async function deleteWorkCenter(workCenterNumber: string): Promise<void> {
    await workCentersApi.delete(workCenterNumber)
    workCenters.value = workCenters.value.filter(wc => wc.work_center_number !== workCenterNumber)
  }

  /**
   * Clear context state
   */
  function clearOperations(linkingGroup: LinkingGroup): void {
    const ctx = getOrCreateContext(linkingGroup)
    ctx.operations = []
    ctx.expandedOps = {}
    ctx.error = null
  }

  /**
   * Reset context for a linking group
   */
  function reset(linkingGroup: LinkingGroup): void {
    const key = linkingGroup || 'unlinked'
    contexts.value.delete(key)
  }

  /**
   * Reset all contexts
   */
  function resetAll(): void {
    contexts.value.clear()
  }

  return {
    // State - Global
    workCenters,
    saving,

    // Getters - Per-context
    getContext,
    getSortedOperations,
    getInternalOperations,
    getCoopOperations,
    getTotalSetupTime,
    getTotalOperationTime,

    // Getters - Global
    activeWorkCenters,

    // Actions - Work Centers
    loadWorkCenters,
    createWorkCenter,
    updateWorkCenter,
    deleteWorkCenter,

    // Actions - Operations
    loadOperations,
    addOperation,
    updateOperation,
    deleteOperation,
    changeMode,
    toggleCoopMode,

    // UI Helpers
    toggleExpand,
    isExpanded,
    getWorkCenterName,
    getOperationTypeFromWorkCenter,

    // Reset
    clearOperations,
    reset,
    resetAll
  }
})
