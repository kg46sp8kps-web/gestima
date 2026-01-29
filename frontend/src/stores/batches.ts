/**
 * Batches Store - Manages batches and batch sets for pricing
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Batch, BatchCreate, BatchSet, BatchSetListItem, BatchSetWithBatches } from '@/types/batch'
import * as batchesApi from '@/api/batches'
import { useUiStore } from './ui'

export const useBatchesStore = defineStore('batches', () => {
  const ui = useUiStore()

  // ==========================================================================
  // State
  // ==========================================================================

  // Current part context
  const currentPartId = ref<number | null>(null)

  // Batches for current part
  const batches = ref<Batch[]>([])

  // Batch sets for current part
  const batchSets = ref<BatchSetListItem[]>([])

  // Selected batch set (null = loose batches)
  const selectedSetId = ref<number | null>(null)

  // Loading states
  const loading = ref(false)
  const batchesLoading = ref(false)
  const setsLoading = ref(false)

  // ==========================================================================
  // Computed
  // ==========================================================================

  /**
   * Batches displayed based on selected set
   */
  const displayedBatches = computed(() => {
    if (selectedSetId.value === null) {
      // Show loose batches (not in any set)
      return batches.value.filter(b => !b.batch_set_id)
    } else {
      // Show batches from selected set
      return batches.value.filter(b => b.batch_set_id === selectedSetId.value)
    }
  })

  /**
   * Loose batches (not in any set, not frozen)
   */
  const looseBatches = computed(() =>
    batches.value.filter(b => !b.batch_set_id && !b.is_frozen)
  )

  /**
   * Count of loose batches
   */
  const looseBatchCount = computed(() => looseBatches.value.length)

  /**
   * Frozen batches
   */
  const frozenBatches = computed(() =>
    batches.value.filter(b => b.is_frozen)
  )

  /**
   * Selected batch set object
   */
  const selectedSet = computed(() =>
    selectedSetId.value !== null
      ? batchSets.value.find(s => s.id === selectedSetId.value) || null
      : null
  )

  /**
   * Total cost of displayed batches
   */
  const displayedTotalCost = computed(() =>
    displayedBatches.value.reduce((sum, b) => sum + b.total_cost, 0)
  )

  // ==========================================================================
  // Actions - Loading
  // ==========================================================================

  /**
   * Set current part and load all data
   */
  async function setPartContext(partId: number): Promise<void> {
    if (currentPartId.value === partId) return

    currentPartId.value = partId
    selectedSetId.value = null // Reset to loose batches
    await loadAll()
  }

  /**
   * Load all data for current part
   */
  async function loadAll(): Promise<void> {
    if (!currentPartId.value) return

    loading.value = true
    try {
      await Promise.all([
        loadBatches(),
        loadBatchSets()
      ])
    } finally {
      loading.value = false
    }
  }

  /**
   * Load batches for current part
   */
  async function loadBatches(): Promise<void> {
    if (!currentPartId.value) return

    batchesLoading.value = true
    try {
      const data = await batchesApi.getBatchesForPart(currentPartId.value)
      // Sort by quantity
      batches.value = data.sort((a, b) => a.quantity - b.quantity)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání dávek')
      throw error
    } finally {
      batchesLoading.value = false
    }
  }

  /**
   * Load batch sets for current part
   */
  async function loadBatchSets(): Promise<void> {
    if (!currentPartId.value) return

    setsLoading.value = true
    try {
      batchSets.value = await batchesApi.getBatchSetsForPart(currentPartId.value)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání sad cen')
      throw error
    } finally {
      setsLoading.value = false
    }
  }

  // ==========================================================================
  // Actions - Batches CRUD
  // ==========================================================================

  /**
   * Create new batch
   */
  async function createBatch(quantity: number): Promise<Batch> {
    if (!currentPartId.value) {
      throw new Error('No part selected')
    }

    const data: BatchCreate = {
      part_id: currentPartId.value,
      quantity
    }

    // If a set is selected, add to that set
    if (selectedSetId.value !== null) {
      const newBatch = await batchesApi.addBatchToSet(selectedSetId.value, data)
      batches.value.push(newBatch)
      batches.value.sort((a, b) => a.quantity - b.quantity)
      ui.showSuccess('Dávka přidána do sady')
      return newBatch
    }

    // Otherwise create loose batch
    const newBatch = await batchesApi.createBatch(data)
    batches.value.push(newBatch)
    batches.value.sort((a, b) => a.quantity - b.quantity)
    ui.showSuccess('Dávka vytvořena')
    return newBatch
  }

  /**
   * Delete batch
   */
  async function deleteBatch(batch: Batch): Promise<void> {
    if (batch.is_frozen) {
      ui.showWarning('Nelze smazat zmrazenou dávku')
      return
    }

    await batchesApi.deleteBatch(batch.batch_number)
    batches.value = batches.value.filter(b => b.id !== batch.id)
    ui.showSuccess('Dávka smazána')
  }

  /**
   * Freeze single batch
   */
  async function freezeBatch(batch: Batch): Promise<Batch> {
    const frozen = await batchesApi.freezeBatch(batch.batch_number)
    const index = batches.value.findIndex(b => b.id === batch.id)
    if (index !== -1) {
      batches.value[index] = frozen
    }
    ui.showSuccess('Dávka zmrazena')
    return frozen
  }

  /**
   * Clone batch
   */
  async function cloneBatch(batch: Batch): Promise<Batch> {
    const cloned = await batchesApi.cloneBatch(batch.batch_number)
    batches.value.push(cloned)
    batches.value.sort((a, b) => a.quantity - b.quantity)
    ui.showSuccess(`Dávka duplikována: ${cloned.batch_number}`)
    return cloned
  }

  /**
   * Recalculate all batches for current part
   */
  async function recalculateBatches(): Promise<void> {
    if (!currentPartId.value) return

    await batchesApi.recalculateBatchesForPart(currentPartId.value)
    await loadBatches()
    ui.showSuccess('Dávky přepočítány')
  }

  // ==========================================================================
  // Actions - Batch Sets
  // ==========================================================================

  /**
   * Select batch set (null = loose batches)
   */
  function selectSet(setId: number | null): void {
    selectedSetId.value = setId
  }

  /**
   * Create new batch set
   */
  async function createBatchSet(name?: string): Promise<BatchSet> {
    if (!currentPartId.value) {
      throw new Error('No part selected')
    }

    const newSet = await batchesApi.createBatchSet({
      part_id: currentPartId.value,
      name
    })
    await loadBatchSets()
    selectedSetId.value = newSet.id
    ui.showSuccess('Sada cen vytvořena')
    return newSet
  }

  /**
   * Delete batch set
   */
  async function deleteBatchSet(setId: number): Promise<void> {
    await batchesApi.deleteBatchSet(setId)
    batchSets.value = batchSets.value.filter(s => s.id !== setId)
    if (selectedSetId.value === setId) {
      selectedSetId.value = null
    }
    await loadBatches() // Reload batches as they may have been deleted
    ui.showSuccess('Sada smazána')
  }

  /**
   * Freeze selected batch set
   */
  async function freezeSelectedSet(): Promise<void> {
    if (selectedSetId.value === null) {
      ui.showWarning('Není vybrána žádná sada')
      return
    }

    const set = selectedSet.value
    if (set?.status === 'frozen') {
      ui.showInfo('Sada je již zmrazena')
      return
    }

    await batchesApi.freezeBatchSet(selectedSetId.value)
    await loadAll()
    ui.showSuccess('Sada zmrazena')
  }

  /**
   * Freeze loose batches as a new set
   */
  async function freezeLooseBatchesAsSet(): Promise<BatchSetWithBatches | null> {
    if (!currentPartId.value) return null

    if (looseBatches.value.length === 0) {
      ui.showInfo('Žádné volné dávky k zmrazení')
      return null
    }

    const newSet = await batchesApi.freezeLooseBatchesAsSet(currentPartId.value)
    await loadAll()
    selectedSetId.value = newSet.id
    ui.showSuccess(`Vytvořena zmrazená sada "${newSet.name}"`)
    return newSet
  }

  /**
   * Clone batch set
   */
  async function cloneBatchSet(setId: number): Promise<BatchSet> {
    const cloned = await batchesApi.cloneBatchSet(setId)
    await loadAll()
    selectedSetId.value = cloned.id
    ui.showSuccess(`Sada duplikována: ${cloned.name}`)
    return cloned
  }

  /**
   * Recalculate selected batch set
   */
  async function recalculateSelectedSet(): Promise<void> {
    if (selectedSetId.value === null) {
      ui.showWarning('Není vybrána žádná sada')
      return
    }

    await batchesApi.recalculateBatchSet(selectedSetId.value)
    await loadBatches()
    ui.showSuccess('Sada přepočítána')
  }

  // ==========================================================================
  // Reset
  // ==========================================================================

  function reset(): void {
    currentPartId.value = null
    batches.value = []
    batchSets.value = []
    selectedSetId.value = null
    loading.value = false
    batchesLoading.value = false
    setsLoading.value = false
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    currentPartId,
    batches,
    batchSets,
    selectedSetId,
    loading,
    batchesLoading,
    setsLoading,

    // Computed
    displayedBatches,
    looseBatches,
    looseBatchCount,
    frozenBatches,
    selectedSet,
    displayedTotalCost,

    // Actions - Loading
    setPartContext,
    loadAll,
    loadBatches,
    loadBatchSets,

    // Actions - Batches
    createBatch,
    deleteBatch,
    freezeBatch,
    cloneBatch,
    recalculateBatches,

    // Actions - Sets
    selectSet,
    createBatchSet,
    deleteBatchSet,
    freezeSelectedSet,
    freezeLooseBatchesAsSet,
    cloneBatchSet,
    recalculateSelectedSet,

    // Reset
    reset
  }
})
