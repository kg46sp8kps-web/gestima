<script setup lang="ts">
/**
 * Production Import Tab - Import ProductionRecords from Infor SLJobRoutes
 *
 * Default properties pre-filled, ready to load immediately.
 * Virtual scroll for 200k+ rows — only renders visible rows.
 * Set-based selection for O(1) checks at scale.
 */

import { ref, computed } from 'vue'
import { alert } from '@/composables/useDialog'
import { previewProductionImport, executeProductionImport, getInforIdoInfo, getInforIdoData, type InforIdoDataParams } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { FileText, Search, Download, Trash2, Check, X, CheckCircle, XCircle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforFieldSelector from './InforFieldSelector.vue'
import InforDataTable from './InforDataTable.vue'
import type { StagedProductionRow } from '@/types/infor'

const DEFAULT_PROPERTIES = 'Job,JobItem,OperNum,Wc,JobQtyReleased,JshSetupHrs,DerRunMchHrs,DerRunLbrHrs,SetupHrsT,RunHrsTMch,RunHrsTLbr,ObsDate'
const ROW_HEIGHT = 36
const VISIBLE_ROWS = 60

const props = defineProps<{ isConnected: boolean }>()

const uiStore = useUiStore()

// IDO state
const selectedIdo = ref('SLJobRoutes')
const idoProperties = ref(DEFAULT_PROPERTIES)
const idoFilter = ref("Type = 'J'")
const idoLimit = ref(100)
const inforData = ref<Record<string, unknown>[]>([])
const loading = ref(false)

// Optional field selector
const availableFields = ref<Array<{ name: string; type: string; required: boolean; readOnly: boolean }>>([])
const selectedFields = ref<string[]>(DEFAULT_PROPERTIES.split(','))
const fetchingFields = ref(false)
const hideUdfFields = ref(true)
const showFieldSelector = ref(false)

// Staging state
const stagedRows = ref<StagedProductionRow[]>([])
const selectedIndices = ref<Set<number>>(new Set())
const importing = ref(false)
const selectAll = ref(true)

// Virtual scroll
const scrollTop = ref(0)
const tableContainer = ref<HTMLElement | null>(null)

const totalHeight = computed(() => stagedRows.value.length * ROW_HEIGHT)
const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / ROW_HEIGHT) - 10))
const endIndex = computed(() => Math.min(stagedRows.value.length, startIndex.value + VISIBLE_ROWS))
const visibleRows = computed(() => stagedRows.value.slice(startIndex.value, endIndex.value))
const offsetY = computed(() => startIndex.value * ROW_HEIGHT)

const validCount = computed(() => stagedRows.value.filter(r => r.validation.is_valid).length)
const errorCount = computed(() => stagedRows.value.length - validCount.value)
const selectedValidCount = computed(() => {
  if (selectAll.value) return validCount.value
  let count = 0
  for (const idx of selectedIndices.value) {
    if (stagedRows.value[idx]?.validation.is_valid) count++
  }
  return count
})

// Progress state
const progressDone = ref(0)
const progressTotal = ref(0)
const progressLabel = ref('')

function onTableScroll(e: Event) {
  scrollTop.value = (e.target as HTMLElement).scrollTop
}

function isSelected(rowIndex: number): boolean {
  return selectAll.value ? true : selectedIndices.value.has(rowIndex)
}

function toggleRow(rowIndex: number) {
  if (selectAll.value) {
    selectAll.value = false
    selectedIndices.value = new Set(stagedRows.value.map((_, i) => i))
    selectedIndices.value.delete(rowIndex)
  } else {
    if (selectedIndices.value.has(rowIndex)) {
      selectedIndices.value.delete(rowIndex)
    } else {
      selectedIndices.value.add(rowIndex)
    }
  }
}

function doSelectAll() {
  selectAll.value = true
  selectedIndices.value.clear()
}

function doDeselectAll() {
  selectAll.value = false
  selectedIndices.value.clear()
}

