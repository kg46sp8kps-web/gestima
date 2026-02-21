<script setup lang="ts">
/**
 * Document Import Tab - Import Drawings/Documents from Infor SLDocumentObjects_Exts
 *
 * Two-step flow:
 *   Step 1 (InforDocumentQueryPanel): Load IDO data from Infor
 *   Step 2: Preview (match to Parts) + Execute import
 */

import { ref, computed } from 'vue'
import { previewDocumentImport, executeDocumentImport } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { Download, Trash2, Check, X, CheckCircle, XCircle, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforDocumentQueryPanel from './InforDocumentQueryPanel.vue'
import type { StagedDocumentRow } from '@/types/infor'

const props = defineProps<{ isConnected: boolean }>()

const uiStore = useUiStore()

// Raw IDO rows from Infor (passed up from query panel)
const inforData = ref<Record<string, unknown>[]>([])

// Staging state
const stagedRows = ref<StagedDocumentRow[]>([])
const selectedIndices = ref<Set<number>>(new Set())
const selectAll = ref(true)
const loading = ref(false)
const importing = ref(false)

// Progress state
const progressDone = ref(0)
const progressTotal = ref(0)
const progressLabel = ref('')

// Summary computed
const validCount = computed(() => stagedRows.value.filter(r => r.is_valid).length)
const errorCount = computed(() => stagedRows.value.filter(r => !r.is_valid).length)
const duplicateCount = computed(() => stagedRows.value.filter(r => r.is_duplicate).length)
const matchedCount = computed(() => stagedRows.value.filter(r => r.matched_part_id !== null).length)

const selectedValidCount = computed(() => {
  if (selectAll.value) return validCount.value
  let count = 0
  for (const idx of selectedIndices.value) {
    if (stagedRows.value[idx]?.is_valid) count++
  }
  return count
})

function isSelected(rowIndex: number): boolean {
  return selectAll.value ? true : selectedIndices.value.has(rowIndex)
}

function toggleRow(rowIndex: number) {
  if (selectAll.value) {
    selectAll.value = false
    selectedIndices.value = new Set(stagedRows.value.map((_, i) => i))
    selectedIndices.value.delete(rowIndex)
  } else {
    if (selectedIndices.value.has(rowIndex)) selectedIndices.value.delete(rowIndex)
    else selectedIndices.value.add(rowIndex)
  }
}

function doSelectAll() { selectAll.value = true; selectedIndices.value.clear() }
function doDeselectAll() { selectAll.value = false; selectedIndices.value.clear() }

function getSelectedRows(): StagedDocumentRow[] {
  if (selectAll.value) return stagedRows.value
  return [...selectedIndices.value].map(i => stagedRows.value[i]).filter((r): r is StagedDocumentRow => r !== undefined)
}

function onDataLoaded(rows: Record<string, unknown>[]) {
  inforData.value = rows
}

async function stageAll() {
  if (inforData.value.length === 0) { uiStore.showError('Žádná data k párování'); return }
  loading.value = true
  progressDone.value = 0
  progressTotal.value = inforData.value.length
  progressLabel.value = 'Párování'
  try {
    const result = await previewDocumentImport(
      inforData.value,
      (done, total) => { progressDone.value = done; progressTotal.value = total }
    )
    stagedRows.value = result.rows
    selectAll.value = true
    selectedIndices.value.clear()
    uiStore.showSuccess(`Napárováno: ${result.valid_count} platných, ${result.error_count} chyb, ${result.duplicate_count} duplikátů`)
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba párování')
  } finally {
    loading.value = false
    progressDone.value = 0
    progressTotal.value = 0
    progressLabel.value = ''
  }
}

async function executeImport() {
  const rows = getSelectedRows().filter(r => r.is_valid)
  if (rows.length === 0) { uiStore.showError('Žádné platné řádky k importu'); return }
  importing.value = true
  progressDone.value = 0
  progressTotal.value = rows.length
  progressLabel.value = 'Import'
  try {
    const result = await executeDocumentImport(
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
</script>

<template>
  <div class="import-tab">
    <!-- STEP 1: Query panel (IDO config + Load + Field selector) -->
    <InforDocumentQueryPanel
      :is-connected="isConnected"
      :infor-data-count="inforData.length"
      :loading="loading"
      @data-loaded="onDataLoaded"
      @stage-all="stageAll"
    />

    <!-- Progress bar (preview or import) -->
    <div v-if="progressTotal > 0" class="progress-bar-container">
      <div class="progress-info">{{ progressLabel }}: {{ progressDone }} / {{ progressTotal }}</div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: (progressDone / progressTotal * 100) + '%' }"></div>
      </div>
    </div>

    <!-- STEP 2: Staging & Import -->
    <div class="section" v-if="stagedRows.length > 0">
      <h4>2. Review & Import ({{ stagedRows.length }} dokumentů)</h4>

      <!-- Summary stats -->
      <div class="summary">
        <span class="badge-neutral">Celkem: {{ stagedRows.length }}</span>
        <span class="badge-valid"><CheckCircle :size="ICON_SIZE.SMALL" /> Napárováno: {{ matchedCount }}</span>
        <span class="badge-dup"><AlertTriangle :size="ICON_SIZE.SMALL" /> Duplikáty: {{ duplicateCount }}</span>
        <span class="badge-error"><XCircle :size="ICON_SIZE.SMALL" /> Chyby: {{ errorCount }}</span>
      </div>

      <div class="toolbar">
        <button @click="doSelectAll" class="btn-ghost"><Check :size="ICON_SIZE.STANDARD" /> Vybrat vše</button>
        <button @click="doDeselectAll" class="btn-ghost"><X :size="ICON_SIZE.STANDARD" /> Zrušit výběr</button>
        <button @click="stagedRows = []; selectAll = true; selectedIndices.clear()" class="btn-ghost btn-danger">
          <Trash2 :size="ICON_SIZE.STANDARD" /> Vymazat
        </button>
      </div>

      <div class="table-scroll">
        <table class="staging-table">
          <thead>
            <tr>
              <th class="col-check">☑</th>
              <th class="col-status">Stav</th>
              <th>Název dokumentu</th>
              <th class="col-ext">Ext</th>
              <th>Napárovaný díl</th>
              <th>Chyby / Varování</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in stagedRows"
              :key="row.row_index"
              :class="{ 'row-error': !row.is_valid, 'row-dup': row.is_duplicate }"
              @click="toggleRow(row.row_index)"
            >
              <td class="col-check"><input type="checkbox" :checked="isSelected(row.row_index)" /></td>
              <td class="status-cell">
                <XCircle v-if="!row.is_valid" :size="ICON_SIZE.STANDARD" class="icon-error" />
                <AlertTriangle v-else-if="row.is_duplicate" :size="ICON_SIZE.STANDARD" class="icon-dup" />
                <CheckCircle v-else :size="ICON_SIZE.STANDARD" class="icon-valid" />
              </td>
              <td class="col-name">{{ row.document_name }}</td>
              <td class="col-ext">{{ row.document_extension || '-' }}</td>
              <td class="col-part">
                <span v-if="row.matched_part_id" class="part-match">
                  {{ row.matched_part_number }} — {{ row.matched_article_number }}
                </span>
                <span v-else class="part-none">— nespárováno —</span>
              </td>
              <td class="errors-cell">
                <span v-if="row.errors.length">{{ row.errors.join(', ') }}</span>
                <span v-else-if="row.warnings.length" class="warn-text">{{ row.warnings.join(', ') }}</span>
                <span v-else>-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <button
        @click="executeImport"
        :disabled="selectedValidCount === 0 || importing"
        class="btn-ghost btn-primary import-btn"
      >
        <Download :size="ICON_SIZE.STANDARD" />
        {{ importing ? 'Importuji...' : `Importovat ${selectedValidCount} dokumentů` }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-tab { padding: var(--space-4); overflow: auto; }
.section { margin-bottom: var(--space-6); }
h4 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-3) 0; }
.toolbar { display: flex; gap: var(--space-2); margin: var(--space-3) 0; flex-wrap: wrap; }
.import-btn { margin-top: var(--space-3); }
.summary { display: flex; gap: var(--space-3); margin-bottom: var(--space-2); flex-wrap: wrap; }
.badge-neutral { padding: var(--space-1) var(--space-2); background: var(--bg-surface); color: var(--text-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.badge-valid { padding: var(--space-1) var(--space-2); background: rgba(34, 197, 94, 0.12); color: rgb(34, 197, 94); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.badge-error { padding: var(--space-1) var(--space-2); background: rgba(239, 68, 68, 0.12); color: rgb(239, 68, 68); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.badge-dup { padding: var(--space-1) var(--space-2); background: rgba(251, 146, 60, 0.12); color: rgb(251, 146, 60); border-radius: var(--radius-md); font-size: var(--text-xs); display: inline-flex; align-items: center; gap: var(--space-1); }
.table-scroll { overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); max-height: 400px; }
.staging-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.staging-table th { background: var(--bg-surface); padding: var(--space-2) var(--space-3); text-align: left; font-weight: var(--font-semibold); color: var(--text-secondary); border-bottom: 1px solid var(--border-default); position: sticky; top: 0; z-index: 1; }
.staging-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border-subtle); white-space: nowrap; }
.staging-table tbody tr { cursor: pointer; }
.staging-table tbody tr:hover { background: var(--state-hover); }
.row-error { background: rgba(239, 68, 68, 0.08); }
.row-dup { background: rgba(251, 146, 60, 0.08); }
.col-check { width: 32px; text-align: center; }
.col-status { width: 40px; text-align: center; }
.col-ext { width: 60px; }
.col-name { max-width: 280px; overflow: hidden; text-overflow: ellipsis; }
.col-part { min-width: 180px; }
.status-cell { text-align: center; }
.icon-valid { color: rgb(34, 197, 94); }
.icon-error { color: rgb(239, 68, 68); }
.icon-dup { color: rgb(251, 146, 60); }
.part-match { color: var(--text-primary); font-family: var(--font-mono); font-size: var(--text-xs); }
.part-none { color: var(--text-tertiary); font-style: italic; font-size: var(--text-xs); }
.errors-cell { max-width: 260px; color: rgb(239, 68, 68); font-size: var(--text-xs); overflow: hidden; text-overflow: ellipsis; }
.warn-text { color: rgb(251, 146, 60); }
.progress-bar-container { margin: var(--space-3) 0; }
.progress-info { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-1); }
.progress-track { height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-brand); border-radius: var(--radius-full); transition: width 0.2s ease; }
</style>
