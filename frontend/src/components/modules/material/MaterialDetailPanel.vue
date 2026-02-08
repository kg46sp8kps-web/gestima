<script setup lang="ts">
/**
 * Material Detail Panel
 * Handles material input CRUD operations and displays material list
 */
import { ref, computed, reactive, watch } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import type {
  MaterialInputWithOperations,
  MaterialInputCreate,
  MaterialInputUpdate,
  StockShape
} from '@/types/material'
import type { LinkingGroup } from '@/stores/windows'
import { STOCK_SHAPE_OPTIONS, getShapeDimensionFields } from '@/types/material'
import { Package, Trash2, Save } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const materialsStore = useMaterialsStore()

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

// Computed from store (per-context)
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const stockCost = computed(() => materialsStore.getContext(props.linkingGroup).stockCost)
const loading = computed(() => {
  const ctx = materialsStore.getContext(props.linkingGroup)
  return ctx.loadingInputs || materialsStore.loading
})
const saving = computed(() => materialsStore.saving)

// Helper to safely get form (used in template after v-if guard)
function form(matId: number): EditForm {
  return editForms[matId]!
}

// Watch partId changes
watch(() => props.partId, async (newPartId) => {
  if (newPartId) {
    await loadData(newPartId)
  }
}, { immediate: true })

// Load data
async function loadData(partId: number) {
  await materialsStore.loadReferenceData()
  await materialsStore.loadMaterialInputs(partId, props.linkingGroup)
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

// Watch material inputs changes
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
  const formData = editForms[matId]
  if (!formData) return

  const fields = getShapeDimensionFields(formData.stock_shape)
  if (!fields.showDiameter) formData.stock_diameter = null
  if (!fields.showWidth) formData.stock_width = null
  if (!fields.showHeight) formData.stock_height = null
  if (!fields.showWallThickness) formData.stock_wall_thickness = null
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
    await materialsStore.reloadStockCost(props.linkingGroup)
  } catch (error) {
    // Error handled in store
  }
}

// Save material
async function saveMaterial(mat: MaterialInputWithOperations) {
  const formData = editForms[mat.id]
  if (!formData) return

  try {
    await materialsStore.updateMaterialInput(mat.id, {
      stock_shape: formData.stock_shape,
      price_category_id: formData.price_category_id,
      stock_diameter: formData.stock_diameter,
      stock_length: formData.stock_length,
      stock_width: formData.stock_width,
      stock_height: formData.stock_height,
      stock_wall_thickness: formData.stock_wall_thickness,
      quantity: formData.quantity,
      notes: formData.notes,
      version: mat.version
    }, props.linkingGroup)
    await materialsStore.reloadStockCost(props.linkingGroup)
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

  await materialsStore.reloadStockCost(props.linkingGroup)
}
</script>

<template>
  <div class="material-detail-panel">
    <!-- Header Actions -->
    <div class="panel-actions">
      <button
        class="btn-primary"
        @click="openCreateForm"
        :disabled="!partId || saving"
      >
        + Přidat materiál
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Načítám materiály...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="materialInputs.length === 0" class="empty">
      <Package :size="48" class="empty-icon" />
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
        <!-- Material header -->
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

            <!-- Row 2: Dimensions -->
            <div class="form-row dimensions-row">
              <div v-if="showDiameter(form(mat.id).stock_shape)" class="form-group">
                <label>Průměr [mm]</label>
                <input
                  v-model.number="form(mat.id).stock_diameter"
                  type="number"
                  class="form-input"
                  min="0"
                  step="0.1"
                  v-select-on-focus
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
                  v-select-on-focus
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
                  v-select-on-focus
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
                  v-select-on-focus
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
                  v-select-on-focus
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
                  v-select-on-focus
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
                class="btn-danger"
                @click="confirmDelete(mat)"
              >
                <Trash2 :size="ICON_SIZE.SMALL" />
                Smazat
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="saving"
              >
                <Save :size="ICON_SIZE.SMALL" />
                {{ saving ? 'Ukládám...' : 'Uložit' }}
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
                <input v-model.number="newMaterial.stock_diameter" type="number" class="form-input" min="0" step="0.1" v-select-on-focus />
              </div>
              <div class="form-group">
                <label>Délka [mm] <span class="required">*</span></label>
                <input v-model.number="newMaterial.stock_length" type="number" class="form-input" min="0" step="0.1" required v-select-on-focus />
              </div>
              <div v-if="showWidth(newMaterial.stock_shape)" class="form-group">
                <label>Šířka [mm]</label>
                <input v-model.number="newMaterial.stock_width" type="number" class="form-input" min="0" step="0.1" v-select-on-focus />
              </div>
              <div v-if="showHeight(newMaterial.stock_shape)" class="form-group">
                <label>Výška [mm]</label>
                <input v-model.number="newMaterial.stock_height" type="number" class="form-input" min="0" step="0.1" v-select-on-focus />
              </div>
              <div v-if="showWallThickness(newMaterial.stock_shape)" class="form-group">
                <label>Tloušťka stěny [mm]</label>
                <input v-model.number="newMaterial.stock_wall_thickness" type="number" class="form-input" min="0" step="0.1" v-select-on-focus />
              </div>
            </div>

            <!-- Quantity -->
            <div class="form-row">
              <div class="form-group" style="max-width: 120px;">
                <label>Počet kusů</label>
                <input v-model.number="newMaterial.quantity" type="number" class="form-input" min="1" v-select-on-focus />
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showCreateForm = false">Zrušit</button>
              <button type="submit" class="btn-primary" :disabled="saving || !newMaterial.price_category_id">
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
            <button class="btn-secondary" @click="showDeleteConfirm = false">Zrušit</button>
            <button class="btn-danger" @click="executeDelete">Smazat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.material-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-4);
}

