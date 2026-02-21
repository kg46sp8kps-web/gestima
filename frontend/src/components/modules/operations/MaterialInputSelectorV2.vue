<script setup lang="ts">
/**
 * Material Input Selector V2 (BUILDING BLOCK - L-039)
 *
 * Features:
 * 1. Parser input (text field) jako hlavní řádek
 * 2. Po potvrzení → zobrazí vybraný materiál (editable délka)
 * 3. Dropdown (ne modal) pro detail + manuální vložení
 * 4. Dvě možnosti výběru:
 *    - Konkrétní MaterialItem (když parser najde přesnou shodu)
 *    - Obecný MaterialPriceCategory (když nenajde konkrétní položku)
 */

import { computed, watch, ref, onMounted } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import { useOperationsStore } from '@/stores/operations'
import { parseMaterialDescription } from '@/api/materials'
import { ChevronDown, ChevronUp, Plus, X, Check } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { LinkingGroup } from '@/stores/windows'
import type { MaterialInputCreate } from '@/types/material'
import type { MaterialInputWithOperations, MaterialParseResult } from '@/types/material'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
  hideHeader?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
  hideHeader: false
})

const materialsStore = useMaterialsStore()
const operationsStore = useOperationsStore()

// State
const parserText = ref('')
const parsing = ref(false)
const parseResult = ref<MaterialParseResult | null>(null)
const selectedMaterialId = ref<number | null>(null)
const expandedMaterialId = ref<number | null>(null)
const editingLengthId = ref<number | null>(null)
const tempLength = ref<number | null>(null)

// Computed
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const loading = computed(() => materialsStore.getContext(props.linkingGroup).loadingInputs)
const initialLoading = computed(() => materialsStore.getContext(props.linkingGroup).initialLoadingInputs)

// Load materials when partId changes
watch(() => props.partId, async (newPartId) => {
  if (newPartId) {
    await materialsStore.loadMaterialInputs(newPartId, props.linkingGroup)
  }
}, { immediate: true })

// Parse material description
async function handleParse() {
  if (!parserText.value.trim()) return

  parsing.value = true
  try {
    const result = await parseMaterialDescription(parserText.value)
    parseResult.value = result

    // Auto-confirm if high confidence
    if (result.confidence >= 0.7) {
      await handleConfirmParse()
    }
  } catch (error) {
    console.error('Failed to parse material:', error)
  } finally {
    parsing.value = false
  }
}

