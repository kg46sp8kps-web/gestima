<script setup lang="ts">
/**
 * Parts Import Tab - Import Parts from Infor SLItems
 *
 * Default properties pre-filled: Item,FamilyCode,Description,DrawingNbr,Revision
 * Default filter: FamilyCode like 'Výrobek'
 * User can click "Načíst pole" to expand selection via InforFieldSelector.
 * "Načíst data" works immediately without fetching fields first.
 */

import { ref } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'
import { previewPartsImport, executePartsImport } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { FileText, Search, Download, Trash2, Check, X, CheckCircle, XCircle, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforFieldSelector from './InforFieldSelector.vue'
import InforDataTable from './InforDataTable.vue'
import type { StagedPartRow } from '@/types/infor'

const DEFAULT_PROPERTIES = 'Item,FamilyCode,Description,DrawingNbr,Revision,RybTridaNazev1'
const DEFAULT_FILTER = "FamilyCode LIKE 'Výrobek' AND (RybTridaNazev1 LIKE 'Nabídka' OR RybTridaNazev1 LIKE 'Aktivní')"

const props = defineProps<{ isConnected: boolean }>()

const uiStore = useUiStore()

// IDO state — properties pre-filled, ready to load immediately
const selectedIdo = ref('SLItems')
const idoProperties = ref(DEFAULT_PROPERTIES)
const idoFilter = ref(DEFAULT_FILTER)
const idoLimit = ref(100)
const inforData = ref<Record<string, unknown>[]>([])
const loading = ref(false)

// Optional field selector (only if user clicks "Načíst pole")
const availableFields = ref<Array<{ name: string; type: string; required: boolean; readOnly: boolean }>>([])
const selectedFields = ref<string[]>(DEFAULT_PROPERTIES.split(','))
const fetchingFields = ref(false)
const hideUdfFields = ref(true)
const showFieldSelector = ref(false)

// Staging state
const stagedRows = ref<StagedPartRow[]>([])
const selectedStaged = ref<StagedPartRow[]>([])
const importing = ref(false)

async function fetchFieldsForIdo() {
  if (!selectedIdo.value) {
    await alert({ title: 'Chyba', message: 'Zadejte IDO name', type: 'warning' })
    return
  }
  fetchingFields.value = true
  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/info`)
    const fields = response.data.info || []
    availableFields.value = fields.map((f: { name: string; dataType?: string; required?: boolean; readOnly?: boolean }) => ({
      name: f.name, type: f.dataType || 'String', required: f.required || false, readOnly: f.readOnly || false
    }))
    // Pre-select current properties
    const current = idoProperties.value.split(',').map(s => s.trim()).filter(Boolean)
    selectedFields.value = current.filter(name => availableFields.value.some(f => f.name === name))
    showFieldSelector.value = true
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
  if (!idoProperties.value) { uiStore.showError('Žádné sloupce k načtení'); return }
  loading.value = true
  try {
    const params: Record<string, string | number> = { properties: idoProperties.value, limit: idoLimit.value }
    if (idoFilter.value) params.filter = idoFilter.value
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
    const result = await previewPartsImport(inforData.value)
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
    const result = await executePartsImport(valid)
    uiStore.showSuccess(`Import: ${result.created_count} created, ${result.updated_count} updated`)
    stagedRows.value = []
    selectedStaged.value = []
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba importu')
  } finally {
    importing.value = false
  }
}

function toggleStaged(row: StagedPartRow) {
  const idx = selectedStaged.value.indexOf(row)
  if (idx > -1) selectedStaged.value.splice(idx, 1)
  else selectedStaged.value.push(row)
}
</script>

<template>
  <div class="import-tab">
    <!-- STEP 1: Load data -->
    <div class="section">
      <h4>1. Načíst data z Infor</h4>

      <div class="query-row">
        <div class="form-group">
          <label>IDO</label>
          <input v-model="selectedIdo" type="text" class="input" placeholder="SLItems" />
        </div>
        <div class="form-group fg-wide">
          <label>Properties</label>
          <input v-model="idoProperties" type="text" class="input" />
        </div>
        <div class="form-group">
          <label>Limit</label>
          <input v-model.number="idoLimit" type="number" class="input" />
        </div>
      </div>

      <div class="query-row">
        <div class="form-group fg-wide">
          <label>Filter (SQL WHERE)</label>
          <input v-model="idoFilter" type="text" class="input" placeholder="FamilyCode LIKE 'Výrobek'" />
        </div>
      </div>

      <div class="toolbar">
        <button @click="loadInforData" :disabled="loading || !isConnected || !idoProperties" class="btn-ghost">
          <Search :size="ICON_SIZE.STANDARD" /> {{ loading ? 'Načítám...' : 'Načíst data' }}
        </button>
        <button @click="stageAll" :disabled="inforData.length === 0 || loading" class="btn-ghost">
          <Download :size="ICON_SIZE.STANDARD" /> Stage vše ({{ inforData.length }})
        </button>
        <button @click="fetchFieldsForIdo" :disabled="fetchingFields || !selectedIdo" class="btn-ghost btn-secondary">
          <FileText :size="ICON_SIZE.STANDARD" /> {{ fetchingFields ? '...' : 'Načíst pole' }}
        </button>
      </div>

      <!-- Optional: expanded field selector -->
      <InforFieldSelector
        v-if="showFieldSelector && availableFields.length > 0"
        :available-fields="availableFields"
        :selected-fields="selectedFields"
        :hide-udf-fields="hideUdfFields"
        @toggle-field="toggleField"
        @select-all="selectAllFields"
        @deselect-all="deselectAllFields"
        @update:hide-udf-fields="hideUdfFields = $event"
      />

      <InforDataTable :data="inforData" />
    </div>

    <!-- STEP 2: Staging & Import -->
    <div class="section" v-if="stagedRows.length > 0">
      <h4>2. Review & Import</h4>
      <div class="summary">
        <span class="badge-valid"><CheckCircle :size="ICON_SIZE.SMALL" /> {{ stagedRows.filter(r => r.validation.is_valid).length }} valid</span>
        <span class="badge-error"><XCircle :size="ICON_SIZE.SMALL" /> {{ stagedRows.filter(r => !r.validation.is_valid).length }} errors</span>
        <span class="badge-dup"><AlertTriangle :size="ICON_SIZE.SMALL" /> {{ stagedRows.filter(r => r.validation.is_duplicate).length }} duplicit</span>
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
              <th>Název</th>
              <th>Výkres</th>
              <th>Revize</th>
              <th>Chyby</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in stagedRows" :key="row.row_index"
                :class="{ 'row-error': !row.validation.is_valid, 'row-dup': row.validation.is_duplicate }"
                @click="toggleStaged(row)">
              <td><input type="checkbox" :checked="selectedStaged.includes(row)" /></td>
              <td class="status-cell">
                <XCircle v-if="!row.validation.is_valid" :size="ICON_SIZE.STANDARD" class="icon-error" />
                <AlertTriangle v-else-if="row.validation.is_duplicate" :size="ICON_SIZE.STANDARD" class="icon-dup" />
                <CheckCircle v-else :size="ICON_SIZE.STANDARD" class="icon-valid" />
              </td>
              <td>{{ row.mapped_data.article_number }}</td>
              <td>{{ row.mapped_data.name }}</td>
              <td>{{ row.mapped_data.drawing_number || '-' }}</td>
              <td>{{ row.mapped_data.customer_revision || '-' }}</td>
              <td class="errors-cell">{{ row.validation.errors.join(', ') || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <button @click="executeImport" :disabled="selectedStaged.length === 0 || importing" class="btn-ghost btn-primary import-btn">
        <Download :size="ICON_SIZE.STANDARD" /> Importovat {{ selectedStaged.filter(r => r.validation.is_valid).length }} položek
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-tab { padding: var(--space-4); overflow: auto; }
.section { margin-bottom: var(--space-6); }
h4 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-3) 0; }
.query-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
.query-row .form-group { flex: 1; }
.query-row .fg-wide { flex: 3; }
.form-group label { display: block; margin-bottom: var(--space-1); font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
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
.badge-dup { padding: var(--space-1) var(--space-2); background: rgba(251, 146, 60, 0.12); color: rgb(251, 146, 60); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.table-scroll { overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); max-height: 400px; }
.staging-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.staging-table th { background: var(--bg-surface); padding: var(--space-2) var(--space-3); text-align: left; font-weight: var(--font-semibold); color: var(--text-secondary); border-bottom: 1px solid var(--border-default); position: sticky; top: 0; }
.staging-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border-subtle); }
.staging-table tbody tr { cursor: pointer; transition: background var(--duration-fast); }
.staging-table tbody tr:hover { background: var(--state-hover); }
.row-error { background: rgba(239, 68, 68, 0.08); }
.row-dup { background: rgba(251, 146, 60, 0.08); }
.status-cell { text-align: center; }
.icon-valid { color: rgb(34, 197, 94); }
.icon-error { color: rgb(239, 68, 68); }
.icon-dup { color: rgb(251, 146, 60); }
.errors-cell { max-width: 300px; color: rgb(239, 68, 68); font-size: var(--text-xs); }
</style>
