<template>
  <div class="material-module">
    <!-- Header -->
    <div class="module-header">
      <h3 v-if="!inline">🧱 Materiály</h3>
      <div class="header-actions">
        <span v-if="materialInputs.length > 0" class="materials-count">
          {{ materialInputs.length }} materiálů
        </span>
        <button
          class="btn btn-primary btn-sm"
          @click="openCreateForm"
          :disabled="!partId || saving"
        >
          + Přidat materiál
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <span class="spinner"></span>
      Načítám materiály...
    </div>

    <!-- Empty state -->
    <div v-else-if="materialInputs.length === 0" class="empty-state">
      <div class="empty-icon">🧱</div>
      <p>Žádné materiály</p>
      <p class="hint">Přidejte materiál kliknutím na tlačítko výše</p>
    </div>

    <!-- Materials list -->
    <div v-else class="materials-list">
      <div
        v-for="mat in materialInputs"
        :key="mat.id"
        class="material-card"
        :class="{ 'is-expanded': expandedMaterials[mat.id] }"
      >
        <!-- Material header (always visible) -->
        <div class="mat-header" @click="toggleExpanded(mat.id)">
          <div class="mat-info">
            <span class="mat-seq">#{{ mat.seq }}</span>
            <span class="mat-shape">{{ formatShape(mat.stock_shape) }}</span>
            <span class="mat-dims">{{ formatDimensions(mat) }}</span>
            <span v-if="mat.quantity > 1" class="quantity-badge">×{{ mat.quantity }}</span>
          </div>
          <div class="mat-category">
            {{ getCategoryName(mat.price_category_id) }}
          </div>
          <button class="expand-btn" :title="expandedMaterials[mat.id] ? 'Sbalit' : 'Rozbalit'">
            {{ expandedMaterials[mat.id] ? '▲' : '▼' }}
          </button>
        </div>

        <!-- Material details (expanded) -->
        <div v-if="expandedMaterials[mat.id] && editForms[mat.id]" class="mat-details">
          <form @submit.prevent="saveMaterial(mat)" class="mat-form">
            <!-- Row 1: Shape + Category -->
            <div class="form-row">
              <div class="form-group">
                <label>Tvar polotovaru</label>
                <select
                  v-model="form(mat.id).stock_shape"
                  class="form-select"
                  @change="onShapeChange(mat.id)"
                >
                  <option
                    v-for="opt in shapeOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Cenová kategorie</label>
                <select
                  v-model="form(mat.id).price_category_id"
                  class="form-select"
                  required
                >
                  <option :value="null" disabled>-- Vyberte --</option>
                  <option
                    v-for="cat in filteredCategories(form(mat.id).stock_shape)"
                    :key="cat.id"
                    :value="cat.id"
                  >
                    {{ cat.name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Row 2: Dimensions (dynamic based on shape) -->
            <div class="form-row dimensions-row">
              <div v-if="showDiameter(form(mat.id).stock_shape)" class="form-group">
                <label>Průměr [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_diameter"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                />
              </div>
              <div class="form-group">
                <label>Délka [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_length"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                />
              </div>
              <div v-if="showWidth(form(mat.id).stock_shape)" class="form-group">
                <label>Šířka [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_width"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                />
              </div>
              <div v-if="showHeight(form(mat.id).stock_shape)" class="form-group">
                <label>Výška [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_height"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                />
              </div>
              <div v-if="showWallThickness(form(mat.id).stock_shape)" class="form-group">
                <label>Tloušťka stěny [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_wall_thickness"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                />
              </div>
            </div>

            <!-- Row 3: Quantity + Notes -->
            <div class="form-row">
              <div class="form-group" style="max-width: 120px;">
                <label>Počet kusů</label>
                <input
                  v-model.number="form(mat.id).quantity"
                  type="number"
                  class="form-input"
                  min="1"
                />
              </div>
              <div class="form-group" style="flex: 2;">
                <label>Poznámky</label>
                <input
                  v-model="form(mat.id).notes"
                  type="text"
                  class="form-input"
                  maxlength="200"
                  placeholder="Volitelné poznámky"
                />
              </div>
            </div>

            <!-- Linked operations -->
            <div v-if="mat.operations && mat.operations.length > 0" class="linked-ops">
              <label>Přiřazeno k operacím:</label>
              <div class="ops-chips">
                <span
                  v-for="op in mat.operations"
                  :key="op.id"
                  class="op-chip"
                >
                  {{ op.name }}
                  <button type="button" class="unlink-btn" @click="unlinkOperation(mat.id, op.id)">×</button>
                </span>
              </div>
            </div>

            <!-- Actions -->
            <div class="form-actions">
              <button
                type="button"
                class="btn btn-danger btn-sm"
                @click="confirmDelete(mat)"
              >
                🗑️ Smazat
              </button>
              <button
                type="submit"
                class="btn btn-primary btn-sm"
                :disabled="saving"
              >
                {{ saving ? 'Ukládám...' : '💾 Uložit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Stock Cost Summary -->
    <div v-if="stockCost" class="cost-summary">
      <div class="summary-item">
        <span class="summary-label">Hmotnost:</span>
        <span class="summary-value">{{ stockCost.weight_kg.toFixed(2) }} kg</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Cena/kg:</span>
        <span class="summary-value">{{ stockCost.price_per_kg.toFixed(2) }} Kč</span>
      </div>
      <div class="summary-item total">
        <span class="summary-label">Celkem materiál:</span>
        <span class="summary-value">{{ stockCost.cost.toFixed(2) }} Kč</span>
      </div>
    </div>

    <!-- Create Material Modal -->
    <Teleport to="body">
      <div v-if="showCreateForm" class="modal-overlay" @click.self="showCreateForm = false">
        <div class="modal-content modal-wide">
          <h3>Nový materiál</h3>
          <form @submit.prevent="createMaterial" class="create-form">
            <!-- Shape + Category -->
            <div class="form-row">
              <div class="form-group">
                <label>Tvar polotovaru <span class="required">*</span></label>
                <select v-model="newMaterial.stock_shape" class="form-select" required>
                  <option v-for="opt in shapeOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Cenová kategorie <span class="required">*</span></label>
                <select v-model="newMaterial.price_category_id" class="form-select" required>
                  <option :value="null" disabled>-- Vyberte --</option>
                  <option
                    v-for="cat in filteredCategories(newMaterial.stock_shape)"
                    :key="cat.id"
                    :value="cat.id"
                  >
                    {{ cat.name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Dimensions -->
            <div class="form-row">
              <div v-if="showDiameter(newMaterial.stock_shape)" class="form-group">
                <label>Průměr [mm]</label>
                <input v-model.number="newMaterial.stock_diameter" type="number" class="form-input" min="0" step="0.1" />
              </div>
              <div class="form-group">
                <label>Délka [mm] <span class="required">*</span></label>
                <input v-model.number="newMaterial.stock_length" type="number" class="form-input" min="0" step="0.1" required />
              </div>
              <div v-if="showWidth(newMaterial.stock_shape)" class="form-group">
                <label>Šířka [mm]</label>
                <input v-model.number="newMaterial.stock_width" type="number" class="form-input" min="0" step="0.1" />
              </div>
              <div v-if="showHeight(newMaterial.stock_shape)" class="form-group">
                <label>Výška [mm]</label>
                <input v-model.number="newMaterial.stock_height" type="number" class="form-input" min="0" step="0.1" />
              </div>
              <div v-if="showWallThickness(newMaterial.stock_shape)" class="form-group">
                <label>Tloušťka stěny [mm]</label>
                <input v-model.number="newMaterial.stock_wall_thickness" type="number" class="form-input" min="0" step="0.1" />
              </div>
            </div>

            <!-- Quantity -->
            <div class="form-row">
              <div class="form-group" style="max-width: 120px;">
                <label>Počet kusů</label>
                <input v-model.number="newMaterial.quantity" type="number" class="form-input" min="1" />
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn btn-secondary" @click="showCreateForm = false">Zrušit</button>
              <button type="submit" class="btn btn-primary" :disabled="saving || !newMaterial.price_category_id">
                {{ saving ? 'Vytvářím...' : 'Vytvořit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-content">
          <h3>Smazat materiál?</h3>
          <p>Opravdu chcete smazat tento materiál?</p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showDeleteConfirm = false">Zrušit</button>
            <button class="btn btn-danger" @click="executeDelete">Smazat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import { useWindowContextStore } from '@/stores/windowContext'
import type { MaterialInputWithOperations, MaterialInputCreate, StockShape } from '@/types/material'
import type { LinkingGroup } from '@/stores/windows'
import { STOCK_SHAPE_OPTIONS, getShapeDimensionFields } from '@/types/material'

// Props
const props = withDefaults(defineProps<{
  inline?: boolean
  partId: number | null
  partNumber: string
  linkingGroup?: LinkingGroup
}>(), {
  linkingGroup: null
})

// Stores
const materialsStore = useMaterialsStore()
const contextStore = useWindowContextStore()

// Local state
const expandedMaterials = reactive<Record<number, boolean>>({})
const editForms = reactive<Record<number, EditForm>>({})
const showCreateForm = ref(false)
const showDeleteConfirm = ref(false)
const materialToDelete = ref<MaterialInputWithOperations | null>(null)

const newMaterial = reactive<NewMaterialForm>({
  stock_shape: 'round_bar',
  price_category_id: null,
  stock_diameter: null,
  stock_length: 100,
  stock_width: null,
  stock_height: null,
  stock_wall_thickness: null,
  quantity: 1
})

interface EditForm {
  stock_shape: StockShape
  price_category_id: number
  stock_diameter: number | null
  stock_length: number | null
  stock_width: number | null
  stock_height: number | null
  stock_wall_thickness: number | null
  quantity: number
  notes: string | null
}

interface NewMaterialForm {
  stock_shape: StockShape
  price_category_id: number | null
  stock_diameter: number | null
  stock_length: number | null
  stock_width: number | null
  stock_height: number | null
  stock_wall_thickness: number | null
  quantity: number
}

// Shape options
const shapeOptions = STOCK_SHAPE_OPTIONS

// Helper to safely get form (used in template after v-if guard)
function form(matId: number): EditForm {
  return editForms[matId]!
}

// Computed from store (per-context)
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const stockCost = computed(() => materialsStore.getContext(props.linkingGroup).stockCost)
const loading = computed(() => {
  const ctx = materialsStore.getContext(props.linkingGroup)
  return ctx.loadingInputs || materialsStore.loading
})

// Computed from store (global)
const saving = computed(() => materialsStore.saving)

// Computed: Get partId from window context (direct property access for fine-grained reactivity)
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  // Direct access to specific color's ref (NOT via function call)
  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

// Effective partId (context or props)
const effectivePartId = computed(() => contextPartId.value ?? props.partId)

// Watch for partId changes
watch(effectivePartId, async (newPartId) => {
  if (newPartId) {
    await loadData(newPartId)
  }
}, { immediate: true })

// Load data
async function loadData(partId: number) {
  await materialsStore.loadReferenceData()
  await materialsStore.loadMaterialInputs(partId, props.linkingGroup)
  if (props.partNumber) {
    await materialsStore.setPartContext(props.partNumber, props.linkingGroup)
  }
  initEditForms()
}

// Initialize edit forms
function initEditForms() {
  for (const mat of materialInputs.value) {
    if (!editForms[mat.id]) {
      editForms[mat.id] = createEditForm(mat)
    }
  }
}

function createEditForm(mat: MaterialInputWithOperations): EditForm {
  return {
    stock_shape: mat.stock_shape,
    price_category_id: mat.price_category_id,
    stock_diameter: mat.stock_diameter,
    stock_length: mat.stock_length,
    stock_width: mat.stock_width,
    stock_height: mat.stock_height,
    stock_wall_thickness: mat.stock_wall_thickness,
    quantity: mat.quantity,
    notes: mat.notes
  }
}

// Watch changes
watch(materialInputs, () => {
  initEditForms()
}, { deep: true })

// Toggle expanded
function toggleExpanded(matId: number) {
  expandedMaterials[matId] = !expandedMaterials[matId]
}

// Shape-based field visibility
function showDiameter(shape: StockShape): boolean {
  return getShapeDimensionFields(shape).showDiameter
}
function showWidth(shape: StockShape): boolean {
  return getShapeDimensionFields(shape).showWidth
}
function showHeight(shape: StockShape): boolean {
  return getShapeDimensionFields(shape).showHeight
}
function showWallThickness(shape: StockShape): boolean {
  return getShapeDimensionFields(shape).showWallThickness
}

// On shape change
function onShapeChange(matId: number) {
  // Clear irrelevant dimensions
  const form = editForms[matId]
  if (!form) return

  const fields = getShapeDimensionFields(form.stock_shape)
  if (!fields.showDiameter) form.stock_diameter = null
  if (!fields.showWidth) form.stock_width = null
  if (!fields.showHeight) form.stock_height = null
  if (!fields.showWallThickness) form.stock_wall_thickness = null
}

// Filtered categories by shape
function filteredCategories(shape: StockShape) {
  return materialsStore.getFilteredCategories(shape)
}

// Get category name
function getCategoryName(categoryId: number): string {
  const cat = materialsStore.getCategoryById(categoryId)
  return cat?.name || '-'
}

// Format shape
function formatShape(shape: StockShape): string {
  return materialsStore.formatShape(shape)
}

// Format dimensions
function formatDimensions(mat: MaterialInputWithOperations): string {
  const parts: string[] = []
  if (mat.stock_diameter) parts.push(`Ø${mat.stock_diameter}`)
  if (mat.stock_width) parts.push(`${mat.stock_width}`)
  if (mat.stock_height) parts.push(`×${mat.stock_height}`)
  if (mat.stock_length) parts.push(`L${mat.stock_length}`)
  if (mat.stock_wall_thickness) parts.push(`t${mat.stock_wall_thickness}`)
  return parts.join(' ') || '-'
}

// Open create form
function openCreateForm() {
  // Reset form
  newMaterial.stock_shape = 'round_bar'
  newMaterial.price_category_id = null
  newMaterial.stock_diameter = null
  newMaterial.stock_length = 100
  newMaterial.stock_width = null
  newMaterial.stock_height = null
  newMaterial.stock_wall_thickness = null
  newMaterial.quantity = 1
  showCreateForm.value = true
}

// Create material
async function createMaterial() {
  if (!props.partId || !newMaterial.price_category_id) return

  const data: MaterialInputCreate = {
    part_id: props.partId,
    stock_shape: newMaterial.stock_shape,
    price_category_id: newMaterial.price_category_id,
    stock_diameter: newMaterial.stock_diameter,
    stock_length: newMaterial.stock_length,
    stock_width: newMaterial.stock_width,
    stock_height: newMaterial.stock_height,
    stock_wall_thickness: newMaterial.stock_wall_thickness,
    quantity: newMaterial.quantity
  }

  try {
    await materialsStore.createMaterialInput(data, props.linkingGroup)
    showCreateForm.value = false
    initEditForms()
    // Reload stock cost
    if (props.partNumber) {
      await materialsStore.reloadStockCost(props.linkingGroup)
    }
  } catch (error) {
    // Error handled in store
  }
}

// Save material
async function saveMaterial(mat: MaterialInputWithOperations) {
  const form = editForms[mat.id]
  if (!form) return

  try {
    await materialsStore.updateMaterialInput(mat.id, {
      stock_shape: form.stock_shape,
      price_category_id: form.price_category_id,
      stock_diameter: form.stock_diameter,
      stock_length: form.stock_length,
      stock_width: form.stock_width,
      stock_height: form.stock_height,
      stock_wall_thickness: form.stock_wall_thickness,
      quantity: form.quantity,
      notes: form.notes,
      version: mat.version
    }, props.linkingGroup)
    // Reload stock cost
    if (props.partNumber) {
      await materialsStore.reloadStockCost(props.linkingGroup)
    }
  } catch (error) {
    // Error handled in store
  }
}

// Unlink operation
async function unlinkOperation(materialId: number, operationId: number) {
  await materialsStore.unlinkMaterialFromOperation(materialId, operationId, props.linkingGroup)
}

// Delete
function confirmDelete(mat: MaterialInputWithOperations) {
  materialToDelete.value = mat
  showDeleteConfirm.value = true
}

async function executeDelete() {
  if (!materialToDelete.value) return

  await materialsStore.deleteMaterialInput(materialToDelete.value.id, props.linkingGroup)
  delete editForms[materialToDelete.value.id]
  delete expandedMaterials[materialToDelete.value.id]

  showDeleteConfirm.value = false
  materialToDelete.value = null

  // Reload stock cost
  if (props.partNumber) {
    await materialsStore.reloadStockCost(props.linkingGroup)
  }
}
</script>

<style scoped>
.material-module {
  padding: var(--density-module-padding, 1rem);
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--density-section-gap, 0.75rem);
}

.module-header h3 {
  margin: 0;
  font-size: var(--density-font-md, 1rem);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.materials-count {
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.8rem);
}

/* Loading & Empty states */
.loading-state,
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

/* Materials list */
.materials-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.material-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-surface);
  overflow: hidden;
}

.material-card.is-expanded {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Material header */
.mat-header {
  display: flex;
  align-items: center;
  padding: var(--density-cell-py, 0.5rem) var(--density-cell-px, 0.75rem);
  cursor: pointer;
  transition: background 0.15s;
}

.mat-header:hover {
  background: var(--bg-primary);
}

.mat-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.mat-seq {
  font-weight: 600;
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.8rem);
}

.mat-shape {
  font-weight: 500;
}

.mat-dims {
  color: var(--text-secondary);
  font-size: var(--density-font-sm, 0.8rem);
}

.quantity-badge {
  font-size: 0.75rem;
  padding: 2px 6px;
  background: var(--accent-red);
  color: white;
  border-radius: 4px;
  font-weight: 600;
}

.mat-category {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-right: 1rem;
}

.expand-btn {
  background: none;
  border: none;
  font-size: 0.75rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
}

/* Material details */
.mat-details {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.mat-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.dimensions-row .form-group {
  min-width: 100px;
  max-width: 150px;
}

.form-group {
  flex: 1;
  min-width: 150px;
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.required {
  color: var(--accent-red);
}

.form-input,
.form-select {
  width: 100%;
  padding: var(--density-input-py, 0.375rem) var(--density-input-px, 0.5rem);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: var(--density-font-base, 0.8rem);
  background: var(--bg-surface);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-red);
}

/* Linked operations */
.linked-ops {
  padding: 0.75rem;
  background: #eff6ff;
  border-radius: 6px;
}

.linked-ops label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  display: block;
}

.ops-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.op-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 4px;
  font-size: 0.8rem;
}

.unlink-btn {
  background: none;
  border: none;
  color: #1e40af;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
  margin-left: 0.25rem;
}

.unlink-btn:hover {
  color: #dc2626;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
}

/* Cost Summary */
.cost-summary {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  margin-top: 1rem;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
}

.summary-item {
  display: flex;
  gap: 0.5rem;
}

.summary-item.total {
  margin-left: auto;
  font-weight: 600;
}

.summary-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.summary-value {
  font-weight: 500;
}

/* Buttons */
.btn {
  padding: var(--density-btn-py, 0.375rem) var(--density-btn-px, 0.75rem);
  border: none;
  border-radius: 4px;
  font-size: var(--density-font-base, 0.8rem);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-sm {
  padding: var(--density-btn-py, 0.25rem) var(--density-btn-px, 0.5rem);
  font-size: var(--density-font-sm, 0.75rem);
}

.btn-primary {
  background: var(--accent-red);
  color: white;
}

.btn-primary:hover {
  background: #b91c1c;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-danger {
  background: #fee2e2;
  color: #dc2626;
}

.btn-danger:hover {
  background: #fecaca;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 400px;
  width: 90%;
}

.modal-wide {
  max-width: 600px;
}

.modal-content h3 {
  margin: 0 0 1rem 0;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
