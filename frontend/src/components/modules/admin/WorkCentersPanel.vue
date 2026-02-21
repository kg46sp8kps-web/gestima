<script setup lang="ts">
/**
 * Work Centers Panel - CRUD for work centers
 * Extracted from MasterAdminModule.vue
 */

import { ref, computed, onMounted } from 'vue'
import { confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import { useOperationsStore } from '@/stores/operations'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import type { WorkCenter, WorkCenterCreate, WorkCenterUpdate, WorkCenterType } from '@/types/operation'

const uiStore = useUiStore()
const operationsStore = useOperationsStore()

// State
const showWorkCenterModal = ref(false)
const editingWorkCenter = ref<WorkCenter | null>(null)
const savingWorkCenter = ref(false)
const loadingWorkCenters = ref(false)
const workCenters = computed(() => operationsStore.workCenters)

const workCenterForm = ref({
  name: '',
  work_center_type: 'CNC_LATHE' as WorkCenterType,
  subtype: null as string | null,
  hourly_rate_amortization: null as number | null,
  hourly_rate_labor: null as number | null,
  hourly_rate_tools: null as number | null,
  hourly_rate_overhead: null as number | null,
  has_bar_feeder: false,
  has_sub_spindle: false,
  has_milling: false,
  suitable_for_series: true,
  suitable_for_single: true,
  setup_base_min: 0,
  setup_per_tool_min: 0,
  is_active: true,
  priority: 1,
  notes: null as string | null,
  version: 0
})

const workCenterColumns: Column[] = [
  { key: 'work_center_number', label: 'Cislo', sortable: true, width: '120px' },
  { key: 'name', label: 'Nazev', sortable: true },
  { key: 'work_center_type', label: 'Typ', sortable: true, width: '150px' },
  { key: 'hourly_rate_total', label: 'Hodinova sazba', format: 'currency', width: '150px' },
  { key: 'is_active', label: 'Aktivni', format: 'boolean', width: '100px' }
]

// Methods
async function loadWorkCenters() {
  loadingWorkCenters.value = true
  try {
    await operationsStore.loadWorkCenters()
  } finally {
    loadingWorkCenters.value = false
  }
}

function openCreateWorkCenterModal() {
  editingWorkCenter.value = null
  workCenterForm.value = {
    name: '',
    work_center_type: 'CNC_LATHE' as WorkCenterType,
    subtype: null,
    hourly_rate_amortization: null,
    hourly_rate_labor: null,
    hourly_rate_tools: null,
    hourly_rate_overhead: null,
    has_bar_feeder: false,
    has_sub_spindle: false,
    has_milling: false,
    suitable_for_series: true,
    suitable_for_single: true,
    setup_base_min: 0,
    setup_per_tool_min: 0,
    is_active: true,
    priority: 1,
    notes: null,
    version: 0
  }
  showWorkCenterModal.value = true
}

function openEditWorkCenterModal(row: Record<string, unknown>) {
  const wc = row as unknown as WorkCenter
  editingWorkCenter.value = wc
  workCenterForm.value = {
    name: wc.name,
    work_center_type: wc.work_center_type,
    subtype: wc.subtype ?? null,
    hourly_rate_amortization: wc.hourly_rate_amortization ?? null,
    hourly_rate_labor: wc.hourly_rate_labor ?? null,
    hourly_rate_tools: wc.hourly_rate_tools ?? null,
    hourly_rate_overhead: wc.hourly_rate_overhead ?? null,
    has_bar_feeder: wc.has_bar_feeder,
    has_sub_spindle: wc.has_sub_spindle,
    has_milling: wc.has_milling,
    suitable_for_series: wc.suitable_for_series,
    suitable_for_single: wc.suitable_for_single,
    setup_base_min: wc.setup_base_min,
    setup_per_tool_min: wc.setup_per_tool_min,
    is_active: wc.is_active,
    priority: wc.priority,
    notes: wc.notes ?? null,
    version: wc.version
  }
  showWorkCenterModal.value = true
}

async function saveWorkCenter() {
  savingWorkCenter.value = true
  try {
    if (editingWorkCenter.value) {
      const updateData: WorkCenterUpdate = {
        name: workCenterForm.value.name,
        work_center_type: workCenterForm.value.work_center_type,
        subtype: workCenterForm.value.subtype,
        hourly_rate_amortization: workCenterForm.value.hourly_rate_amortization,
        hourly_rate_labor: workCenterForm.value.hourly_rate_labor,
        hourly_rate_tools: workCenterForm.value.hourly_rate_tools,
        hourly_rate_overhead: workCenterForm.value.hourly_rate_overhead,
        has_bar_feeder: workCenterForm.value.has_bar_feeder,
        has_sub_spindle: workCenterForm.value.has_sub_spindle,
        has_milling: workCenterForm.value.has_milling,
        suitable_for_series: workCenterForm.value.suitable_for_series,
        suitable_for_single: workCenterForm.value.suitable_for_single,
        setup_base_min: workCenterForm.value.setup_base_min,
        setup_per_tool_min: workCenterForm.value.setup_per_tool_min,
        is_active: workCenterForm.value.is_active,
        priority: workCenterForm.value.priority,
        notes: workCenterForm.value.notes,
        version: workCenterForm.value.version
      }
      await operationsStore.updateWorkCenter(editingWorkCenter.value.work_center_number, updateData)
      uiStore.showSuccess('Pracoviste aktualizovano')
    } else {
      const createData: WorkCenterCreate = {
        name: workCenterForm.value.name,
        work_center_type: workCenterForm.value.work_center_type,
        subtype: workCenterForm.value.subtype,
        hourly_rate_amortization: workCenterForm.value.hourly_rate_amortization,
        hourly_rate_labor: workCenterForm.value.hourly_rate_labor,
        hourly_rate_tools: workCenterForm.value.hourly_rate_tools,
        hourly_rate_overhead: workCenterForm.value.hourly_rate_overhead,
        has_bar_feeder: workCenterForm.value.has_bar_feeder,
        has_sub_spindle: workCenterForm.value.has_sub_spindle,
        has_milling: workCenterForm.value.has_milling,
        suitable_for_series: workCenterForm.value.suitable_for_series,
        suitable_for_single: workCenterForm.value.suitable_for_single,
        setup_base_min: workCenterForm.value.setup_base_min,
        setup_per_tool_min: workCenterForm.value.setup_per_tool_min,
        is_active: workCenterForm.value.is_active,
        priority: workCenterForm.value.priority,
        notes: workCenterForm.value.notes
      }
      await operationsStore.createWorkCenter(createData)
      uiStore.showSuccess('Pracoviste vytvoreno')
    }
    showWorkCenterModal.value = false
    await loadWorkCenters()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba pri ukladani'
    uiStore.showError(message)
  } finally {
    savingWorkCenter.value = false
  }
}

async function deleteWorkCenterItem(wc: WorkCenter) {
  const confirmed = await confirm({
    title: 'Smazat pracoviste?',
    message: `Opravdu chcete smazat pracoviste ${wc.work_center_number} - ${wc.name}?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrusit'
  })

  if (!confirmed) return

  try {
    await operationsStore.deleteWorkCenter(wc.work_center_number)
    uiStore.showSuccess('Pracoviste smazano')
    showWorkCenterModal.value = false
    await loadWorkCenters()
  } catch (error) {
    uiStore.showError('Chyba pri mazani pracoviste')
    console.error(error)
  }
}

// Lifecycle
onMounted(() => {
  loadWorkCenters()
})
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <h2>Pracoviste</h2>
      <button class="btn btn-primary" @click="openCreateWorkCenterModal">+ Pridat pracoviste</button>
    </div>

    <DataTable
      :data="workCenters"
      :columns="workCenterColumns"
      :loading="loadingWorkCenters"
      :row-clickable="true"
      empty-text="Zadna pracoviste"
      @row-click="openEditWorkCenterModal"
    />

    <Modal
      v-model="showWorkCenterModal"
      :title="editingWorkCenter ? 'Upravit pracoviste' : 'Nove pracoviste'"
      size="lg"
    >
      <form @submit.prevent="saveWorkCenter">
        <div class="form-group">
          <label>Nazev *</label>
          <input v-model="workCenterForm.name" type="text" maxlength="200" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Typ pracoviste *</label>
            <select v-model="workCenterForm.work_center_type" required>
              <option value="CNC_LATHE">CNC Soustruh</option>
              <option value="CNC_MILL_3AX">CNC Frezka 3-osa</option>
              <option value="CNC_MILL_4AX">CNC Frezka 4-osa</option>
              <option value="CNC_MILL_5AX">CNC Frezka 5-osa</option>
              <option value="SAW">Pila</option>
              <option value="DRILL">Vrtacka</option>
              <option value="QUALITY_CONTROL">Kontrola kvality</option>
              <option value="MANUAL_ASSEMBLY">Rucni montaz</option>
              <option value="EXTERNAL">Externi</option>
            </select>
          </div>
          <div class="form-group">
            <label>Podtyp</label>
            <input v-model="workCenterForm.subtype" type="text" maxlength="50" />
          </div>
        </div>

        <h4 class="section-title">Hodinove sazby (Kc/hod)</h4>
        <div class="form-row">
          <div class="form-group">
            <label>Odpisy</label>
            <input v-model.number="workCenterForm.hourly_rate_amortization" type="number" step="0.01" min="0" />
          </div>
          <div class="form-group">
            <label>Mzdy</label>
            <input v-model.number="workCenterForm.hourly_rate_labor" type="number" step="0.01" min="0" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Nastroje</label>
            <input v-model.number="workCenterForm.hourly_rate_tools" type="number" step="0.01" min="0" />
          </div>
          <div class="form-group">
            <label>Rezie</label>
            <input v-model.number="workCenterForm.hourly_rate_overhead" type="number" step="0.01" min="0" />
          </div>
        </div>

        <h4 class="section-title">Serizovaci casy</h4>
        <div class="form-row">
          <div class="form-group">
            <label>Zakladni serizeni (min) *</label>
            <input v-model.number="workCenterForm.setup_base_min" type="number" step="1" min="0" required />
          </div>
          <div class="form-group">
            <label>Cas na nastroj (min) *</label>
            <input v-model.number="workCenterForm.setup_per_tool_min" type="number" step="1" min="0" required />
          </div>
        </div>

        <h4 class="section-title">Vybaveni</h4>
        <div class="form-row">
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.has_bar_feeder" type="checkbox" />
              Podavac tyci
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.has_sub_spindle" type="checkbox" />
              Protivreteno
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.has_milling" type="checkbox" />
              Frezovani
            </label>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.suitable_for_series" type="checkbox" />
              Vhodne pro serii
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.suitable_for_single" type="checkbox" />
              Vhodne pro kusovku
            </label>
          </div>
        </div>

        <h4 class="section-title">Stav</h4>
        <div class="form-row">
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="workCenterForm.is_active" type="checkbox" />
              Aktivni
            </label>
          </div>
          <div class="form-group">
            <label>Priorita *</label>
            <input v-model.number="workCenterForm.priority" type="number" step="1" min="1" max="99" required />
          </div>
        </div>
        <div class="form-group">
          <label>Poznamky</label>
          <textarea v-model="workCenterForm.notes" rows="3"></textarea>
        </div>

        <div class="form-actions">
          <button
            v-if="editingWorkCenter"
            type="button"
            class="btn btn-danger"
            @click="deleteWorkCenterItem(editingWorkCenter)"
          >
            Smazat
          </button>
          <div class="spacer"></div>
          <button type="button" class="btn btn-secondary" @click="showWorkCenterModal = false">Zrusit</button>
          <button type="submit" class="btn btn-primary" :disabled="savingWorkCenter">
            {{ savingWorkCenter ? 'Ukladam...' : 'Ulozit' }}
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

/* Forms */
.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.section-title {
  margin: var(--space-4) 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-label input[type='checkbox'] {
  width: auto;
  cursor: pointer;
}

/* Buttons */

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
</style>
