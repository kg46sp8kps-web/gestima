/**
 * Batches Store - Manages batches and batch sets for pricing
 * MULTI-CONTEXT PATTERN: Supports per-linkingGroup contexts for multi-window workflow
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Batch, BatchCreate, BatchSet, BatchSetListItem, BatchSetWithBatches } from '@/types/batch'
import * as batchesApi from '@/api/batches'
import { useUiStore } from './ui'
import type { LinkingGroup } from './windows'

/**
 * Per-window context state
 */
interface BatchesContext {
  currentPartId: number | null
  batches: Batch[]
  batchSets: BatchSetListItem[]
  selectedSetId: number | null
  loading: boolean
  batchesLoading: boolean
  setsLoading: boolean
}

export const useBatchesStore = defineStore('batches', () => {
  const ui = useUiStore()

  // ==========================================================================
  // State - Multi-context pattern
  // ==========================================================================

  const contexts = ref<Map<string, BatchesContext>>(new Map())

  /**
   * Get or create context for a linking group
   */
  function getOrCreateContext(linkingGroup: LinkingGroup): BatchesContext {
    const key = linkingGroup || 'unlinked'
    if (!contexts.value.has(key)) {
      contexts.value.set(key, {
        currentPartId: null,
        batches: [],
        batchSets: [],
        selectedSetId: null,
        loading: false,
        batchesLoading: false,
        setsLoading: false
      })
    }
    return contexts.value.get(key)!
  }

  // ==========================================================================
  // Getters - Per-context
  // ==========================================================================

  /**
   * Get batches displayed based on selected set
   */
  function getDisplayedBatches(linkingGroup: LinkingGroup): Batch[] {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.selectedSetId === null) {
      // Show loose batches (not in any set)
      return ctx.batches.filter(b => !b.batch_set_id)
    } else {
      // Show batches from selected set
      return ctx.batches.filter(b => b.batch_set_id === ctx.selectedSetId)
    }
  }

  /**
   * Get loose batches (not in any set, not frozen)
   */
  function getLooseBatches(linkingGroup: LinkingGroup): Batch[] {
    const ctx = getOrCreateContext(linkingGroup)
    return ctx.batches.filter(b => !b.batch_set_id && !b.is_frozen)
  }

  /**
   * Get count of loose batches
   */
  function getLooseBatchCount(linkingGroup: LinkingGroup): number {
    return getLooseBatches(linkingGroup).length
  }

  /**
   * Get frozen batches
   */
  function getFrozenBatches(linkingGroup: LinkingGroup): Batch[] {
    const ctx = getOrCreateContext(linkingGroup)
    return ctx.batches.filter(b => b.is_frozen)
  }

  /**
   * Get selected batch set object
   */
  function getSelectedSet(linkingGroup: LinkingGroup): BatchSetListItem | null {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.selectedSetId === null) return null
    return ctx.batchSets.find(s => s.id === ctx.selectedSetId) || null
  }

  /**
   * Get total cost of displayed batches
   */
  function getDisplayedTotalCost(linkingGroup: LinkingGroup): number {
    return getDisplayedBatches(linkingGroup).reduce((sum, b) => sum + b.total_cost, 0)
  }

  /**
   * Get context state (for direct access in components)
   */
  function getContext(linkingGroup: LinkingGroup): BatchesContext {
    return getOrCreateContext(linkingGroup)
  }

  // ==========================================================================
  // Actions - Loading
  // ==========================================================================

  /**
   * Set current part and load all data
   */
  async function setPartContext(partId: number, linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.currentPartId === partId) return

    ctx.currentPartId = partId
    ctx.selectedSetId = null // Reset to loose batches
    await loadAll(linkingGroup)
  }

  /**
   * Load all data for current part
   */
  async function loadAll(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) return

    ctx.loading = true
    try {
      await Promise.all([
        loadBatches(linkingGroup),
        loadBatchSets(linkingGroup)
      ])
    } finally {
      ctx.loading = false
    }
  }

  /**
   * Load batches for current part
   */
  async function loadBatches(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) return

    ctx.batchesLoading = true
    try {
      const data = await batchesApi.getBatchesForPart(ctx.currentPartId)
      // Sort by quantity
      ctx.batches = data.sort((a, b) => a.quantity - b.quantity)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání dávek')
      throw error
    } finally {
      ctx.batchesLoading = false
    }
  }

  /**
   * Load batch sets for current part
   */
  async function loadBatchSets(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) return

    ctx.setsLoading = true
    try {
      ctx.batchSets = await batchesApi.getBatchSetsForPart(ctx.currentPartId)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání sad cen')
      throw error
    } finally {
      ctx.setsLoading = false
    }
  }

  // ==========================================================================
  // Actions - Batches CRUD
  // ==========================================================================

  /**
   * Create new batch
   */
  async function createBatch(quantity: number, linkingGroup: LinkingGroup): Promise<Batch> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) {
      throw new Error('No part selected')
    }

    const data: BatchCreate = {
      part_id: ctx.currentPartId,
      quantity
    }

    // If a set is selected, add to that set
    if (ctx.selectedSetId !== null) {
      const newBatch = await batchesApi.addBatchToSet(ctx.selectedSetId, data)
      ctx.batches.push(newBatch)
      ctx.batches.sort((a, b) => a.quantity - b.quantity)
      ui.showSuccess('Dávka přidána do sady')
      return newBatch
    }

    // Otherwise create loose batch
    const newBatch = await batchesApi.createBatch(data)
    ctx.batches.push(newBatch)
    ctx.batches.sort((a, b) => a.quantity - b.quantity)
    ui.showSuccess('Dávka vytvořena')
    return newBatch
  }

  /**
   * Delete batch
   */
  async function deleteBatch(batch: Batch, linkingGroup: LinkingGroup): Promise<void> {
    if (batch.is_frozen) {
      ui.showWarning('Nelze smazat zmrazenou dávku')
      return
    }

    const ctx = getOrCreateContext(linkingGroup)
    await batchesApi.deleteBatch(batch.batch_number)
    ctx.batches = ctx.batches.filter(b => b.id !== batch.id)
    ui.showSuccess('Dávka smazána')
  }

  /**
   * Freeze single batch
   */
  async function freezeBatch(batch: Batch, linkingGroup: LinkingGroup): Promise<Batch> {
    const ctx = getOrCreateContext(linkingGroup)
    const frozen = await batchesApi.freezeBatch(batch.batch_number)
    const index = ctx.batches.findIndex(b => b.id === batch.id)
    if (index !== -1) {
      ctx.batches[index] = frozen
    }
    ui.showSuccess('Dávka zmrazena')
    return frozen
  }

  /**
   * Clone batch
   */
  async function cloneBatch(batch: Batch, linkingGroup: LinkingGroup): Promise<Batch> {
    const ctx = getOrCreateContext(linkingGroup)
    const cloned = await batchesApi.cloneBatch(batch.batch_number)
    ctx.batches.push(cloned)
    ctx.batches.sort((a, b) => a.quantity - b.quantity)
    ui.showSuccess(`Dávka duplikována: ${cloned.batch_number}`)
    return cloned
  }

  /**
   * Recalculate all batches for current part
   */
  async function recalculateBatches(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) return

    await batchesApi.recalculateBatchesForPart(ctx.currentPartId)
    await loadBatches(linkingGroup)
    ui.showSuccess('Dávky přepočítány')
  }

  // ==========================================================================
  // Actions - Batch Sets
  // ==========================================================================

  /**
   * Select batch set (null = loose batches)
   */
  function selectSet(setId: number | null, linkingGroup: LinkingGroup): void {
    const ctx = getOrCreateContext(linkingGroup)
    ctx.selectedSetId = setId
  }

  /**
   * Create new batch set
   */
  async function createBatchSet(name: string | undefined, linkingGroup: LinkingGroup): Promise<BatchSet> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) {
      throw new Error('No part selected')
    }

    const newSet = await batchesApi.createBatchSet({
      part_id: ctx.currentPartId,
      name
    })
    await loadBatchSets(linkingGroup)
    ctx.selectedSetId = newSet.id
    ui.showSuccess('Sada cen vytvořena')
    return newSet
  }

  /**
   * Delete batch set
   */
  async function deleteBatchSet(setId: number, linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    await batchesApi.deleteBatchSet(setId)
    ctx.batchSets = ctx.batchSets.filter(s => s.id !== setId)
    if (ctx.selectedSetId === setId) {
      ctx.selectedSetId = null
    }
    await loadBatches(linkingGroup) // Reload batches as they may have been deleted
    ui.showSuccess('Sada smazána')
  }

  /**
   * Freeze selected batch set
   */
  async function freezeSelectedSet(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.selectedSetId === null) {
      ui.showWarning('Není vybrána žádná sada')
      return
    }

    const set = getSelectedSet(linkingGroup)
    if (set?.status === 'frozen') {
      ui.showInfo('Sada je již zmrazena')
      return
    }

    await batchesApi.freezeBatchSet(ctx.selectedSetId)
    await loadAll(linkingGroup)
    ui.showSuccess('Sada zmrazena')
  }

  /**
   * Freeze loose batches as a new set
   */
  async function freezeLooseBatchesAsSet(linkingGroup: LinkingGroup): Promise<BatchSetWithBatches | null> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartId) return null

    const looseBatches = getLooseBatches(linkingGroup)
    if (looseBatches.length === 0) {
      ui.showInfo('Žádné volné dávky k zmrazení')
      return null
    }

    const newSet = await batchesApi.freezeLooseBatchesAsSet(ctx.currentPartId)
    await loadAll(linkingGroup)
    ctx.selectedSetId = newSet.id
    ui.showSuccess(`Vytvořena zmrazená sada "${newSet.name}"`)
    return newSet
  }

  /**
   * Clone batch set
   */
  async function cloneBatchSet(setId: number, linkingGroup: LinkingGroup): Promise<BatchSet> {
    const ctx = getOrCreateContext(linkingGroup)
    const cloned = await batchesApi.cloneBatchSet(setId)
    await loadAll(linkingGroup)
    ctx.selectedSetId = cloned.id
    ui.showSuccess(`Sada duplikována: ${cloned.name}`)
    return cloned
  }

  /**
   * Recalculate selected batch set
   */
  async function recalculateSelectedSet(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.selectedSetId === null) {
      ui.showWarning('Není vybrána žádná sada')
      return
    }

    await batchesApi.recalculateBatchSet(ctx.selectedSetId)
    await loadBatches(linkingGroup)
    ui.showSuccess('Sada přepočítána')
  }

  // ==========================================================================
  // Reset
  // ==========================================================================

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

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // Getters (per-context)
    getContext,
    getDisplayedBatches,
    getLooseBatches,
    getLooseBatchCount,
    getFrozenBatches,
    getSelectedSet,
    getDisplayedTotalCost,

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
    reset,
    resetAll
  }
})
