<script setup lang="ts">
/**
 * Material Norms Panel - CRUD for material norms
 * Extracted from MasterAdminModule.vue
 */

import { ref, onMounted } from 'vue'
import { alert, confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import type { MaterialNorm, MaterialNormCreate, MaterialNormUpdate, MaterialGroup } from '@/types/material'
import {
  getMaterialNorms,
  createMaterialNorm,
  updateMaterialNorm,
  deleteMaterialNorm,
  getAdminMaterialGroups
} from '@/api/materials'

const uiStore = useUiStore()

// State
const norms = ref<MaterialNorm[]>([])
const groups = ref<MaterialGroup[]>([])
const loadingNorms = ref(false)
const showNormModal = ref(false)
const editingNorm = ref<MaterialNorm | null>(null)
const savingNorm = ref(false)

const normForm = ref({
  w_nr: '',
  en_iso: '',
  csn: '',
  aisi: '',
  material_group_id: 0,
  note: '',
  version: 0
})

const normColumns: Column[] = [
  { key: 'w_nr', label: 'W.Nr', sortable: true, width: '120px' },
  { key: 'en_iso', label: 'EN ISO', sortable: true, width: '120px' },
  { key: 'csn', label: 'CSN', sortable: true, width: '100px' },
  { key: 'aisi', label: 'AISI', sortable: true, width: '100px' },
  { key: 'material_group.name', label: 'Skupina', sortable: true },
  { key: 'note', label: 'Poznamka', sortable: false }
]

// Methods
async function loadGroups() {
  try {
    groups.value = await getAdminMaterialGroups()
  } catch (error) {
    console.error('Failed to load groups:', error)
  }
}

async function loadNorms() {
  loadingNorms.value = true
  try {
    norms.value = await getMaterialNorms()
  } catch (error) {
    uiStore.showError('Chyba pri nacitani norem')
    console.error(error)
  } finally {
    loadingNorms.value = false
  }
}

function openCreateNormModal() {
  editingNorm.value = null
  normForm.value = {
    w_nr: '',
    en_iso: '',
    csn: '',
    aisi: '',
    material_group_id: groups.value[0]?.id || 0,
    note: '',
    version: 0
  }
  showNormModal.value = true
}

function openEditNormModal(row: Record<string, unknown>) {
  const norm = row as unknown as MaterialNorm
  editingNorm.value = norm
  normForm.value = {
    w_nr: norm.w_nr || '',
    en_iso: norm.en_iso || '',
    csn: norm.csn || '',
    aisi: norm.aisi || '',
    material_group_id: norm.material_group_id,
    note: norm.note || '',
    version: norm.version
  }
  showNormModal.value = true
}

async function saveNorm() {
  savingNorm.value = true
  try {
    if (editingNorm.value) {
      const updateData: MaterialNormUpdate = {
        w_nr: normForm.value.w_nr || null,
        en_iso: normForm.value.en_iso || null,
        csn: normForm.value.csn || null,
        aisi: normForm.value.aisi || null,
        material_group_id: normForm.value.material_group_id,
        note: normForm.value.note || null,
        version: normForm.value.version
      }
      await updateMaterialNorm(editingNorm.value.id, updateData)
      uiStore.showSuccess('Norma aktualizovana')
    } else {
      const createData: MaterialNormCreate = {
        w_nr: normForm.value.w_nr || null,
        en_iso: normForm.value.en_iso || null,
        csn: normForm.value.csn || null,
        aisi: normForm.value.aisi || null,
        material_group_id: normForm.value.material_group_id,
        note: normForm.value.note || null
      }
      await createMaterialNorm(createData)
      uiStore.showSuccess('Norma vytvorena')
    }
    showNormModal.value = false
    await loadNorms()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
  } finally {
    savingNorm.value = false
  }
}

async function deleteNormItem(norm: MaterialNorm) {
  const normName = norm.w_nr || norm.en_iso || norm.csn || norm.aisi
  const confirmed = await confirm({
    title: 'Smazat normu?',
    message: `Opravdu chcete smazat normu ${normName}?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrusit'
  })

  if (!confirmed) return

  try {
    await deleteMaterialNorm(norm.id)
    uiStore.showSuccess('Norma smazana')
    showNormModal.value = false
    await loadNorms()
  } catch (error) {
    uiStore.showError('Chyba pri mazani normy')
    console.error(error)
  }
}

// Lifecycle
onMounted(async () => {
  await loadGroups()
  await loadNorms()
})
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <h2>Normy materialu</h2>
      <button class="btn btn-primary" @click="openCreateNormModal">+ Pridat normu</button>
    </div>

    <DataTable
      :data="norms"
      :columns="normColumns"
      :loading="loadingNorms"
      :row-clickable="true"
      empty-text="Zadne normy materialu"
      @row-click="openEditNormModal"
    />

    <Modal v-model="showNormModal" :title="editingNorm ? 'Upravit normu' : 'Nova norma'">
      <form @submit.prevent="saveNorm">
        <div class="form-group">
          <label>Skupina materialu *</label>
          <select v-model="normForm.material_group_id" required>
            <option v-for="group in groups" :key="group.id" :value="group.id">
              {{ group.code }} - {{ group.name }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>W.Nr</label>
            <input v-model="normForm.w_nr" type="text" maxlength="50" />
          </div>
          <div class="form-group">
            <label>EN ISO</label>
            <input v-model="normForm.en_iso" type="text" maxlength="50" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>CSN</label>
            <input v-model="normForm.csn" type="text" maxlength="50" />
          </div>
          <div class="form-group">
            <label>AISI</label>
            <input v-model="normForm.aisi" type="text" maxlength="50" />
          </div>
        </div>
        <div class="form-group">
          <label>Poznamka</label>
          <textarea v-model="normForm.note" rows="3"></textarea>
        </div>
        <div class="form-actions">
          <button v-if="editingNorm" type="button" class="btn btn-danger" @click="deleteNormItem(editingNorm)">
            Smazat
          </button>
          <div class="spacer"></div>
          <button type="button" class="btn btn-secondary" @click="showNormModal = false">Zrusit</button>
          <button type="submit" class="btn btn-primary" :disabled="savingNorm">
            {{ savingNorm ? 'Ukladam...' : 'Ulozit' }}
          </button>
        </div>
      </form>
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
  border: 1px solid var(--border-color);
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

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-color);
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
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-danger {
  background: var(--color-danger);
  color: white;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.spacer {
  flex: 1;
}
</style>
