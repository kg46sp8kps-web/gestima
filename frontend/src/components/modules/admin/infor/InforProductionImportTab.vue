<script setup lang="ts">
/**
 * Production Import Tab - Import ProductionRecords from Infor SLJobRoutes
 *
 * Same IDO browser pattern: Fetch Fields → Select → Load → Stage → Import
 */

import { ref } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'
import { previewProductionImport, executeProductionImport } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { FileText, Search, Download, Trash2, Check, X, CheckCircle, XCircle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforFieldSelector from './InforFieldSelector.vue'
import InforQueryForm from './InforQueryForm.vue'
import InforDataTable from './InforDataTable.vue'
import type { StagedProductionRow } from '@/types/infor'

const props = defineProps<{ isConnected: boolean }>()

const uiStore = useUiStore()

// IDO browser state
const selectedIdo = ref('SLJobRoutes')
const idoProperties = ref('')
const idoFilter = ref('')
const idoOrderBy = ref('')
const idoLimit = ref(100)
const availableFields = ref<Array<{ name: string; type: string; required: boolean; readOnly: boolean }>>([])
const selectedFields = ref<string[]>([])
const fetchingFields = ref(false)
const hideUdfFields = ref(true)
const inforData = ref<Record<string, unknown>[]>([])
const loading = ref(false)

// Staging state
const stagedRows = ref<StagedProductionRow[]>([])
const selectedStaged = ref<StagedProductionRow[]>([])
const importing = ref(false)

async function fetchFieldsForIdo() {
  if (!selectedIdo.value) { await alert({ title: 'Chyba', message: 'Zadejte IDO name', type: 'warning' }); return }
  fetchingFields.value = true
  availableFields.value = []
  selectedFields.value = []
  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/info`)
    const fields = response.data.info || []
    availableFields.value = fields.map((f: { name: string; dataType?: string; required?: boolean; readOnly?: boolean }) => ({
      name: f.name, type: f.dataType || 'String', required: f.required || false, readOnly: f.readOnly || false
    }))
    const hints = ['Job', 'Item', 'OperNum', 'Wc', 'Qty', 'RunHrs', 'ActRunHrs', 'Complete']
    selectedFields.value = availableFields.value.filter(f => hints.some(h => f.name.includes(h))).map(f => f.name).slice(0, 10)
    idoProperties.value = selectedFields.value.join(',')
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    await alert({ title: 'Chyba', message: 'Nepodařilo se načíst pole: ' + (err.response?.data?.detail || err.message), type: 'error' })
  } finally {
    fetchingFields.value = false
  }
}

function toggleField(fieldName: string) {
  const idx = selectedFields.value.indexOf(fieldName)
  if (idx > -1) selectedFields.value.splice(idx, 1)
  else selectedFields.value.push(fieldName)
  idoProperties.value = selectedFields.value.join(',')
}

function selectAllFields() {
  selectedFields.value = availableFields.value.map(f => f.name)
  idoProperties.value = selectedFields.value.join(',')
}

function deselectAllFields() {
  selectedFields.value = []
  idoProperties.value = ''
}

async function loadInforData() {
  if (!props.isConnected) { uiStore.showError('Nejste připojeni k Infor ION API'); return }
  if (!idoProperties.value) { uiStore.showError('Vyberte alespoň jeden sloupec'); return }
  loading.value = true
  try {
    const params: Record<string, string | number> = { properties: idoProperties.value, limit: idoLimit.value }
    if (idoFilter.value) params.filter = idoFilter.value
    if (idoOrderBy.value) params.order_by = idoOrderBy.value
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/data`, { params })
    inforData.value = response.data.data || []
    uiStore.showSuccess(`Načteno ${inforData.value.length} řádků`)
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    uiStore.showError(err.response?.data?.detail || err.message || 'Chyba načtení dat')
  } finally {
    loading.value = false
  }
}

async function stageAll() {
  if (inforData.value.length === 0) { uiStore.showError('Žádná data k zobrazení'); return }
  loading.value = true
  try {
    const result = await previewProductionImport(inforData.value)
    stagedRows.value = result.rows
    uiStore.showSuccess(`Staged: ${result.valid_count} valid, ${result.error_count} errors`)
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba preview')
  } finally {
    loading.value = false
  }
}