/* Panel Actions */
.panel-actions {
  display: flex;
  justify-content: flex-end;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-default);
}

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--palette-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty State */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
  text-align: center;
}

.empty-icon {
  margin-bottom: var(--space-2);
  opacity: 0.5;
  color: var(--text-secondary);
}

.hint {
  font-size: var(--text-sm);
  margin-top: var(--space-2);
}

/* Materials list */
.materials-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.material-card {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  overflow: hidden;
}

.material-card.is-expanded {
  box-shadow: var(--shadow-md);
}

/* Material header */
.mat-header {
  display: flex;
  align-items: center;
  padding: var(--space-3);
  cursor: pointer;
  transition: background 0.15s;
}

.mat-header:hover {
  background: var(--state-hover);
}

.mat-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.mat-seq {
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.mat-shape {
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.mat-dims {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.quantity-badge {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-2);
  background: var(--palette-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-weight: var(--font-semibold);
}

.mat-category {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-right: var(--space-3);
}

.expand-btn {
  background: none;
  border: none;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
  padding: var(--space-1);
}

/* Material details */
.mat-details {
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  background: var(--bg-raised);
}

.mat-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
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
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
  margin-bottom: var(--space-1);
}

.required {
  color: var(--palette-danger);
}

.form-input,
.form-select {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-body);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

/* Linked operations */
.linked-ops {
  padding: var(--space-3);
  background: var(--palette-info-light, rgba(37, 99, 235, 0.1));
  border-radius: var(--radius-md);
  border: 1px solid var(--palette-info);
}

.linked-ops label {
  font-size: var(--text-sm);
  color: var(--text-body);
  margin-bottom: var(--space-2);
  display: block;
}

.ops-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.op-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--palette-info);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.unlink-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: var(--text-base);
  line-height: 1;
  padding: 0;
  margin-left: var(--space-1);
}

.unlink-btn:hover {
  color: var(--palette-danger);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-default);
}

/* Cost Summary */
.cost-summary {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-4);
  margin-top: var(--space-4);
  background: var(--palette-success-light);
  border: 1px solid var(--palette-success);
  border-radius: var(--radius-lg);
}

.summary-item {
  display: flex;
  gap: var(--space-2);
}

.summary-item.total {
  margin-left: auto;
  font-weight: var(--font-semibold);
}

.summary-label {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.summary-value {
  font-weight: var(--font-medium);
  color: var(--text-body);
}

/* Buttons */
.btn-primary,
.btn-secondary,
.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary {
  background: var(--palette-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--palette-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: var(--palette-danger-light, rgba(244, 63, 94, 0.15));
  color: var(--palette-danger);
}

.btn-danger:hover {
  background: var(--palette-danger);
  color: white;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  max-width: 400px;
  width: 90%;
  border: 1px solid var(--border-default);
}

.modal-wide {
  max-width: 600px;
}

.modal-content h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
</style>