function getSelectedRows(): StagedProductionRow[] {
  if (selectAll.value) return stagedRows.value
  return [...selectedIndices.value]
    .map(i => stagedRows.value[i])
    .filter((r): r is StagedProductionRow => r != null)
}

async function fetchFieldsForIdo() {
  if (!selectedIdo.value) { await alert({ title: 'Chyba', message: 'Zadejte IDO name', type: 'warning' }); return }
  fetchingFields.value = true
  try {
    const data = await getInforIdoInfo(selectedIdo.value)
    const fields = data.info || []
    availableFields.value = fields.map((f: { name: string; dataType?: string; required?: boolean; readOnly?: boolean }) => ({
      name: f.name, type: f.dataType || 'String', required: f.required || false, readOnly: f.readOnly || false
    }))
    const hints = ['Job', 'JobItem', 'OperNum', 'Wc', 'Qty', 'Setup', 'RunMch', 'RunLbr', 'DerRun']
    const current = idoProperties.value.split(',').map(s => s.trim()).filter(Boolean)
    selectedFields.value = current.length > 0
      ? current.filter(name => availableFields.value.some(f => f.name === name))
      : availableFields.value.filter(f => hints.some(h => f.name.includes(h))).map(f => f.name).slice(0, 12)
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
    const params: InforIdoDataParams = {
      properties: idoProperties.value,
      limit: idoLimit.value,
      ...(idoFilter.value ? { filter: idoFilter.value } : {})
    }
    const data = await getInforIdoData(selectedIdo.value, params)
    inforData.value = data.data || []
    uiStore.showSuccess(`Načteno ${inforData.value.length.toLocaleString()} řádků`)
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
  progressDone.value = 0
  progressTotal.value = inforData.value.length
  progressLabel.value = 'Stage'
  try {
    const result = await previewProductionImport(
      inforData.value,
      (done, total) => { progressDone.value = done; progressTotal.value = total }
    )
    for (const row of result.rows) {
      row.infor_data = {}
    }
    stagedRows.value = result.rows
    selectAll.value = true
    selectedIndices.value.clear()
    uiStore.showSuccess(`Staged: ${result.valid_count.toLocaleString()} valid, ${result.error_count.toLocaleString()} errors, ${result.duplicate_count.toLocaleString()} duplicates`)
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba preview')
  } finally {
    loading.value = false
    progressDone.value = 0
    progressTotal.value = 0
    progressLabel.value = ''
  }
}

async function executeImport() {
  const rows = getSelectedRows().filter(r => r.validation.is_valid)
  if (rows.length === 0) { uiStore.showError('Žádné validní řádky k importu'); return }
  importing.value = true
  progressDone.value = 0
  progressTotal.value = rows.length
  progressLabel.value = 'Import'
  try {
    const result = await executeProductionImport(
      rows,
      (done, total) => { progressDone.value = done; progressTotal.value = total }
    )
    uiStore.showSuccess(`Import: ${result.created_count} vytvořeno, ${result.updated_count} aktualizováno, ${result.skipped_count} přeskočeno`)
    stagedRows.value = []
    selectAll.value = true
    selectedIndices.value.clear()
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba importu')
  } finally {
    importing.value = false
    progressDone.value = 0
    progressTotal.value = 0
    progressLabel.value = ''
  }
}

function fmt(val: unknown, decimals = 1): string {
  if (val == null) return '-'
  const n = Number(val)
  return isNaN(n) ? '-' : n.toFixed(decimals)
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
          <input v-model="selectedIdo" type="text" class="input" placeholder="SLJobRoutes" />
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
          <input v-model="idoFilter" type="text" class="input" placeholder="Type = 'J'" />
        </div>
      </div>

      <div class="toolbar">
        <button @click="loadInforData" :disabled="loading || !isConnected || !idoProperties" class="btn-ghost">
          <Search :size="ICON_SIZE.STANDARD" /> {{ loading ? 'Načítám...' : 'Načíst data' }}
        </button>
        <button @click="stageAll" :disabled="inforData.length === 0 || loading" class="btn-ghost">
          <Download :size="ICON_SIZE.STANDARD" /> Stage vše ({{ inforData.length.toLocaleString() }})
        </button>
        <button @click="fetchFieldsForIdo" :disabled="fetchingFields || !selectedIdo" class="btn-ghost btn-secondary">
          <FileText :size="ICON_SIZE.STANDARD" /> {{ fetchingFields ? '...' : 'Načíst pole' }}
        </button>
      </div>

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

      <div v-if="progressTotal > 0" class="progress-bar-container">
        <div class="progress-info">{{ progressLabel }}: {{ progressDone.toLocaleString() }} / {{ progressTotal.toLocaleString() }}</div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: (progressDone / progressTotal * 100) + '%' }"></div>
        </div>
      </div>

      <InforDataTable :data="inforData" />
    </div>

    <!-- STEP 2: Staging & Import (virtual scroll) -->
    <div class="section" v-if="stagedRows.length > 0">
      <h4>2. Review & Import ({{ stagedRows.length.toLocaleString() }} řádků)</h4>
      <div class="summary">
        <span class="badge-valid"><CheckCircle :size="ICON_SIZE.SMALL" /> {{ validCount.toLocaleString() }} valid</span>
        <span class="badge-error"><XCircle :size="ICON_SIZE.SMALL" /> {{ errorCount.toLocaleString() }} errors</span>
      </div>
      <div class="toolbar">
        <button @click="doSelectAll" class="btn-ghost"><Check :size="ICON_SIZE.STANDARD" /> Vybrat vše</button>
        <button @click="doDeselectAll" class="btn-ghost"><X :size="ICON_SIZE.STANDARD" /> Zrušit výběr</button>
        <button @click="stagedRows = []; selectAll = true; selectedIndices.clear()" class="btn-ghost btn-danger">
          <Trash2 :size="ICON_SIZE.STANDARD" /> Vymazat
        </button>
      </div>

      <!-- Virtual scroll container -->
      <div class="table-scroll" ref="tableContainer" @scroll="onTableScroll">
        <table class="staging-table">
          <thead>
            <tr>
              <th class="col-check">☑</th>
              <th class="col-status">St</th>
              <th class="col-text">Article #</th>
              <th class="col-text">Job</th>
              <th class="col-val">OP</th>
              <th class="col-val">Ks</th>
              <th class="col-val">Setup plán</th>
              <th class="col-val">Stroj plán</th>
              <th class="col-val">Obsl plán</th>
              <th class="col-val">Man plán</th>
              <th class="col-val">Setup real</th>
              <th class="col-val">Stroj real</th>
              <th class="col-val">Obsl real</th>
              <th class="col-val">Man real</th>
              <th class="col-text">WC</th>
              <th class="col-errors">Chyby</th>
            </tr>
          </thead>
          <tbody :style="{ height: totalHeight + 'px', position: 'relative' }">
            <!-- Spacer top -->
            <tr v-if="offsetY > 0" :style="{ height: offsetY + 'px' }"><td colspan="16"></td></tr>
            <!-- Visible rows only -->
            <tr v-for="row in visibleRows" :key="row.row_index"
                :class="{ 'row-error': !row.validation.is_valid }"
                :style="{ height: ROW_HEIGHT + 'px' }"
                @click="toggleRow(row.row_index)">
              <td class="col-check"><input type="checkbox" :checked="isSelected(row.row_index)" /></td>
              <td class="col-status">
                <XCircle v-if="!row.validation.is_valid" :size="ICON_SIZE.SMALL" class="icon-error" />
                <CheckCircle v-else :size="ICON_SIZE.SMALL" class="icon-valid" />
              </td>
              <td class="col-text">{{ row.mapped_data.article_number || '-' }}</td>
              <td class="col-text">{{ row.mapped_data.infor_order_number || '-' }}</td>
              <td class="col-val">{{ row.mapped_data.operation_seq }}</td>
              <td class="col-val">{{ row.mapped_data.batch_quantity ?? '-' }}</td>
              <td class="col-val">{{ fmt(row.mapped_data.planned_setup_min) }}</td>
              <td class="col-val">{{ fmt(row.mapped_data.planned_time_min, 2) }}</td>
              <td class="col-val">{{ fmt(row.mapped_data.planned_labor_time_min, 2) }}</td>
              <td class="col-val">{{ row.mapped_data.manning_coefficient != null ? fmt(row.mapped_data.manning_coefficient, 0) + '%' : '-' }}</td>
              <td class="col-val">{{ fmt(row.mapped_data.actual_setup_min) }}</td>
              <td class="col-val highlight">{{ fmt(row.mapped_data.actual_time_min, 2) }}</td>
              <td class="col-val">{{ fmt(row.mapped_data.actual_labor_time_min, 2) }}</td>
              <td class="col-val">{{ row.mapped_data.actual_manning_coefficient != null ? fmt(row.mapped_data.actual_manning_coefficient, 0) + '%' : '-' }}</td>
              <td class="col-text">{{ row.mapped_data.infor_wc_code || '-' }}</td>
              <td class="col-errors">{{ row.validation.errors.join(', ') || '-' }}</td>
            </tr>
            <!-- Spacer bottom -->
            <tr v-if="endIndex < stagedRows.length" :style="{ height: (stagedRows.length - endIndex) * ROW_HEIGHT + 'px' }"><td colspan="16"></td></tr>
          </tbody>
        </table>
      </div>

      <button @click="executeImport" :disabled="selectedValidCount === 0 || importing" class="btn-ghost btn-primary import-btn">
        <Download :size="ICON_SIZE.STANDARD" /> Importovat {{ selectedValidCount.toLocaleString() }} záznamů
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-tab { padding: var(--space-4); overflow: auto; }
.section { margin-bottom: var(--space-6); }
h4 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-3) 0; }
.query-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
.query-row .fg-wide { flex: 3; }
.toolbar { display: flex; gap: var(--space-2); margin: var(--space-3) 0; flex-wrap: wrap; }
.import-btn { margin-top: var(--space-3); }
.summary { display: flex; gap: var(--space-3); margin-bottom: var(--space-2); }
.badge-valid { padding: var(--space-1) var(--space-2); background: var(--bg-raised); color: var(--status-ok); border-radius: var(--radius-md); font-size: var(--text-sm); display: inline-flex; align-items: center; gap: var(--space-1); }
.badge-error { padding: var(--space-1) var(--space-2); background: var(--bg-raised); color: var(--status-error); border-radius: var(--radius-md); font-size: var(--text-sm); display: inline-flex; align-items: center; gap: var(--space-1); }
.table-scroll { overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); max-height: 400px; }
.staging-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.staging-table th { background: var(--bg-surface); padding: var(--space-1) var(--space-2); text-align: left; font-weight: var(--font-semibold); color: var(--text-secondary); border-bottom: 1px solid var(--border-default); position: sticky; top: 0; z-index: 1; white-space: nowrap; }
.staging-table td { padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--border-subtle); white-space: nowrap; }
.staging-table tbody tr { cursor: pointer; }
.staging-table tbody tr:hover { background: var(--state-hover); }
.row-error { background: var(--status-error-bg); }
.col-check { width: 28px; text-align: center; }
.col-status { width: 28px; text-align: center; }
.col-text { text-align: left; }
.col-val { text-align: left; font-variant-numeric: tabular-nums; font-family: var(--font-mono, monospace); }
.col-val.highlight { font-weight: 600; color: var(--text-primary); }
.col-errors { max-width: 200px; color: var(--status-error); font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; }
.icon-valid { color: var(--status-ok); }
.icon-error { color: var(--status-error); }
.progress-bar-container { margin: var(--space-3) 0; }
.progress-info { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-1); }
.progress-track { height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-brand); border-radius: var(--radius-full); transition: width 0.2s ease; }
</style>
