<script setup lang="ts">
/**
 * Material Groups Panel - CRUD for material groups
 * Extracted from MasterAdminModule.vue
 */

import { ref, onMounted } from 'vue'
import { confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import type { MaterialGroup, MaterialGroupCreate, MaterialGroupUpdate } from '@/types/material'
import {
  getAdminMaterialGroups,
  createMaterialGroup,
  updateMaterialGroup,
  deleteMaterialGroup
} from '@/api/materials'

const uiStore = useUiStore()

// State
const groups = ref<MaterialGroup[]>([])
const loadingGroups = ref(false)
const showGroupModal = ref(false)
const editingGroup = ref<MaterialGroup | null>(null)
const savingGroup = ref(false)

const groupForm = ref({
  code: '',
  name: '',
  density: 0,
  version: 0
})

const groupColumns: Column[] = [
  { key: 'code', label: 'Kod', sortable: true, width: '120px' },
  { key: 'name', label: 'Nazev', sortable: true },
  { key: 'density', label: 'Hustota (kg/dm3)', sortable: true, width: '180px' }
]

// Methods
async function loadGroups() {
  loadingGroups.value = true
  try {
    groups.value = await getAdminMaterialGroups()
  } catch (error) {
    uiStore.showError('Chyba pri nacitani skupin materialu')
    console.error(error)
  } finally {
    loadingGroups.value = false
  }
}

function openCreateGroupModal() {
  editingGroup.value = null
  groupForm.value = {
    code: '',
    name: '',
    density: 0,
    version: 0
  }
  showGroupModal.value = true
}

function openEditGroupModal(row: Record<string, unknown>) {
  const group = row as unknown as MaterialGroup
  editingGroup.value = group
  groupForm.value = {
    code: group.code,
    name: group.name,
    density: group.density,
    version: group.version
  }
  showGroupModal.value = true
}

async function saveGroup() {
  savingGroup.value = true
  try {
    if (editingGroup.value) {
      const updateData: MaterialGroupUpdate = {
        code: groupForm.value.code,
        name: groupForm.value.name,
        density: groupForm.value.density,
        version: groupForm.value.version
      }
      await updateMaterialGroup(editingGroup.value.id, updateData)
      uiStore.showSuccess('Skupina aktualizovana')
    } else {
      const createData: MaterialGroupCreate = {
        code: groupForm.value.code,
        name: groupForm.value.name,
        density: groupForm.value.density
      }
      await createMaterialGroup(createData)
      uiStore.showSuccess('Skupina vytvorena')
    }
    showGroupModal.value = false
    await loadGroups()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
  } finally {
    savingGroup.value = false
  }
}

async function deleteGroupItem(group: MaterialGroup) {
  const confirmed = await confirm({
    title: 'Smazat skupinu?',
    message: `Opravdu chcete smazat skupinu ${group.code} - ${group.name}?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrusit'
  })

  if (!confirmed) return

  try {
    await deleteMaterialGroup(group.id)
    uiStore.showSuccess('Skupina smazana')
    showGroupModal.value = false
    await loadGroups()
  } catch (error) {
    uiStore.showError('Chyba pri mazani skupiny')
    console.error(error)
  }
}

// Lifecycle
onMounted(() => {
  loadGroups()
})
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <h2>Skupiny materialu</h2>
      <button class="btn btn-primary" @click="openCreateGroupModal">+ Pridat skupinu</button>
    </div>

    <DataTable
      :data="groups"
      :columns="groupColumns"
      :loading="loadingGroups"
      :row-clickable="true"
      empty-text="Zadne skupiny materialu"
      @row-click="openEditGroupModal"
    />

    <Modal v-model="showGroupModal" :title="editingGroup ? 'Upravit skupinu' : 'Nova skupina'">
      <form @submit.prevent="saveGroup">
        <div class="form-group">
          <label>Kod *</label>
          <input v-model="groupForm.code" type="text" maxlength="20" required />
        </div>
        <div class="form-group">
          <label>Nazev *</label>
          <input v-model="groupForm.name" type="text" maxlength="100" required />
        </div>
        <div class="form-group">
          <label>Hustota (kg/dm3) *</label>
          <input v-model.number="groupForm.density" type="number" step="0.001" min="0" required />
        </div>
        <div class="form-actions">
          <button v-if="editingGroup" type="button" class="btn btn-danger" @click="deleteGroupItem(editingGroup)">
            Smazat
          </button>
          <div class="spacer"></div>
          <button type="button" class="btn btn-secondary" @click="showGroupModal = false">Zrusit</button>
          <button type="submit" class="btn btn-primary" :disabled="savingGroup">
            {{ savingGroup ? 'Ukladam...' : 'Ulozit' }}
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