// Confirm parse result → create MaterialInput
async function handleConfirmParse() {
  if (!parseResult.value || !props.partId) return

  const result = parseResult.value

  // price_category_id je VŽDY required (MaterialItem má vztah k PriceCategory)
  if (!result.suggested_price_category_id) {
    console.error('Parser nevrátil price_category_id (required)')
    return
  }

  // Build MaterialInput payload - shape must be non-null
  if (!result.shape) {
    console.error('Parser nevrátil stock_shape (required)')
    return
  }

  const payload: MaterialInputCreate = {
    part_id: props.partId,
    seq: materialInputs.value.length * 10 + 10,
    stock_shape: result.shape,
    stock_diameter: result.diameter,
    stock_width: result.width,
    stock_height: result.height,
    stock_wall_thickness: result.wall_thickness,
    stock_length: result.length,
    quantity: 1,
    price_category_id: result.suggested_price_category_id,
    material_item_id: result.suggested_material_item_id || null
  }

  try {
    await materialsStore.createMaterialInput(payload, props.linkingGroup)

    // Reset parser
    parserText.value = ''
    parseResult.value = null

    // Reload materials
    if (props.partId) {
      await materialsStore.loadMaterialInputs(props.partId, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to create material input:', error)
  }
}

// Cancel parse
function handleCancelParse() {
  parseResult.value = null
}

// Format material label for display — returns { code, name } separately
function getMaterialCode(material: MaterialInputWithOperations): string {
  return material.material_item?.code ?? ''
}

function getMaterialName(material: MaterialInputWithOperations): string {
  if (material.material_item?.name) return material.material_item.name
  if (material.price_category?.name) return material.price_category.name
  return ''
}

function formatDimensions(material: MaterialInputWithOperations): string {
  if (material.stock_shape === 'round_bar' && material.stock_diameter) {
    return `Ø${material.stock_diameter}`
  } else if (material.stock_shape === 'square_bar' && material.stock_width) {
    return `□${material.stock_width}`
  } else if (material.stock_shape === 'flat_bar' && material.stock_width && material.stock_height) {
    return `${material.stock_width}×${material.stock_height}`
  }
  return ''
}

// Toggle dropdown
function toggleDropdown(materialId: number) {
  expandedMaterialId.value = expandedMaterialId.value === materialId ? null : materialId
}

// Start editing length
function startEditLength(material: MaterialInputWithOperations) {
  editingLengthId.value = material.id
  tempLength.value = material.stock_length
}

// Save length
async function saveLength(material: MaterialInputWithOperations) {
  if (tempLength.value === null || tempLength.value === material.stock_length) {
    editingLengthId.value = null
    return
  }

  try {
    await materialsStore.updateMaterialInput(
      material.id,
      { stock_length: tempLength.value, version: material.version },
      props.linkingGroup
    )
    editingLengthId.value = null
  } catch (error) {
    console.error('Failed to update length:', error)
  }
}

// Cancel length edit
function cancelEditLength() {
  editingLengthId.value = null
  tempLength.value = null
}

// Delete material
async function deleteMaterial(materialId: number) {
  try {
    await materialsStore.deleteMaterialInput(materialId, props.linkingGroup)
    if (props.partId) {
      await materialsStore.loadMaterialInputs(props.partId, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to delete material:', error)
  }
}

// Calculate total cost
const totalMaterialCost = computed(() => {
  return materialInputs.value.reduce((sum, mat) => sum + (mat.cost_per_piece || 0), 0)
})
</script>

<template>
  <div class="material-input-selector-v2">
    <div v-if="!hideHeader" class="selector-header">
      <label class="selector-label">Materiál</label>
    </div>

    <!-- PARSER INPUT (hlavní řádek) -->
    <div class="parser-input">
      <input
        v-model="parserText"
        type="text"
        class="parser-field"
        placeholder="Např: D20 1.4301 100mm (stiskni Enter)"
        :disabled="loading || parsing"
        @keyup.enter="handleParse"
      />
      <button
        v-if="parsing"
        class="btn-parse"
        disabled
        title="Parsování..."
      >
        <div class="spinner"></div>
      </button>
      <button
        v-else-if="parserText"
        class="btn-parse"
        @click="handleParse"
        title="Parsovat materiál"
      >
        <Plus :size="ICON_SIZE.STANDARD" />
      </button>
    </div>

    <!-- PARSE RESULT PREVIEW (po parsingu před potvrzením) -->
    <div v-if="parseResult && parseResult.confidence >= 0.4" class="parse-preview">
      <div class="preview-header">
        <span class="preview-label">Rozpoznáno:</span>
        <span class="preview-confidence">{{ Math.round(parseResult.confidence * 100) }}%</span>
      </div>
      <div class="preview-content">
        <div class="preview-values">
          <span v-if="parseResult.shape" class="preview-item">{{ parseResult.shape }}</span>
          <span v-if="parseResult.diameter" class="preview-item">Ø{{ parseResult.diameter }}</span>
          <span v-if="parseResult.width" class="preview-item">{{ parseResult.width }}mm</span>
          <span v-if="parseResult.height" class="preview-item">×{{ parseResult.height }}mm</span>
          <span v-if="parseResult.length" class="preview-item">L{{ parseResult.length }}mm</span>
          <span v-if="parseResult.material_norm" class="preview-item">{{ parseResult.material_norm }}</span>
        </div>
        <div class="preview-type">
          <span v-if="parseResult.suggested_material_item_id" class="type-badge item">
            {{ parseResult.suggested_material_item_name || `Položka #${parseResult.suggested_material_item_id}` }}
          </span>
          <span v-else-if="parseResult.suggested_price_category_id" class="type-badge category">
            {{ parseResult.suggested_price_category_name || 'Obecný materiál' }}
          </span>
        </div>
        <div v-if="parseResult.suggested_material_group_name" class="preview-group">
          <span class="preview-item">{{ parseResult.suggested_material_group_name }}</span>
        </div>
        <div v-if="parseResult.warnings?.length" class="preview-warnings">
          <span v-for="w in parseResult.warnings" :key="w" class="preview-warning">{{ w }}</span>
        </div>
      </div>
      <div class="preview-actions">
        <button class="btn-cancel" @click="handleCancelParse" title="Zrušit">
          <X :size="ICON_SIZE.SMALL" />
        </button>
        <button class="btn-confirm" @click="handleConfirmParse" title="Potvrdit">
          <Check :size="ICON_SIZE.SMALL" />
          Potvrdit
        </button>
      </div>
    </div>

    <!-- LOW CONFIDENCE WARNING -->
    <div v-else-if="parseResult && parseResult.confidence < 0.4" class="parse-warning">
      Nepodařilo se rozpoznat materiál. Zkuste jiný formát nebo zadejte ručně.
    </div>

    <!-- MATERIAL LIST (potvrzené materiály) -->
    <div v-if="materialInputs.length > 0" class="material-list">
      <div
        v-for="material in materialInputs"
        :key="material.id"
        class="material-item"
        :class="{ expanded: expandedMaterialId === material.id }"
      >
        <!-- Main row — celý řádek klikatelný pro toggle -->
        <div class="material-main-row" @click="toggleDropdown(material.id)">
          <div class="material-info">
            <div class="material-label-group">
              <span v-if="getMaterialCode(material)" class="material-code">{{ getMaterialCode(material) }}</span>
              <span v-if="getMaterialCode(material)" class="material-sep">·</span>
              <span class="material-name">{{ getMaterialName(material) }}</span>
              <span class="material-sep">·</span>
              <span v-if="editingLengthId === material.id" class="length-edit" @click.stop>
                <input
                  v-model.number="tempLength"
                  type="number"
                  class="length-input"
                  @keyup.enter="saveLength(material)"
                  @keyup.esc="cancelEditLength"
                />
                <button class="btn-icon-sm" @click="saveLength(material)" title="Uložit">
                  <Check :size="ICON_SIZE.SMALL" />
                </button>
                <button class="btn-icon-sm" @click="cancelEditLength" title="Zrušit">
                  <X :size="ICON_SIZE.SMALL" />
                </button>
              </span>
              <button
                v-else
                class="length-inline-btn"
                @click.stop="startEditLength(material)"
                title="Klikni pro úpravu délky"
              >
                <span class="param-key">L=</span>{{ material.stock_length || 0 }}<span class="param-unit">mm</span>
              </button>
            </div>
          </div>

          <div class="material-actions">
            <span v-if="material.cost_per_piece" class="material-cost">
              {{ material.cost_per_piece.toFixed(0) }} Kč
            </span>
            <span class="btn-toggle" title="Zobrazit detail">
              <ChevronDown v-if="expandedMaterialId !== material.id" :size="ICON_SIZE.SMALL" />
              <ChevronUp v-else :size="ICON_SIZE.SMALL" />
            </span>
            <button
              class="btn-delete"
              @click.stop="deleteMaterial(material.id)"
              title="Smazat materiál"
            >
              <X :size="ICON_SIZE.SMALL" />
            </button>
          </div>
        </div>

        <!-- Dropdown detail -->
        <div v-if="expandedMaterialId === material.id" class="material-dropdown">
          <div class="dropdown-section">
            <span class="dropdown-label">Typ:</span>
            <span class="dropdown-value">
              <span v-if="material.material_item" class="type-badge item">
                {{ material.material_item.name }}
              </span>
              <span v-else-if="material.price_category" class="type-badge category">
                {{ material.price_category.name }}
              </span>
              <span v-else class="type-badge category">
                Obecný materiál
              </span>
            </span>
          </div>
          <div v-if="material.material_item" class="dropdown-section">
            <span class="dropdown-label">Kód:</span>
            <span class="dropdown-value">{{ material.material_item.code }}</span>
          </div>
          <div class="dropdown-section">
            <span class="dropdown-label">Délka:</span>
            <div v-if="editingLengthId === material.id" class="length-edit" @click.stop>
              <input
                v-model.number="tempLength"
                type="number"
                class="length-input"
                @keyup.enter="saveLength(material)"
                @keyup.esc="cancelEditLength"
              />
              <button class="btn-icon-sm" @click="saveLength(material)" title="Uložit">
                <Check :size="ICON_SIZE.SMALL" />
              </button>
              <button class="btn-icon-sm" @click="cancelEditLength" title="Zrušit">
                <X :size="ICON_SIZE.SMALL" />
              </button>
            </div>
            <button
              v-else
              class="length-inline-btn"
              @click.stop="startEditLength(material)"
              title="Klikni pro úpravu délky"
            >
              <span class="param-key">L=</span>{{ material.stock_length || 0 }}<span class="param-unit">mm</span>
            </button>
          </div>
          <div v-if="material.weight_kg" class="dropdown-section">
            <span class="dropdown-label">Hmotnost:</span>
            <span class="dropdown-value">{{ material.weight_kg.toFixed(2) }} kg</span>
          </div>
          <div v-if="material.price_per_kg" class="dropdown-section">
            <span class="dropdown-label">Cena/kg:</span>
            <span class="dropdown-value">{{ material.price_per_kg.toFixed(0) }} Kč</span>
          </div>
          <div class="dropdown-section">
            <span class="dropdown-label">Rozměry:</span>
            <span class="dropdown-value">
              <span v-if="material.stock_diameter">Ø{{ material.stock_diameter }}</span>
              <span v-if="material.stock_width">{{ material.stock_width }}mm</span>
              <span v-if="material.stock_height">×{{ material.stock_height }}mm</span>
              <span v-if="material.stock_wall_thickness">t{{ material.stock_wall_thickness }}mm</span>
            </span>
          </div>

          <!-- TODO: Manuální vložení zde -->
          <div class="dropdown-actions">
            <button class="btn-manual" disabled>
              Manuální úprava (TODO)
            </button>
          </div>
        </div>
      </div>

      <!-- Total cost summary -->
      <div v-if="materialInputs.length > 1" class="material-total">
        <span class="total-label">Celkem:</span>
        <span class="total-value">{{ totalMaterialCost.toFixed(0) }} Kč</span>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && !initialLoading && !parseResult" class="empty-state">
      <span class="empty-text">Zadejte materiál výše</span>
    </div>

    <!-- Loading state (only on first load — no flash on part switch) -->
    <div v-if="initialLoading" class="loading-state">
      <div class="spinner"></div>
      <span>Načítám materiály...</span>
    </div>
  </div>
</template>

<style scoped>
.material-input-selector-v2 {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selector-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Parser input */
.parser-input {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.parser-field {
  flex: 1;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  background: var(--bg-base);
  color: var(--text-primary);
  transition: var(--transition-fast);
}

.parser-field:focus {
  outline: none;
  border-color: var(--color-primary);
}

.parser-field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-parse {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-parse:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-parse:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Parse preview */
.parse-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-info-subtle);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.preview-confidence {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-success);
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.preview-values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.preview-item {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-base);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.preview-type {
  display: flex;
  gap: var(--space-1);
}

.preview-group {
  display: flex;
  gap: var(--space-1);
}

.preview-warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.preview-warning {
  font-size: var(--text-xs);
  color: var(--color-warning);
}

.type-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.type-badge.item {
  background: var(--bg-success-subtle);
  color: var(--color-success);
}

.type-badge.category {
  background: var(--bg-warning-subtle);
  color: var(--color-warning);
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.btn-cancel {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-cancel:hover {
  background: var(--bg-hover);
}

.btn-confirm {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--color-success);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-confirm:hover {
  background: var(--color-success-hover);
}

/* Parse warning */
.parse-warning {
  padding: var(--space-2);
  background: var(--bg-warning-subtle);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--color-warning);
}

/* Material list */
.material-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.material-item {
  display: flex;
  flex-direction: column;
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.material-item.expanded {
  border-color: var(--border-strong);
}

.material-main-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 28px;
  padding: 0 var(--space-2);
  cursor: pointer;
}

.material-main-row:hover {
  background: var(--hover);
  border-radius: var(--radius-md);
}

.material-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.material-label-group {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.material-code {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
  line-height: 1;
  white-space: nowrap;
  flex-shrink: 0;
}

.material-sep {
  display: inline-flex;
  align-items: center;
  line-height: 1;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  flex-shrink: 0;
  user-select: none;
}

.material-name {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  color: var(--text-secondary);
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.length-inline-btn {
  display: inline-flex;
  align-items: center;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
  line-height: 1;
  cursor: pointer;
  text-decoration: none;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.length-inline-btn:hover {
  color: var(--color-primary);
}

.param-key {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  color: var(--text-secondary);
  margin-right: 2px;
}

.param-unit {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  color: var(--text-secondary);
  margin-left: 2px;
}

.length-edit {
  display: flex;
  gap: var(--space-1);
  align-items: center;
}

.length-input {
  width: 60px;
  height: 20px;
  padding: 0 var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--text-primary);
  box-sizing: border-box;
  -moz-appearance: textfield;
}

.length-input:focus {
  outline: none;
  border-color: var(--focus-ring);
  background: var(--focus-bg);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.btn-icon-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: var(--transition-fast);
}

.btn-icon-sm:hover {
  background: var(--bg-hover);
}

.material-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.material-cost {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.btn-toggle,
.btn-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: var(--transition-fast);
  color: var(--text-secondary);
}

.btn-toggle:hover {
  color: var(--color-primary);
}

.btn-delete:hover {
  color: var(--color-danger);
}

/* Dropdown detail */
.material-dropdown {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  border-top: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.dropdown-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dropdown-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}

.dropdown-value {
  font-size: var(--text-xs);
  color: var(--text-primary);
}

.dropdown-value .type-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.dropdown-value .type-badge.item {
  background: var(--bg-success-subtle);
  color: var(--color-success);
}

.dropdown-value .type-badge.category {
  background: var(--bg-warning-subtle);
  color: var(--color-warning);
}

.dropdown-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.btn-manual {
  flex: 1;
  padding: var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-manual:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-manual:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Total summary */
.material-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2);
  background: var(--bg-base);
  border-top: 2px solid var(--border-default);
}

.total-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}

.total-value {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  font-family: var(--font-mono);
}

/* Empty/Loading states */

.empty-text {
  color: var(--text-secondary);
}

/* Spinner */

</style>
