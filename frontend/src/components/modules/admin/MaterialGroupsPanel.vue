<script setup lang="ts">
/**
 * Material Groups Panel - CRUD for material groups
 * Extracted from MasterAdminModule.vue
 */

import { ref, onMounted, computed } from 'vue'
import { confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import MaterialGroupBasicForm from './MaterialGroupBasicForm.vue'
import MaterialGroupCuttingParamsForm from './MaterialGroupCuttingParamsForm.vue'
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
const activeFormTab = ref<'basic' | 'cutting'>('basic')

const groupForm = ref({
  code: '',
  name: '',
  density: 0,
  version: 0,
  iso_group: null as string | null,
  hardness_hb: null as number | null,
  mrr_turning_roughing: null as number | null,
  mrr_turning_finishing: null as number | null,
  mrr_milling_roughing: null as number | null,
  mrr_milling_finishing: null as number | null,
  cutting_speed_turning: null as number | null,
  cutting_speed_milling: null as number | null,
  feed_turning: null as number | null,
  feed_milling: null as number | null,
  deep_pocket_penalty: 1.8,
  thin_wall_penalty: 2.5,
  cutting_data_source: null as string | null
})

const groupColumns: Column[] = [
  { key: 'code', label: 'Kod', sortable: true, width: '120px' },
  { key: 'name', label: 'Nazev', sortable: true },
  { key: 'iso_group', label: 'ISO', sortable: true, width: '80px' },
  { key: 'density', label: 'Hustota', sortable: true, width: '120px' },
  { key: 'mrr_milling_roughing', label: 'MRR Freza', sortable: true, width: '120px' },
  { key: 'cutting_speed_milling', label: 'Vc (m/min)', sortable: true, width: '120px' }
]

// Computed bindings for sub-forms
const basicFields = computed({
  get: () => ({ code: groupForm.value.code, name: groupForm.value.name, density: groupForm.value.density }),
  set: (v) => { groupForm.value.code = v.code; groupForm.value.name = v.name; groupForm.value.density = v.density }
})

const cuttingParams = computed({
  get: () => ({
    iso_group: groupForm.value.iso_group,
    hardness_hb: groupForm.value.hardness_hb,
    mrr_turning_roughing: groupForm.value.mrr_turning_roughing,
    mrr_turning_finishing: groupForm.value.mrr_turning_finishing,
    mrr_milling_roughing: groupForm.value.mrr_milling_roughing,
    mrr_milling_finishing: groupForm.value.mrr_milling_finishing,
    cutting_speed_turning: groupForm.value.cutting_speed_turning,
    cutting_speed_milling: groupForm.value.cutting_speed_milling,
    feed_turning: groupForm.value.feed_turning,
    feed_milling: groupForm.value.feed_milling,
    deep_pocket_penalty: groupForm.value.deep_pocket_penalty,
    thin_wall_penalty: groupForm.value.thin_wall_penalty,
    cutting_data_source: groupForm.value.cutting_data_source
  }),
  set: (v) => Object.assign(groupForm.value, v)
})

async function loadGroups() {
  loadingGroups.value = true
  try {
    groups.value = await getAdminMaterialGroups()
  } catch (error) {
    uiStore.showError('Chyba pri nacitani skupin materialu')
  } finally {
    loadingGroups.value = false
  }
}

function openCreateGroupModal() {
  editingGroup.value = null
  groupForm.value = {
    code: '', name: '', density: 0, version: 0,
    iso_group: null, hardness_hb: null, mrr_turning_roughing: null,
    mrr_turning_finishing: null, mrr_milling_roughing: null, mrr_milling_finishing: null,
    cutting_speed_turning: null, cutting_speed_milling: null, feed_turning: null,
    feed_milling: null, deep_pocket_penalty: 1.8, thin_wall_penalty: 2.5,
    cutting_data_source: null
  }
  activeFormTab.value = 'basic'
  showGroupModal.value = true
}

function openEditGroupModal(row: Record<string, unknown>) {
  const g = row as unknown as MaterialGroup
  editingGroup.value = g
  groupForm.value = {
    code: g.code, name: g.name, density: g.density, version: g.version,
    iso_group: g.iso_group ?? null, hardness_hb: g.hardness_hb ?? null,
    mrr_turning_roughing: g.mrr_turning_roughing ?? null,
    mrr_turning_finishing: g.mrr_turning_finishing ?? null,
    mrr_milling_roughing: g.mrr_milling_roughing ?? null,
    mrr_milling_finishing: g.mrr_milling_finishing ?? null,
    cutting_speed_turning: g.cutting_speed_turning ?? null,
    cutting_speed_milling: g.cutting_speed_milling ?? null,
    feed_turning: g.feed_turning ?? null, feed_milling: g.feed_milling ?? null,
    deep_pocket_penalty: g.deep_pocket_penalty ?? 1.8,
    thin_wall_penalty: g.thin_wall_penalty ?? 2.5,
    cutting_data_source: g.cutting_data_source ?? null
  }
  activeFormTab.value = 'basic'
  showGroupModal.value = true
}

async function saveGroup() {
  savingGroup.value = true
  try {
    if (editingGroup.value) {
      const updateData: MaterialGroupUpdate = { ...groupForm.value, version: groupForm.value.version }
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
    uiStore.showError(error instanceof Error ? error.message : 'Chyba pri ukladani')
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
  }
}

onMounted(() => { loadGroups() })
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

    <Modal v-model="showGroupModal" :title="editingGroup ? 'Upravit skupinu' : 'Nova skupina'" size="xl">
      <form @submit.prevent="saveGroup">
        <div class="form-tabs">
          <button type="button" @click="activeFormTab = 'basic'" :class="{ active: activeFormTab === 'basic' }">
            Zakladni
          </button>
          <button type="button" @click="activeFormTab = 'cutting'" :class="{ active: activeFormTab === 'cutting' }">
            Rezne podminky
          </button>
        </div>

        <div v-show="activeFormTab === 'basic'">
          <MaterialGroupBasicForm v-model="basicFields" />
        </div>

        <div v-show="activeFormTab === 'cutting'">
          <MaterialGroupCuttingParamsForm v-model="cuttingParams" />
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
  border: 1px solid var(--border-default);
}

.panel-header h2 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.form-tabs {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.form-tabs button {
  padding: var(--space-2) var(--space-4);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.form-tabs button.active {
  color: var(--color-info);
  border-bottom-color: var(--color-info);
}

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
</style>
