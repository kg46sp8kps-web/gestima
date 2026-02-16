<script setup lang="ts">
/**
 * Price Categories Panel - CRUD for price categories with tiers management
 * Extracted from MasterAdminModule.vue
 */

import { ref, onMounted } from 'vue'
import { confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import type {
  MaterialGroup,
  MaterialPriceCategory,
  MaterialPriceCategoryCreate,
  MaterialPriceCategoryUpdate,
  MaterialPriceTier,
  MaterialPriceTierCreate,
  MaterialPriceTierUpdate
} from '@/types/material'
import {
  getAdminMaterialGroups,
  getPriceCategories,
  createPriceCategory,
  updatePriceCategory,
  deletePriceCategory,
  getPriceTiers,
  createPriceTier,
  updatePriceTier,
  deletePriceTier
} from '@/api/materials'
import { Trash2, CheckCircle, XCircle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const uiStore = useUiStore()

// State
const groups = ref<MaterialGroup[]>([])
const categories = ref<MaterialPriceCategory[]>([])
const loadingCategories = ref(false)
const showCategoryModal = ref(false)
const editingCategory = ref<MaterialPriceCategory | null>(null)
const savingCategory = ref(false)

// Price Tiers Management
const tiers = ref<MaterialPriceTier[]>([])
const selectedCategory = ref<MaterialPriceCategory | null>(null)
const loadingTiers = ref(false)
const showTierModal = ref(false)
const editingTier = ref<MaterialPriceTier | null>(null)
const savingTier = ref(false)

// Inline cell editing
const editingCell = ref<{ tierId: number; field: string } | null>(null)
const cellEditValue = ref<number | null>(null)

const categoryForm = ref({
  code: '',
  name: '',
  material_group_id: null as number | null,
  version: 0
})

const categoryColumns: Column[] = [
  { key: 'code', label: 'Kod', sortable: true, width: '120px' },
  { key: 'name', label: 'Nazev', sortable: true },
  { key: 'material_group.name', label: 'Skupina materialu', sortable: true }
]

const tierForm = ref({
  min_weight: 0,
  max_weight: null as number | null,
  price_per_kg: 0,
  version: 0
})

// Methods
async function loadGroups() {
  try {
    groups.value = await getAdminMaterialGroups()
  } catch (error) {
    console.error('Failed to load groups:', error)
  }
}

async function loadCategories() {
  loadingCategories.value = true
  try {
    categories.value = await getPriceCategories()
  } catch (error) {
    uiStore.showError('Chyba pri nacitani cenovych kategorii')
    console.error(error)
  } finally {
    loadingCategories.value = false
  }
}

function openCreateCategoryModal() {
  editingCategory.value = null
  categoryForm.value = {
    code: '',
    name: '',
    material_group_id: null,
    version: 0
  }
  showCategoryModal.value = true
}

async function openEditCategoryModal(row: Record<string, unknown>) {
  const category = row as unknown as MaterialPriceCategory
  editingCategory.value = category
  selectedCategory.value = category
  categoryForm.value = {
    code: category.code,
    name: category.name,
    material_group_id: category.material_group_id,
    version: category.version
  }
  showCategoryModal.value = true
  await loadTiers(category.id)
}

async function saveCategory() {
  savingCategory.value = true
  try {
    if (editingCategory.value) {
      const updateData: MaterialPriceCategoryUpdate = {
        code: categoryForm.value.code,
        name: categoryForm.value.name,
        material_group_id: categoryForm.value.material_group_id,
        version: categoryForm.value.version
      }
      await updatePriceCategory(editingCategory.value.id, updateData)
      uiStore.showSuccess('Kategorie aktualizovana')
    } else {
      const createData: MaterialPriceCategoryCreate = {
        code: categoryForm.value.code,
        name: categoryForm.value.name,
        material_group_id: categoryForm.value.material_group_id
      }
      await createPriceCategory(createData)
      uiStore.showSuccess('Kategorie vytvorena')
    }
    showCategoryModal.value = false
    await loadCategories()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
  } finally {
    savingCategory.value = false
  }
}

async function deleteCategoryItem(category: MaterialPriceCategory) {
  const confirmed = await confirm({
    title: 'Smazat kategorii?',
    message: `Opravdu chcete smazat kategorii ${category.code} - ${category.name}?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrusit'
  })

  if (!confirmed) return

  try {
    await deletePriceCategory(category.id)
    uiStore.showSuccess('Kategorie smazana')
    showCategoryModal.value = false
    await loadCategories()
  } catch (error) {
    uiStore.showError('Chyba pri mazani kategorie')
    console.error(error)
  }
}

// Price Tiers Methods
async function loadTiers(categoryId: number) {
  loadingTiers.value = true
  try {
    tiers.value = await getPriceTiers(categoryId)
  } catch (error) {
    uiStore.showError('Chyba pri nacitani cenovych stupnu')
    console.error(error)
  } finally {
    loadingTiers.value = false
  }
}

function openCreateTierModal() {
  editingTier.value = null
  tierForm.value = {
    min_weight: 0,
    max_weight: null,
    price_per_kg: 0,
    version: 0
  }
  showTierModal.value = true
}

function startEditCell(tier: MaterialPriceTier, field: 'min_weight' | 'max_weight' | 'price_per_kg') {
  editingCell.value = { tierId: tier.id, field }
  cellEditValue.value = tier[field]
}

function cancelCellEdit() {
  editingCell.value = null
  cellEditValue.value = null
}

async function saveCellEdit(tier: MaterialPriceTier) {
  if (!editingCell.value || !selectedCategory.value) return

  const field = editingCell.value.field as 'min_weight' | 'max_weight' | 'price_per_kg'
  const newValue = cellEditValue.value

  if (field !== 'max_weight' && (newValue === null || newValue < 0)) {
    uiStore.showError('Hodnota musi byt kladne cislo')
    cancelCellEdit()
    return
  }

  try {
    const updateData: MaterialPriceTierUpdate = {
      min_weight: tier.min_weight,
      max_weight: tier.max_weight,
      price_per_kg: tier.price_per_kg,
      [field]: newValue,
      version: tier.version
    }

    await updatePriceTier(tier.id, updateData)
    uiStore.showSuccess('Hodnota aktualizovana')
    cancelCellEdit()
    await loadTiers(selectedCategory.value.id)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
    cancelCellEdit()
  }
}

function cancelAddTier() {
  showTierModal.value = false
  tierForm.value = {
    min_weight: 0,
    max_weight: null,
    price_per_kg: 0,
    version: 0
  }
}

async function saveTier() {
  if (!selectedCategory.value) return

  savingTier.value = true
  try {
    if (editingTier.value) {
      const updateData: MaterialPriceTierUpdate = {
        min_weight: tierForm.value.min_weight,
        max_weight: tierForm.value.max_weight,
        price_per_kg: tierForm.value.price_per_kg,
        version: tierForm.value.version
      }
      await updatePriceTier(editingTier.value.id, updateData)
      uiStore.showSuccess('Cenovy stupen aktualizovan')
    } else {
      const createData: MaterialPriceTierCreate = {
        price_category_id: selectedCategory.value.id,
        min_weight: tierForm.value.min_weight,
        max_weight: tierForm.value.max_weight,
        price_per_kg: tierForm.value.price_per_kg
      }
      await createPriceTier(createData)
      uiStore.showSuccess('Cenovy stupen vytvoren')
    }

    editingTier.value = null
    showTierModal.value = false
    tierForm.value = {
      min_weight: 0,
      max_weight: null,
      price_per_kg: 0,
      version: 0
    }

    await loadTiers(selectedCategory.value.id)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
  } finally {
    savingTier.value = false
  }
}

async function deleteTierItem(tier: MaterialPriceTier) {
  const confirmed = await confirm({
    title: 'Smazat cenovy stupen?',
    message: `Opravdu chcete smazat cenovy stupen ${tier.min_weight}-${tier.max_weight || 'inf'} kg?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrusit'
  })

  if (!confirmed) return
  if (!selectedCategory.value) return

  try {
    await deletePriceTier(tier.id)
    uiStore.showSuccess('Cenovy stupen smazan')
    await loadTiers(selectedCategory.value.id)
  } catch (error) {
    uiStore.showError('Chyba pri mazani cenoveho stupne')
    console.error(error)
  }
}

// Lifecycle
onMounted(async () => {
  await loadGroups()
  await loadCategories()
})
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <h2>Cenove kategorie</h2>
      <button class="btn btn-primary" @click="openCreateCategoryModal">+ Pridat kategorii</button>
    </div>

    <DataTable
      :data="categories"
      :columns="categoryColumns"
      :loading="loadingCategories"
      :row-clickable="true"
      empty-text="Zadne cenove kategorie"
      @row-click="openEditCategoryModal"
    />

    <Modal
      v-model="showCategoryModal"
      :title="editingCategory ? `Upravit kategorii - ${categoryForm.code}` : 'Nova kategorie'"
      size="lg"
    >
      <div class="combined-category-modal">
        <form @submit.prevent="saveCategory" class="category-form-section">
          <h3 class="section-title">Zakladni informace</h3>
          <div class="form-group">
            <label>Kod *</label>
            <input v-model="categoryForm.code" type="text" maxlength="20" required />
          </div>
          <div class="form-group">
            <label>Nazev *</label>
            <input v-model="categoryForm.name" type="text" maxlength="100" required />
          </div>
          <div class="form-group">
            <label>Skupina materialu</label>
            <select v-model="categoryForm.material_group_id">
              <option :value="null">-- Bez skupiny --</option>
              <option v-for="group in groups" :key="group.id" :value="group.id">
                {{ group.code }} - {{ group.name }}
              </option>
            </select>
          </div>
          <div class="form-actions">
            <button
              v-if="editingCategory"
              type="button"
              class="btn btn-danger"
              @click="deleteCategoryItem(editingCategory)"
            >
              Smazat
            </button>
            <div class="spacer"></div>
            <button type="button" class="btn btn-secondary" @click="showCategoryModal = false">Zavrit</button>
            <button type="submit" class="btn btn-primary" :disabled="savingCategory">
              {{ savingCategory ? 'Ukladam...' : 'Ulozit' }}
            </button>
          </div>
        </form>

        <div v-if="editingCategory" class="tiers-management">
          <div class="tiers-header">
            <h3>Cenove stupne</h3>
            <button class="btn btn-primary btn-sm" @click="openCreateTierModal">+ Pridat</button>
          </div>
          <div class="tiers-table">
            <table class="tier-table">
              <thead>
                <tr>
                  <th>Min kg</th>
                  <th>Max kg</th>
                  <th>Kc/kg</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tier in tiers" :key="tier.id">
                  <td @click="startEditCell(tier, 'min_weight')" class="editable-cell">
                    <input
                      v-if="editingCell?.tierId === tier.id && editingCell?.field === 'min_weight'"
                      v-model.number="cellEditValue"
                      type="number"
                      step="0.001"
                      class="inline-input"
                      @blur="saveCellEdit(tier)"
                      @keyup.enter="saveCellEdit(tier)"
                      @keyup.esc="cancelCellEdit"
                      autofocus
                    />
                    <span v-else>{{ tier.min_weight }}</span>
                  </td>
                  <td @click="startEditCell(tier, 'max_weight')" class="editable-cell">
                    <input
                      v-if="editingCell?.tierId === tier.id && editingCell?.field === 'max_weight'"
                      v-model.number="cellEditValue"
                      type="number"
                      step="0.001"
                      class="inline-input"
                      @blur="saveCellEdit(tier)"
                      @keyup.enter="saveCellEdit(tier)"
                      @keyup.esc="cancelCellEdit"
                      autofocus
                    />
                    <span v-else>{{ tier.max_weight ?? 'inf' }}</span>
                  </td>
                  <td @click="startEditCell(tier, 'price_per_kg')" class="editable-cell">
                    <input
                      v-if="editingCell?.tierId === tier.id && editingCell?.field === 'price_per_kg'"
                      v-model.number="cellEditValue"
                      type="number"
                      step="0.01"
                      class="inline-input"
                      @blur="saveCellEdit(tier)"
                      @keyup.enter="saveCellEdit(tier)"
                      @keyup.esc="cancelCellEdit"
                      autofocus
                    />
                    <span v-else>{{ tier.price_per_kg.toLocaleString('cs-CZ', { minimumFractionDigits: 2 }) }} Kc</span>
                  </td>
                  <td>
                    <button @click="deleteTierItem(tier)" class="icon-btn" title="Smazat">
                      <Trash2 :size="ICON_SIZE.STANDARD" />
                    </button>
                  </td>
                </tr>
                <tr v-if="showTierModal" class="new-row">
                  <td>
                    <input v-model.number="tierForm.min_weight" type="number" step="0.001" class="inline-input" />
                  </td>
                  <td>
                    <input
                      v-model.number="tierForm.max_weight"
                      type="number"
                      step="0.001"
                      class="inline-input"
                      placeholder="inf"
                    />
                  </td>
                  <td>
                    <input v-model.number="tierForm.price_per_kg" type="number" step="0.01" class="inline-input" />
                  </td>
                  <td>
                    <button @click="saveTier" class="icon-btn" title="Ulozit">
                      <CheckCircle :size="ICON_SIZE.STANDARD" />
                    </button>
                    <button @click="cancelAddTier" class="icon-btn" title="Zrusit">
                      <XCircle :size="ICON_SIZE.STANDARD" />
                    </button>
                  </td>
                </tr>
                <tr v-if="!loadingTiers && tiers.length === 0 && !showTierModal">
                  <td colspan="4" class="empty-cell">Zadne stupne</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.admin-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  padding: var(--space-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.panel-header h2 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

/* Forms */
.form-group {
  margin-bottom: var(--space-3);
}

.form-group label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Buttons */
.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-primary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-danger {
  background: var(--color-danger);
  color: white;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}

.spacer {
  flex: 1;
}

/* Combined Modal */
.combined-category-modal {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: var(--space-4);
  align-items: start;
}

.category-form-section {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.section-title {
  margin: var(--space-4) 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

h3.section-title {
  margin-top: 0;
}

.tiers-management {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.tiers-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.tiers-header h3 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
}

.tiers-table {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.tier-table {
  width: 100%;
  border-collapse: collapse;
}

.tier-table th,
.tier-table td {
  padding: var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.tier-table th {
  background: var(--bg-raised);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.editable-cell {
  cursor: text;
  transition: all var(--duration-fast);
}

.editable-cell:hover {
  background: rgba(153, 27, 27, 0.1);
}

.inline-input {
  width: 100%;
  padding: var(--space-1);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--bg-base);
  color: var(--text-primary);
}

.new-row {
  background: rgba(153, 27, 27, 0.05);
}

.empty-cell {
  text-align: center;
  color: var(--text-tertiary);
  font-style: italic;
}

.icon-btn {
  background: transparent;
  border: none;
  padding: var(--space-1);
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.icon-btn:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
</style>
