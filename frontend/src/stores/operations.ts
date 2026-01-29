/**
 * GESTIMA - Operations Pinia Store
 *
 * Manages operations for the current part in workspace context.
 * Listens for partId changes from workspace store.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { operationsApi, workCentersApi } from '@/api/operations'
import { useWorkspaceStore } from './workspace'
import { useUiStore } from './ui'
import type {
  Operation,
  OperationCreate,
  OperationUpdate,
  WorkCenter,
  CuttingMode,
  OperationType
} from '@/types'
import { OPERATION_TYPE_MAP } from '@/types/operation'

export const useOperationsStore = defineStore('operations', () => {
  // ═══════════════════════════════════════════════════════════════════════════
  // State
  // ═══════════════════════════════════════════════════════════════════════════

  const operations = ref<Operation[]>([])
  const workCenters = ref<WorkCenter[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const expandedOps = ref<Record<number, boolean>>({})

  // ═══════════════════════════════════════════════════════════════════════════
  // Getters
  // ═══════════════════════════════════════════════════════════════════════════

  /** Operations sorted by sequence */
  const sortedOperations = computed(() =>
    [...operations.value].sort((a, b) => a.seq - b.seq)
  )

  /** Internal operations (not coop) */
  const internalOperations = computed(() =>
    sortedOperations.value.filter(op => !op.is_coop)
  )

  /** Cooperation operations */
  const coopOperations = computed(() =>
    sortedOperations.value.filter(op => op.is_coop)
  )

  /** Total setup time in minutes */
  const totalSetupTime = computed(() =>
    operations.value.reduce((sum, op) => sum + (op.setup_time_min || 0), 0)
  )

  /** Total operation time in minutes */
  const totalOperationTime = computed(() =>
    operations.value.reduce((sum, op) => sum + (op.operation_time_min || 0), 0)
  )

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
  async function loadOperations(partId: number): Promise<void> {
    if (!partId) {
      operations.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      operations.value = await operationsApi.listByPart(partId)
      console.debug(`[operations] Loaded ${operations.value.length} operations for part ${partId}`)
    } catch (err) {
      console.error('[operations] Load error:', err)
      error.value = 'Chyba při načítání operací'
      operations.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Add new operation
   */
  async function addOperation(partId: number): Promise<Operation | null> {
    const ui = useUiStore()

    try {
      // Calculate next sequence number
      const nextSeq = operations.value.length > 0
        ? Math.max(...operations.value.map(o => o.seq)) + 10
        : 10

      const payload: OperationCreate = {
        part_id: partId,
        seq: nextSeq,
        name: `OP${nextSeq}`,
        type: 'generic',
        icon: '🔧',
        setup_time_min: 0,
        operation_time_min: 0,
        is_coop: false,
        coop_price: 0
      }

      const newOp = await operationsApi.create(payload)
      operations.value.push(newOp)

      // Expand new operation
      expandedOps.value[newOp.id] = true

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
  async function updateOperation(operationId: number, updates: Partial<OperationUpdate>): Promise<Operation | null> {
    const ui = useUiStore()

    // Find current operation
    const current = operations.value.find(o => o.id === operationId)
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
      const idx = operations.value.findIndex(o => o.id === operationId)
      if (idx !== -1) {
        operations.value[idx] = updated
      }

      return updated

    } catch (err: any) {
      console.error('[operations] Update error:', err)

      // Handle version conflict
      if (err?.status === 409) {
        ui.showToast('Konflikt verze - obnovuji data', 'warning')
        const workspace = useWorkspaceStore()
        if (workspace.context.partId) {
          await loadOperations(workspace.context.partId)
        }
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
  async function deleteOperation(operationId: number): Promise<boolean> {
    const ui = useUiStore()

    try {
      await operationsApi.delete(operationId)

      // Remove from local state
      operations.value = operations.value.filter(o => o.id !== operationId)
      delete expandedOps.value[operationId]

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
  async function changeMode(operationId: number, mode: CuttingMode): Promise<Operation | null> {
    const ui = useUiStore()

    // Find current operation
    const current = operations.value.find(o => o.id === operationId)
    if (!current) return null

    try {
      const updated = await operationsApi.changeMode(operationId, {
        cutting_mode: mode,
        version: current.version
      })

      // Update local state
      const idx = operations.value.findIndex(o => o.id === operationId)
      if (idx !== -1) {
        operations.value[idx] = updated
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
  async function toggleCoopMode(operationId: number): Promise<Operation | null> {
    const current = operations.value.find(o => o.id === operationId)
    if (!current) return null

    return updateOperation(operationId, {
      is_coop: !current.is_coop
    })
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UI Helpers
  // ═══════════════════════════════════════════════════════════════════════════

  function toggleExpand(operationId: number): void {
    expandedOps.value[operationId] = !expandedOps.value[operationId]
  }

  function isExpanded(operationId: number): boolean {
    return !!expandedOps.value[operationId]
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
    const defaultType = { type: 'generic' as OperationType, icon: '🔧', label: 'Operace' }

    if (!workCenterId) {
      return defaultType
    }
    const wc = workCenters.value.find(w => w.id === workCenterId)
    if (!wc) {
      return defaultType
    }
    return OPERATION_TYPE_MAP[wc.type] ?? defaultType
  }

  /**
   * Clear all state
   */
  function clearOperations(): void {
    operations.value = []
    expandedOps.value = {}
    error.value = null
  }

  return {
    // State
    operations,
    workCenters,
    loading,
    saving,
    error,
    expandedOps,

    // Getters
    sortedOperations,
    internalOperations,
    coopOperations,
    totalSetupTime,
    totalOperationTime,
    activeWorkCenters,

    // Actions
    loadWorkCenters,
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
    clearOperations
  }
})
