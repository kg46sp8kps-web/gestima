/**
 * Materials Store - Material data for PartMaterialModule
 * MULTI-CONTEXT PATTERN: Supports per-linkingGroup contexts for multi-window workflow
 *
 * ADR-024: MaterialInput refactor (v1.8.0)
 *
 * Manages:
 * - Price categories (for dropdown + filtering) - GLOBAL
 * - Material groups (for density calculations) - GLOBAL
 * - Material parser (AI-powered quick input) - GLOBAL
 * - MaterialInput CRUD (Part → N MaterialInputs) - PER-CONTEXT
 * - M:N linking MaterialInput ↔ Operation - PER-CONTEXT
 * - Stock cost calculation - PER-CONTEXT
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  MaterialPriceCategory,
  MaterialGroup,
  StockCost,
  MaterialParseResult,
  MaterialInput,
  MaterialInputWithOperations,
  MaterialInputCreate,
  MaterialInputUpdate,
  StockShape
} from '@/types/material'
import * as materialsApi from '@/api/materials'
import * as materialInputsApi from '@/api/materialInputs'
import { useUiStore } from './ui'
import { useBatchesStore } from './batches'
import type { LinkingGroup } from './windows'

/**
 * Per-window context state
 */
interface MaterialsContext {
  currentPartId: number | null
  currentPartNumber: string | null
  materialInputs: MaterialInputWithOperations[]
  stockCost: StockCost | null
  loadingInputs: boolean
  initialLoadingInputs: boolean  // true only on first load (no data yet) — prevents flash on part switch
  loadingStockCost: boolean
}

