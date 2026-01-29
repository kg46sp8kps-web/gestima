/**
 * Materials Store - Material data for PartMaterialModule
 *
 * ADR-024: MaterialInput refactor (v1.8.0)
 *
 * Manages:
 * - Price categories (for dropdown + filtering)
 * - Material groups (for density calculations)
 * - MaterialInput CRUD (Part → N MaterialInputs)
 * - M:N linking MaterialInput ↔ Operation
 * - Stock cost calculation
 * - Material parser (AI-powered quick input)
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

export const useMaterialsStore = defineStore('materials', () => {
  const ui = useUiStore()

  // ==========================================================================
  // State
  // ==========================================================================

  // Reference data (loaded once)
  const priceCategories = ref<MaterialPriceCategory[]>([])
  const materialGroups = ref<MaterialGroup[]>([])
  const referenceDataLoaded = ref(false)

  // MaterialInput data (ADR-024)
  const materialInputs = ref<MaterialInputWithOperations[]>([])
  const currentPartId = ref<number | null>(null)
  const currentPartNumber = ref<string | null>(null)

  // Stock cost (total for all material inputs)
  const stockCost = ref<StockCost | null>(null)

  // Parser state
  const parseResult = ref<MaterialParseResult | null>(null)
  const parsingMaterial = ref(false)

  // Loading states
  const loading = ref(false)
  const loadingInputs = ref(false)
  const saving = ref(false)
  const loadingStockCost = ref(false)

  // ==========================================================================
  // Computed
  // ==========================================================================

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
        `⚠️ No categories found for shape ${stockShape} with suffixes ${suffixes.join(', ')} - showing all`
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
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání materiálů')
      throw error
    } finally {
      loading.value = false
    }
  }

  // ==========================================================================
  // Actions - MaterialInput CRUD (ADR-024)
  // ==========================================================================

  /**
   * Load material inputs for a part
   */
  async function loadMaterialInputs(partId: number): Promise<void> {
    currentPartId.value = partId
    loadingInputs.value = true

    try {
      materialInputs.value = await materialInputsApi.getMaterialInputs(partId)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání materiálů')
      materialInputs.value = []
      throw error
    } finally {
      loadingInputs.value = false
    }
  }

  /**
   * Create new material input
   */
  async function createMaterialInput(data: MaterialInputCreate): Promise<MaterialInput> {
    saving.value = true
    try {
      const newMaterial = await materialInputsApi.createMaterialInput(data)

      // Reload list to get updated seq and relationships
      if (currentPartId.value) {
        await loadMaterialInputs(currentPartId.value)
      }

      ui.showSuccess('Materiál vytvořen')
      return newMaterial
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při vytváření materiálu')
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
    data: MaterialInputUpdate
  ): Promise<MaterialInput> {
    saving.value = true
    try {
      const updated = await materialInputsApi.updateMaterialInput(materialId, data)

      // Update in local state
      const index = materialInputs.value.findIndex(m => m.id === materialId)
      if (index !== -1) {
        materialInputs.value[index] = { ...materialInputs.value[index], ...updated }
      }

      return updated
    } catch (error: any) {
      if (error.response?.status === 409) {
        ui.showError('Data byla změněna jiným uživatelem. Načtěte znovu.')
        // Reload to get latest version
        if (currentPartId.value) {
          await loadMaterialInputs(currentPartId.value)
        }
      } else {
        ui.showError(error.message || 'Chyba při ukládání materiálu')
      }
      throw error
    } finally {
      saving.value = false
    }
  }

  /**
   * Delete material input
   */
  async function deleteMaterialInput(materialId: number): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.deleteMaterialInput(materialId)

      // Remove from local state
      materialInputs.value = materialInputs.value.filter(m => m.id !== materialId)

      ui.showSuccess('Materiál smazán')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání materiálu')
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
    consumedQuantity?: number
  ): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.linkMaterialToOperation(materialId, operationId, consumedQuantity)

      // Reload to get updated relationships
      if (currentPartId.value) {
        await loadMaterialInputs(currentPartId.value)
      }

      ui.showSuccess('Materiál přiřazen k operaci')
    } catch (error: any) {
      if (error.response?.status === 409) {
        ui.showError('Vazba již existuje')
      } else {
        ui.showError(error.message || 'Chyba při přiřazování materiálu')
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
    operationId: number
  ): Promise<void> {
    saving.value = true
    try {
      await materialInputsApi.unlinkMaterialFromOperation(materialId, operationId)

      // Reload to get updated relationships
      if (currentPartId.value) {
        await loadMaterialInputs(currentPartId.value)
      }

      ui.showSuccess('Vazba odebrána')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při odebírání vazby')
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
  async function setPartContext(partNumber: string): Promise<void> {
    if (currentPartNumber.value === partNumber) return

    currentPartNumber.value = partNumber
    await loadStockCost()
  }

  /**
   * Load stock cost for current part
   */
  async function loadStockCost(): Promise<void> {
    if (!currentPartNumber.value) {
      stockCost.value = null
      return
    }

    loadingStockCost.value = true
    try {
      stockCost.value = await materialsApi.getStockCost(currentPartNumber.value)
    } catch (error: any) {
      console.error('[materials] Stock cost error:', error)
      stockCost.value = null
    } finally {
      loadingStockCost.value = false
    }
  }

  /**
   * Reload stock cost (after material changes)
   */
  async function reloadStockCost(): Promise<void> {
    await loadStockCost()
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
    } catch (error: any) {
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

  function reset(): void {
    currentPartId.value = null
    currentPartNumber.value = null
    materialInputs.value = []
    stockCost.value = null
    parseResult.value = null
    parsingMaterial.value = false
    loading.value = false
    loadingInputs.value = false
    saving.value = false
    loadingStockCost.value = false
  }

  function resetAll(): void {
    reset()
    priceCategories.value = []
    materialGroups.value = []
    referenceDataLoaded.value = false
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    priceCategories,
    materialGroups,
    referenceDataLoaded,
    materialInputs,
    currentPartId,
    currentPartNumber,
    stockCost,
    parseResult,
    parsingMaterial,
    loading,
    loadingInputs,
    saving,
    loadingStockCost,

    // Computed
    sortedCategories,
    getCategoryById,
    hasValidParseResult,
    getFilteredCategories,

    // Actions - Reference Data
    loadReferenceData,

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
