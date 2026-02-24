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
import { useDialog } from '@/composables/useDialog'
import { previewPartsImport, executePartsImport } from '@/api/infor-jobs'
import { getIdoInfo, getIdoData } from '@/api/infor'
import { useUiStore } from '@/stores/ui'
import { FileText, Search, Download, Trash2, Check, X, CheckCircle, XCircle, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforFieldSelector from './InforFieldSelector.vue'
import InforDataTable from './InforDataTable.vue'
import Input from '@/components/ui/Input.vue'
import type { StagedPartRow, InforIdoDataParams } from '@/types/infor'

const DEFAULT_PROPERTIES = 'Item,FamilyCode,Description,DrawingNbr,Revision,RybTridaNazev1'
const DEFAULT_FILTER = "FamilyCode LIKE 'Výrobek' AND (RybTridaNazev1 LIKE 'Nabídka' OR RybTridaNazev1 LIKE 'Aktivní')"

const props = defineProps<{ isConnected: boolean }>()

const uiStore = useUiStore()
const { alert } = useDialog()

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
    await alert({ title: 'Chyba', message: 'Zadejte IDO name' })
    return
  }
  fetchingFields.value = true
  try {
    const data = await getIdoInfo(selectedIdo.value)
    const fields = data.info || []
    availableFields.value = fields.map((f: { name: string; dataType?: string; required?: boolean; readOnly?: boolean }) => ({
      name: f.name, type: f.dataType || 'String', required: f.required || false, readOnly: f.readOnly || false
    }))
    // Pre-select current properties
    const current = idoProperties.value.split(',').map(s => s.trim()).filter(Boolean)
    selectedFields.value = current.filter(name => availableFields.value.some(f => f.name === name))
    showFieldSelector.value = true
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    await alert({ title: 'Chyba', message: 'Nepodařilo se načíst pole: ' + (err.response?.data?.detail || err.message) })
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
    const data = await getIdoData(selectedIdo.value, params)
    inforData.value = data.data || []
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
        <Input v-model="selectedIdo" label="IDO" placeholder="SLItems" data-testid="infor-parts-ido" />
        <div class="fg-wide">
          <Input v-model="idoProperties" label="Properties" data-testid="infor-parts-properties" />
        </div>
        <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
        <input v-model.number="idoLimit" type="number" class="input limit-input" data-testid="infor-parts-limit" />
      </div>

      <div class="query-row">
        <div class="fg-wide">
          <Input v-model="idoFilter" label="Filter (SQL WHERE)" placeholder="FamilyCode LIKE 'Výrobek'" data-testid="infor-parts-filter" />
        </div>
      </div>

      <div class="toolbar">
        <button @click="loadInforData" :disabled="loading || !isConnected || !idoProperties" class="btn-secondary" data-testid="infor-parts-load">
          <Search :size="ICON_SIZE" /> {{ loading ? 'Načítám...' : 'Načíst data' }}
        </button>
        <button @click="stageAll" :disabled="inforData.length === 0 || loading" class="btn-secondary" data-testid="infor-parts-stage">
          <Download :size="ICON_SIZE" /> Stage vše ({{ inforData.length }})
        </button>
        <button @click="fetchFieldsForIdo" :disabled="fetchingFields || !selectedIdo" class="btn-secondary" data-testid="infor-parts-fetch-fields">
          <FileText :size="ICON_SIZE" /> {{ fetchingFields ? '...' : 'Načíst pole' }}
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
        <span class="badge"><span class="badge-dot-ok"></span>{{ stagedRows.filter(r => r.validation.is_valid).length }} valid</span>
        <span class="badge"><span class="badge-dot-error"></span>{{ stagedRows.filter(r => !r.validation.is_valid).length }} chyb</span>
        <span class="badge"><span class="badge-dot-warn"></span>{{ stagedRows.filter(r => r.validation.is_duplicate).length }} duplicit</span>
      </div>
      <div class="toolbar">
        <button @click="selectedStaged = [...stagedRows]" class="btn-secondary" data-testid="infor-parts-select-all"><Check :size="ICON_SIZE" /> Vybrat vše</button>
        <button @click="selectedStaged = []" class="btn-secondary" data-testid="infor-parts-deselect-all"><X :size="ICON_SIZE" /> Zrušit výběr</button>
        <button @click="stagedRows = []; selectedStaged = []" class="btn-destructive" data-testid="infor-parts-clear"><Trash2 :size="ICON_SIZE" /> Vymazat</button>
      </div>
      <div class="ot-wrap">
        <table class="ot">
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
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <td><input type="checkbox" :checked="selectedStaged.includes(row)" /></td>
              <td class="status-cell">
                <XCircle v-if="!row.validation.is_valid" :size="ICON_SIZE" class="icon-error" />
                <AlertTriangle v-else-if="row.validation.is_duplicate" :size="ICON_SIZE" class="icon-dup" />
                <CheckCircle v-else :size="ICON_SIZE" class="icon-valid" />
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
      <button @click="executeImport" :disabled="selectedStaged.length === 0 || importing" class="btn-primary import-btn" data-testid="infor-parts-import">
        <Download :size="ICON_SIZE" /> Importovat {{ selectedStaged.filter(r => r.validation.is_valid).length }} položek
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-tab { padding: 12px; overflow: auto; }
.section { margin-bottom: 20px; }
h4 { font-size: var(--fsh); font-weight: 600; color: var(--t1); margin: 0 0 var(--pad) 0; }
.query-row { display: flex; gap: var(--pad); margin-bottom: var(--pad); align-items: flex-end; }
.query-row .fg-wide { flex: 3; }
.limit-input { width: 80px; }
.toolbar { display: flex; gap: 6px; margin: var(--pad) 0; flex-wrap: wrap; }
.import-btn { margin-top: var(--pad); }
.summary { display: flex; gap: var(--pad); margin-bottom: 6px; }
.ot-wrap { overflow-y: auto; border: 1px solid var(--b2); border-radius: var(--r); max-height: 360px; }
.row-error td { background: var(--err-10); }
.row-dup td { background: var(--warn-10); }
.status-cell { text-align: center; }
.icon-valid { color: var(--ok); }
.icon-error { color: var(--err); }
.icon-dup { color: var(--warn); }
.errors-cell { max-width: 300px; color: var(--err); font-size: var(--fs); }
</style>