export const useMaterialsStore = defineStore('materials', () => {
  const ui = useUiStore()

  // ==========================================================================
  // State - Multi-context pattern
  // ==========================================================================

  const contexts = ref<Map<string, MaterialsContext>>(new Map())

  /**
   * Get or create context for a linking group
   */
  function getOrCreateContext(linkingGroup: LinkingGroup): MaterialsContext {
    const key = linkingGroup || 'unlinked'
    if (!contexts.value.has(key)) {
      contexts.value.set(key, {
        currentPartId: null,
        currentPartNumber: null,
        materialInputs: [],
        stockCost: null,
        loadingInputs: false,
        initialLoadingInputs: false,
        loadingStockCost: false
      })
    }
    return contexts.value.get(key)!
  }

  /**
   * Get context (for direct access in components)
   */
  function getContext(linkingGroup: LinkingGroup): MaterialsContext {
    return getOrCreateContext(linkingGroup)
  }

  // ==========================================================================
  // State - Global (shared across all windows)
  // ==========================================================================

  // Reference data (loaded once, shared across all windows)
  const priceCategories = ref<MaterialPriceCategory[]>([])
  const materialGroups = ref<MaterialGroup[]>([])
  const referenceDataLoaded = ref(false)

  // Material Items — same pattern as parts store (200 first, batch 50 on scroll)
  const MATERIAL_PAGE_SIZE = 200
  const MATERIAL_BATCH_SIZE = 50
  const materialItems = ref<import('@/types/material').MaterialItem[]>([])
  const materialItemsTotal = ref(0)
  const materialItemsLoaded = ref(false)
  const loadingMaterialItems = ref(false)
  const loadingMoreMaterialItems = ref(false)

  // Parser state (shared across all windows)
  const parseResult = ref<MaterialParseResult | null>(null)
  const parsingMaterial = ref(false)

  // Global loading states
  const loading = ref(false)
  const saving = ref(false)

  // ==========================================================================
  // Computed
  // ==========================================================================

  // Identical to parts store pattern
  const initialLoadingMaterialItems = computed(() => loadingMaterialItems.value && materialItems.value.length === 0)
  const hasMaterialItems = computed(() => materialItems.value.length > 0)
  const hasMoreMaterialItems = computed(() => materialItems.value.length < materialItemsTotal.value)

  /**
   * Price categories sorted by name
   */
  const sortedCategories = computed(() =>
    [...priceCategories.value].sort((a, b) => a.name.localeCompare(b.name))
  )

  /**
   * Get category by ID
   */
  const getCategoryById = computed(() => (id: number | null) => {
    if (!id) return null
    return priceCategories.value.find(c => c.id === id) || null
  })

  /**
   * Has valid parse result (confidence > 0.4)
   */
  const hasValidParseResult = computed(() =>
    parseResult.value !== null && parseResult.value.confidence >= 0.4
  )

  /**
   * Get filtered categories by stock shape
   * Based on Alpine.js filteredCategories logic from edit.html
   */
  const getFilteredCategories = computed(() => (stockShape: StockShape | null) => {
    if (!stockShape) {
      return priceCategories.value
    }

    // Mapping: shape → category code suffix (for proper price category selection)
    const shapeToSuffix: Record<StockShape, string[]> = {
      'round_bar': ['KRUHOVA', 'BRONZ'],       // OCEL-KRUHOVA, MOSAZ-BRONZ
      'square_bar': ['CTVEREC'],                // OCEL-KONS-CTVEREC, NEREZ-CTVEREC, HLINIK-CTVEREC
      'hexagonal_bar': ['KRUHOVA', 'SESTIH'],  // OCEL-KRUHOVA (contains hexagon in name)
      'flat_bar': ['PLOCHA'],                   // OCEL-PLOCHA, NEREZ-PLOCHA, HLINIK-PLOCHA
      'plate': ['DESKY'],                       // OCEL-DESKY, HLINIK-DESKY, PLASTY-DESKY
      'tube': ['TRUBKA'],                       // OCEL-TRUBKA
      'casting': [],                            // No filter (show all)
      'forging': []                             // No filter (show all)
    }

    const suffixes = shapeToSuffix[stockShape]
    if (!suffixes || suffixes.length === 0) {
      return priceCategories.value // Fallback: no filter defined
    }

    // Filter by code suffix
    const filtered = priceCategories.value.filter(category =>
      suffixes.some(suffix => category.code.includes(suffix))
    )

    // FALLBACK: If filter found nothing, show all categories
    if (filtered.length === 0) {
      console.warn(
        `WARNING: No categories found for shape ${stockShape} with suffixes ${suffixes.join(', ')} - showing all`
      )
      return priceCategories.value
    }

    return filtered
  })

  // ==========================================================================
  // Actions - Reference Data
  // ==========================================================================

  /**
   * Load reference data (price categories, material groups)
   */
  async function loadReferenceData(): Promise<void> {
    if (referenceDataLoaded.value) return

    loading.value = true
    try {
      const [categories, groups] = await Promise.all([
        materialsApi.getPriceCategories(),
        materialsApi.getMaterialGroups()
      ])

      priceCategories.value = categories
      materialGroups.value = groups
      referenceDataLoaded.value = true
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při načítání materiálů')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch first 200 material items — identical to fetchParts()
   */
  async function fetchMaterialItems(): Promise<void> {
    if (materialItemsLoaded.value) return

    loadingMaterialItems.value = true
    try {
      const response = await materialsApi.getMaterialItems({ skip: 0, limit: MATERIAL_PAGE_SIZE })
      materialItems.value = response.items
      materialItemsTotal.value = response.total
      materialItemsLoaded.value = true
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při načítání materiálových položek')
      throw error
    } finally {
      loadingMaterialItems.value = false
    }
  }

  /**
   * Fetch next batch (50) — called on scroll, identical to fetchMore() in parts
   */
  async function fetchMoreMaterialItems(): Promise<void> {
    if (loadingMoreMaterialItems.value || !hasMoreMaterialItems.value) return
    loadingMoreMaterialItems.value = true
    try {
      const response = await materialsApi.getMaterialItems({
        skip: materialItems.value.length,
        limit: MATERIAL_BATCH_SIZE
      })
      materialItems.value.push(...response.items)
    } catch {
      // silent
    } finally {
      loadingMoreMaterialItems.value = false
    }
  }

  // Keep backward compat alias used in prefetch
  const loadMaterialItems = fetchMaterialItems

  // ==========================================================================
  // Actions - MaterialInput CRUD (ADR-024)
  // ==========================================================================

  /**
   * Load material inputs for a part
   */
  async function loadMaterialInputs(partId: number, linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)

    // Detect first load vs part switch — keep old data visible during switch
    const isFirstLoad = ctx.currentPartId === null && ctx.materialInputs.length === 0

    ctx.currentPartId = partId
    ctx.initialLoadingInputs = isFirstLoad
    ctx.loadingInputs = true

    try {
      ctx.materialInputs = await materialInputsApi.getMaterialInputs(partId)
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při načítání materiálů')
      ctx.materialInputs = []
      throw error
    } finally {
      ctx.loadingInputs = false
      ctx.initialLoadingInputs = false
    }
  }

  /**
   * Create new material input
   */
  async function createMaterialInput(data: MaterialInputCreate, linkingGroup: LinkingGroup): Promise<MaterialInput> {
    saving.value = true
    try {
      const newMaterial = await materialInputsApi.createMaterialInput(data)

      // Reload list to get updated seq and relationships
      const ctx = getOrCreateContext(linkingGroup)
      if (ctx.currentPartId) {
        await loadMaterialInputs(ctx.currentPartId, linkingGroup)
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

      ui.showSuccess('Materiál vytvořen')
      return newMaterial
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při vytváření materiálu')
      throw error
    } finally {
      saving.value = false
    }
  }

  /**
   * Update material input (optimistic locking)
   */
  async function updateMaterialInput(
    materialId: number,
    data: MaterialInputUpdate,
    linkingGroup: LinkingGroup
  ): Promise<MaterialInput> {
    saving.value = true
    try {
      const updated = await materialInputsApi.updateMaterialInput(materialId, data)

      // Update in local state (preserve operations from existing record)
      const ctx = getOrCreateContext(linkingGroup)
      const index = ctx.materialInputs.findIndex(m => m.id === materialId)
      if (index !== -1) {
        const existing = ctx.materialInputs[index]!
        ctx.materialInputs[index] = { ...existing, ...updated, operations: existing.operations }
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
    } catch (error: unknown) {
      const err = error as { response?: { status: number }; message?: string }
      if (err.response?.status === 409) {
        ui.showError('Data byla změněna jiným uživatelem. Načtěte znovu.')
        // Reload to get latest version
        const ctx = getOrCreateContext(linkingGroup)
        if (ctx.currentPartId) {
          await loadMaterialInputs(ctx.currentPartId, linkingGroup)
        }
      } else {
        ui.showError((error as Error).message || 'Chyba při ukládání materiálu')
      }
      throw error
    } finally {
      saving.value = false
    }
  }

  /**
   * Delete material input
   */
  async function deleteMaterialInput(materialId: number, linkingGroup: LinkingGroup): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.deleteMaterialInput(materialId)

      // Remove from local state
      const ctx = getOrCreateContext(linkingGroup)
      ctx.materialInputs = ctx.materialInputs.filter(m => m.id !== materialId)

      // Trigger batch recalculation for live pricing updates
      if (ctx.currentPartId) {
        try {
          const batchesStore = useBatchesStore()
          await batchesStore.recalculateBatches(linkingGroup, ctx.currentPartId, true)
        } catch (e) {
          // Ignore - batches context may not be initialized
        }
      }

      ui.showSuccess('Materiál smazán')
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při mazání materiálu')
      throw error
    } finally {
      saving.value = false
    }
  }

  /**
   * Link material input to operation
   */
  async function linkMaterialToOperation(
    materialId: number,
    operationId: number,
    linkingGroup: LinkingGroup,
    consumedQuantity?: number
  ): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.linkMaterialToOperation(materialId, operationId, consumedQuantity)

      // Reload to get updated relationships
      const ctx = getOrCreateContext(linkingGroup)
      if (ctx.currentPartId) {
        await loadMaterialInputs(ctx.currentPartId, linkingGroup)
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

      ui.showSuccess('Materiál přiřazen k operaci')
    } catch (error: unknown) {
      const err = error as { response?: { status: number }; message?: string }
      if (err.response?.status === 409) {
        ui.showError('Vazba již existuje')
      } else {
        ui.showError(err.message || 'Chyba při přiřazování materiálu')
      }
      throw error
    } finally {
      saving.value = false
    }
  }

  /**
   * Unlink material input from operation
   */
  async function unlinkMaterialFromOperation(
    materialId: number,
    operationId: number,
    linkingGroup: LinkingGroup
  ): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.unlinkMaterialFromOperation(materialId, operationId)

      // Reload to get updated relationships
      const ctx = getOrCreateContext(linkingGroup)
      if (ctx.currentPartId) {
        await loadMaterialInputs(ctx.currentPartId, linkingGroup)
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

      ui.showSuccess('Vazba odebrána')
    } catch (error: unknown) {
      ui.showError((error as Error).message || 'Chyba při odebírání vazby')
      throw error
    } finally {
      saving.value = false
    }
  }

  // ==========================================================================
  // Actions - Stock Cost
  // ==========================================================================

  /**
   * Set current part and load stock cost
   */
  async function setPartContext(partNumber: string, linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (ctx.currentPartNumber === partNumber) return

    ctx.currentPartNumber = partNumber
    await loadStockCost(linkingGroup)
  }

  /**
   * Load stock cost for current part
   */
  async function loadStockCost(linkingGroup: LinkingGroup): Promise<void> {
    const ctx = getOrCreateContext(linkingGroup)
    if (!ctx.currentPartNumber) {
      ctx.stockCost = null
      return
    }

    ctx.loadingStockCost = true
    try {
      ctx.stockCost = await materialsApi.getStockCost(ctx.currentPartNumber)
    } catch (error: unknown) {
      console.error('[materials] Stock cost error:', error)
      ctx.stockCost = null
    } finally {
      ctx.loadingStockCost = false
    }
  }

  /**
   * Reload stock cost (after material changes)
   */
  async function reloadStockCost(linkingGroup: LinkingGroup): Promise<void> {
    await loadStockCost(linkingGroup)
  }

  // ==========================================================================
  // Actions - Material Parser
  // ==========================================================================

  /**
   * Parse material description
   */
  async function parseMaterial(description: string): Promise<void> {
    if (!description || description.trim().length < 2) {
      parseResult.value = null
      return
    }

    parsingMaterial.value = true
    try {
      parseResult.value = await materialsApi.parseMaterialDescription(description.trim())
    } catch (error: unknown) {
      console.error('[materials] Parse error:', error)
      parseResult.value = null
    } finally {
      parsingMaterial.value = false
    }
  }

  /**
   * Clear parse result
   */
  function clearParseResult(): void {
    parseResult.value = null
  }

  /**
   * Apply parse result to MaterialInput data
   */
  function applyParseResultToMaterialInput(
    inputData: Partial<MaterialInputCreate>
  ): Partial<MaterialInputCreate> {
    if (!parseResult.value || parseResult.value.confidence < 0.4) {
      return inputData
    }

    const result = parseResult.value
    const updated = { ...inputData }

    if (result.shape) {
      updated.stock_shape = result.shape
    }
    if (result.diameter !== null) {
      updated.stock_diameter = result.diameter
    }
    if (result.length !== null) {
      updated.stock_length = result.length
    }
    if (result.width !== null) {
      updated.stock_width = result.width
    }
    if (result.height !== null) {
      updated.stock_height = result.height
    }
    if (result.thickness !== null) {
      updated.stock_height = result.thickness // height = thickness for plate
    }
    if (result.wall_thickness !== null) {
      updated.stock_wall_thickness = result.wall_thickness
    }
    if (result.suggested_price_category_id !== null) {
      updated.price_category_id = result.suggested_price_category_id
    }

    return updated
  }

  // ==========================================================================
  // Helpers
  // ==========================================================================

  /**
   * Format stock shape for display
   */
  function formatShape(shape: StockShape | null | undefined): string {
    const labels: Record<StockShape, string> = {
      round_bar: 'Kulatina (D)',
      square_bar: 'Čtyřhran (□)',
      flat_bar: 'Profil',
      hexagonal_bar: 'Šestihran (⬡)',
      plate: 'Plech',
      tube: 'Trubka (⊙)',
      casting: 'Odlitek',
      forging: 'Výkovek'
    }
    return shape ? labels[shape] || shape : '-'
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
   * Reset all contexts and global state
   */
  function resetAll(): void {
    contexts.value.clear()
    priceCategories.value = []
    materialGroups.value = []
    referenceDataLoaded.value = false
    materialItems.value = []
    materialItemsTotal.value = 0
    materialItemsLoaded.value = false
    loadingMoreMaterialItems.value = false
    parseResult.value = null
    parsingMaterial.value = false
    loading.value = false
    saving.value = false
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State - Global
    priceCategories,
    materialGroups,
    referenceDataLoaded,
    materialItems,
    materialItemsTotal,
    materialItemsLoaded,
    loadingMaterialItems,
    loadingMoreMaterialItems,
    initialLoadingMaterialItems,
    hasMaterialItems,
    hasMoreMaterialItems,
    parseResult,
    parsingMaterial,
    loading,
    saving,

    // Getters - Per-context
    getContext,

    // Computed - Global
    sortedCategories,
    getCategoryById,
    hasValidParseResult,
    getFilteredCategories,

    // Actions - Reference Data
    loadReferenceData,
    loadMaterialItems,    // alias → fetchMaterialItems (used in prefetch)
    fetchMaterialItems,
    fetchMoreMaterialItems,

    // Actions - MaterialInput CRUD
    loadMaterialInputs,
    createMaterialInput,
    updateMaterialInput,
    deleteMaterialInput,
    linkMaterialToOperation,
    unlinkMaterialFromOperation,

    // Actions - Stock Cost
    setPartContext,
    loadStockCost,
    reloadStockCost,

    // Actions - Parser
    parseMaterial,
    clearParseResult,
    applyParseResultToMaterialInput,

    // Helpers
    formatShape,

    // Reset
    reset,
    resetAll
  }
})