async function executeImport() {
  const valid = selectedStaged.value.filter(r => r.validation.is_valid)
  if (valid.length === 0) { uiStore.showError('Žádné validní řádky k importu'); return }
  importing.value = true
  try {
    const result = await executeProductionImport(valid)
    uiStore.showSuccess(`Import: ${result.created_count} created`)
    stagedRows.value = []
    selectedStaged.value = []
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba importu')
  } finally {
    importing.value = false
  }
}

function toggleStaged(row: StagedProductionRow) {
  const idx = selectedStaged.value.indexOf(row)
  if (idx > -1) selectedStaged.value.splice(idx, 1)
  else selectedStaged.value.push(row)
}
</script>

<template>
  <div class="import-tab">
    <!-- STEP 1: IDO Browser -->
    <div class="section">
      <h4>1. Načíst data z Infor</h4>
      <div class="ido-row">
        <div class="form-group">
          <label>IDO Name <span class="case-warning">(case-sensitive)</span></label>
          <div class="input-with-button">
            <input v-model="selectedIdo" type="text" class="input" placeholder="SLJobRoutes" />
            <button @click="fetchFieldsForIdo" :disabled="fetchingFields || !selectedIdo" class="btn-ghost">
              <FileText :size="ICON_SIZE.STANDARD" /> {{ fetchingFields ? 'Načítám...' : 'Načíst pole' }}
            </button>
          </div>
        </div>
      </div>

      <InforFieldSelector
        v-if="availableFields.length > 0"
        :available-fields="availableFields"
        :selected-fields="selectedFields"
        :hide-udf-fields="hideUdfFields"
        @toggle-field="toggleField"
        @select-all="selectAllFields"
        @deselect-all="deselectAllFields"
        @update:hide-udf-fields="hideUdfFields = $event"
      />

      <InforQueryForm
        v-if="availableFields.length > 0"
        :properties="idoProperties"
        :filter="idoFilter"
        :order-by="idoOrderBy"
        :limit="idoLimit"
        @update:properties="idoProperties = $event"
        @update:filter="idoFilter = $event"
        @update:order-by="idoOrderBy = $event"
        @update:limit="idoLimit = $event"
      />

      <div class="toolbar" v-if="availableFields.length > 0">
        <button @click="loadInforData" :disabled="loading || !isConnected || !idoProperties" class="btn-ghost">
          <Search :size="ICON_SIZE.STANDARD" /> {{ loading ? 'Načítám...' : 'Načíst data' }}
        </button>
        <button @click="stageAll" :disabled="inforData.length === 0 || loading" class="btn-ghost">
          <Download :size="ICON_SIZE.STANDARD" /> Stage vše ({{ inforData.length }})
        </button>
      </div>

      <InforDataTable :data="inforData" />
    </div>

    <!-- STEP 2: Staging & Import -->
    <div class="section" v-if="stagedRows.length > 0">
      <h4>2. Review & Import</h4>
      <div class="summary">
        <span class="badge-valid"><CheckCircle :size="ICON_SIZE.SMALL" /> {{ stagedRows.filter(r => r.validation.is_valid).length }} valid</span>
        <span class="badge-error"><XCircle :size="ICON_SIZE.SMALL" /> {{ stagedRows.filter(r => !r.validation.is_valid).length }} errors</span>
      </div>
      <div class="toolbar">
        <button @click="selectedStaged = [...stagedRows]" class="btn-ghost"><Check :size="ICON_SIZE.STANDARD" /> Vybrat vše</button>
        <button @click="selectedStaged = []" class="btn-ghost"><X :size="ICON_SIZE.STANDARD" /> Zrušit výběr</button>
        <button @click="stagedRows = []; selectedStaged = []" class="btn-ghost btn-danger"><Trash2 :size="ICON_SIZE.STANDARD" /> Vymazat</button>
      </div>
      <div class="table-scroll">
        <table class="staging-table">
          <thead>
            <tr>
              <th>☑</th>
              <th>Status</th>
              <th>Article #</th>
              <th>Zakázka</th>
              <th>Op</th>
              <th>Ks</th>
              <th>Plán (min)</th>
              <th>Real (min)</th>
              <th>WC</th>
              <th>Chyby</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in stagedRows" :key="row.row_index"
                :class="{ 'row-error': !row.validation.is_valid }"
                @click="toggleStaged(row)">
              <td><input type="checkbox" :checked="selectedStaged.includes(row)" /></td>
              <td class="status-cell">
                <XCircle v-if="!row.validation.is_valid" :size="ICON_SIZE.STANDARD" class="icon-error" />
                <CheckCircle v-else :size="ICON_SIZE.STANDARD" class="icon-valid" />
              </td>
              <td>{{ row.mapped_data.article_number }}</td>
              <td>{{ row.mapped_data.infor_order_number }}</td>
              <td>{{ row.mapped_data.operation_seq }}</td>
              <td>{{ row.mapped_data.batch_quantity || '-' }}</td>
              <td>{{ row.mapped_data.planned_time_min || '-' }}</td>
              <td>{{ row.mapped_data.actual_time_min || '-' }}</td>
              <td>{{ row.mapped_data.infor_wc_code || '-' }}</td>
              <td class="errors-cell">{{ row.validation.errors.join(', ') || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <button @click="executeImport" :disabled="selectedStaged.length === 0 || importing" class="btn-ghost btn-primary import-btn">
        <Download :size="ICON_SIZE.STANDARD" /> Importovat {{ selectedStaged.filter(r => r.validation.is_valid).length }} záznamů
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-tab { padding: var(--space-4); overflow: auto; }
.section { margin-bottom: var(--space-6); }
h4 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-3) 0; }
.ido-row { margin-bottom: var(--space-3); }
.form-group label { display: block; margin-bottom: var(--space-1); font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
.case-warning { color: var(--color-primary); font-size: var(--text-xs); font-weight: 600; }
.input-with-button { display: flex; gap: var(--space-2); }
.input-with-button .input { flex: 1; }
.input { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-default); background: var(--bg-base); color: var(--text-primary); border-radius: var(--radius-md); font-size: var(--text-sm); }
.input:focus { outline: none; border-color: var(--color-brand); }
.toolbar { display: flex; gap: var(--space-2); margin: var(--space-3) 0; flex-wrap: wrap; }
.btn-ghost { display: inline-flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border: 1px solid var(--border-default); background: transparent; color: var(--text-primary); border-radius: var(--radius-md); font-size: var(--text-sm); cursor: pointer; transition: all var(--duration-fast); }
.btn-ghost:hover:not(:disabled) { background: var(--state-hover); border-color: var(--border-strong); }
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost.btn-primary { color: var(--color-brand); border-color: var(--color-brand); }
.btn-ghost.btn-danger { color: var(--color-danger); border-color: var(--color-danger); }
.import-btn { margin-top: var(--space-3); }
.summary { display: flex; gap: var(--space-3); margin-bottom: var(--space-2); }
.badge-valid { padding: var(--space-1) var(--space-2); background: rgba(34, 197, 94, 0.12); color: rgb(34, 197, 94); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.badge-error { padding: var(--space-1) var(--space-2); background: rgba(239, 68, 68, 0.12); color: rgb(239, 68, 68); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.table-scroll { overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); max-height: 400px; }
.staging-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.staging-table th { background: var(--bg-surface); padding: var(--space-2) var(--space-3); text-align: left; font-weight: var(--font-semibold); color: var(--text-secondary); border-bottom: 1px solid var(--border-default); position: sticky; top: 0; }
.staging-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border-subtle); }
.staging-table tbody tr { cursor: pointer; transition: background var(--duration-fast); }
.staging-table tbody tr:hover { background: var(--state-hover); }
.row-error { background: rgba(239, 68, 68, 0.08); }
.status-cell { text-align: center; }
.icon-valid { color: rgb(34, 197, 94); }
.icon-error { color: rgb(239, 68, 68); }
.errors-cell { max-width: 200px; color: rgb(239, 68, 68); font-size: var(--text-xs); }
</style>
