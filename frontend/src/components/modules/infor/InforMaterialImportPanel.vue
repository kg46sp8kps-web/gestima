<script setup lang="ts">
/**
 * Material Import Panel - MVP Version
 *
 * Simple split-pane import UI for Infor → Gestima materials
 */

import { ref, computed } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'
import {
  Check,
  X,
  Search,
  ArrowRight,
  Package,
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Trash2,
  FileText,
  Download
} from 'lucide-vue-next'
import type {
  StagedMaterialRow,
  MaterialImportPreviewResponse,
  MaterialImportExecuteResponse
} from '@/types/infor'
import { getSurfaceTreatmentLabel } from '@/types/infor'

// Props
const props = defineProps<{
  isConnected: boolean
}>()

// State - Load source
const selectedIdo = ref('SLItems')
const selectedFields = ref<string[]>(['Item', 'Description'])
const availableFields = ref<Array<{ name: string; type: string; required: boolean }>>([])
const fetchingFields = ref(false)
const showFieldChooser = ref(false)
const fieldSearchQuery = ref('')
const idoLimit = ref(2000)
const idoFilter = ref("FamilyCode like 'materiál'")  // WHERE clause for Infor query
const inforData = ref<any[]>([])
const selectedRows = ref<any[]>([])
const loading = ref(false)

// State - Staging
const stagedRows = ref<StagedMaterialRow[]>([])
const selectedStagedRows = ref<StagedMaterialRow[]>([])  // Selected rows for import
const stagingSearchQuery = ref('')  // Search in staging table
const importing = ref(false)

// State - Pattern Testing Modal
const showTestModal = ref(false)
const testResult = ref<any>(null)
const testingPattern = ref(false)

// State - UI
const panelSize = ref(50)  // Split panel size in percentage
const isDragging = ref(false)

// Computed
const validCount = computed(() => stagedRows.value.filter(r => r.validation.is_valid).length)
const errorCount = computed(() => stagedRows.value.filter(r => !r.validation.is_valid).length)
const duplicateCount = computed(() => stagedRows.value.filter(r => r.validation.is_duplicate).length)
const selectedValidCount = computed(() => selectedStagedRows.value.filter(r => r.validation.is_valid).length)

const filteredFields = computed(() => {
  if (!fieldSearchQuery.value) return availableFields.value

  const query = fieldSearchQuery.value.toLowerCase()
  return availableFields.value.filter(field =>
    field.name.toLowerCase().includes(query) ||
    field.type.toLowerCase().includes(query)
  )
})

const filteredStagedRows = computed(() => {
  if (!stagingSearchQuery.value) return stagedRows.value

  const query = stagingSearchQuery.value.toLowerCase()
  return stagedRows.value.filter(row => {
    const data = row.mapped_data
    return (
      data.code?.toLowerCase().includes(query) ||
      data.name?.toLowerCase().includes(query) ||
      data.shape?.toLowerCase().includes(query)
    )
  })
})

// Fetch available fields for IDO
async function fetchFields() {
  if (!selectedIdo.value) {
    await alert({ title: 'Chyba', message: 'Zadejte IDO name', type: 'warning' })
    return
  }

  fetchingFields.value = true
  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/info`)
    const fields = response.data.info || []

    availableFields.value = fields.map((field: any) => ({
      name: field.name,
      type: field.dataType || 'String',
      required: field.required || false
    }))

    showFieldChooser.value = true
  } catch (error: any) {
    await alert({ title: 'Error', message: error.response?.data?.detail || error.message, type: 'error' })
  } finally {
    fetchingFields.value = false
  }
}

// Toggle field selection
function toggleField(fieldName: string) {
  const idx = selectedFields.value.indexOf(fieldName)
  if (idx > -1) {
    selectedFields.value.splice(idx, 1)
  } else {
    selectedFields.value.push(fieldName)
  }
}

// Load Infor data
async function loadInforData() {
  if (!selectedIdo.value || selectedFields.value.length === 0) {
    await alert({ title: 'Chyba', message: 'Vyberte IDO a fieldy', type: 'warning' })
    return
  }

  loading.value = true
  try {
    const params: any = {
      properties: selectedFields.value.join(','),
      limit: idoLimit.value
    }

    // Add filter if provided
    if (idoFilter.value.trim()) {
      params.filter = idoFilter.value.trim()
    }

    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/data`, {
      params
    })
    inforData.value = response.data.data || []
    // Success - no modal needed, data count is visible in UI
  } catch (error: any) {
    await alert({ title: 'Error', message: error.response?.data?.detail || error.message, type: 'error' })
  } finally {
    loading.value = false
  }
}

// Toggle row selection
function toggleRow(row: any) {
  const idx = selectedRows.value.indexOf(row)
  if (idx > -1) {
    selectedRows.value.splice(idx, 1)
  } else {
    selectedRows.value.push(row)
  }
}

// Select all rows
function selectAll() {
  selectedRows.value = [...inforData.value]
}

// Unselect all rows
function unselectAll() {
  selectedRows.value = []
}

// Clear all loaded data
function clearData() {
  inforData.value = []
  selectedRows.value = []
  stagedRows.value = []
  selectedStagedRows.value = []
}

// Clear staging area
function clearStaging() {
  stagedRows.value = []
  selectedStagedRows.value = []
}

// Toggle staged row selection
function toggleStagedRow(row: StagedMaterialRow) {
  const idx = selectedStagedRows.value.indexOf(row)
  if (idx > -1) {
    selectedStagedRows.value.splice(idx, 1)
  } else {
    selectedStagedRows.value.push(row)
  }
}

// Select all staged rows
function selectAllStaged() {
  selectedStagedRows.value = [...stagedRows.value]
}

// Unselect all staged rows
function unselectAllStaged() {
  selectedStagedRows.value = []
}

// Resize panel handler
function startResize(event: MouseEvent) {
  isDragging.value = true
  const startX = event.clientX
  const startSize = panelSize.value
  const containerWidth = (event.target as HTMLElement).parentElement?.offsetWidth || 1000

  const onMouseMove = (e: MouseEvent) => {
    const deltaX = e.clientX - startX
    const deltaPercent = (deltaX / containerWidth) * 100
    const newSize = Math.max(20, Math.min(80, startSize + deltaPercent))
    panelSize.value = newSize
  }

  const onMouseUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Stage selected rows (preview)
async function stageSelected() {
  if (selectedRows.value.length === 0) {
    await alert({ title: 'Chyba', message: 'Vyberte řádky', type: 'warning' })
    return
  }

  loading.value = true
  try {
    // Clean rows: remove metadata fields that start with underscore
    const cleanedRows = selectedRows.value.map(row => {
      const cleaned: any = {}
      for (const [key, value] of Object.entries(row)) {
        // Skip fields that start with underscore (metadata)
        if (!key.startsWith('_')) {
          cleaned[key] = value
        }
      }
      return cleaned
    })

    // DEBUG: Log what we're sending
    console.log('[Staging]', {
      ido_name: selectedIdo.value,
      rows_count: cleanedRows.length,
      first_row: cleanedRows[0],
      original_first_row: selectedRows.value[0]
    })

    const response = await axios.post<MaterialImportPreviewResponse>('/api/infor/import/materials/preview', {
      ido_name: selectedIdo.value,
      rows: cleanedRows
    })

    stagedRows.value = response.data.rows as StagedMaterialRow[]

    console.log('[Preview] Success:', {
      valid: response.data.valid_count,
      errors: response.data.error_count,
      duplicates: response.data.duplicate_count,
      first_staged: stagedRows.value[0]
    })

    // Success - no modal needed, counts are visible in summary badges
  } catch (error: any) {
    console.error('[Preview] Error:', error)
    console.error('Error response:', error.response?.data)

    // Show full error message
    const errorDetail = error.response?.data?.detail || error.message
    console.error('Full error detail:', errorDetail)

    await alert({
      title: 'Error',
      message: typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail),
      type: 'error'
    })
  } finally {
    loading.value = false
  }
}

// Test pattern modal
async function openTestModal() {
  // Get first selected row OR first error row
  let testRow: StagedMaterialRow | null = null

  if (selectedStagedRows.value.length > 0) {
    testRow = selectedStagedRows.value[0]
  } else if (stagedRows.value.length > 0) {
    // Find first row with errors
    testRow = stagedRows.value.find(r => !r.validation.is_valid) || stagedRows.value[0]
  }

  if (!testRow) {
    await alert({ title: 'Chyba', message: 'Není k dispozici žádný řádek pro test', type: 'warning' })
    return
  }

  testingPattern.value = true
  try {
    const response = await axios.post('/api/infor/import/materials/test-pattern', {
      row: testRow.infor_data
    })

    testResult.value = response.data
    showTestModal.value = true
  } catch (error: any) {
    await alert({ title: 'Error', message: error.response?.data?.detail || error.message, type: 'error' })
  } finally {
    testingPattern.value = false
  }
}

function closeTestModal() {
  showTestModal.value = false
  testResult.value = null
}

// Execute import
async function executeImport() {
  if (selectedStagedRows.value.length === 0) {
    await alert({ title: 'Chyba', message: 'Vyberte řádky k importu', type: 'warning' })
    return
  }

  const selectedWithErrors = selectedStagedRows.value.filter(r => !r.validation.is_valid)
  if (selectedWithErrors.length > 0) {
    await alert({ title: 'Chyba', message: `${selectedWithErrors.length} vybraných řádků má errors`, type: 'error' })
    return
  }

  importing.value = true
  try {
    const rows = selectedStagedRows.value.map(r => {
      const row: any = { ...r.mapped_data }
      // Only add duplicate_action if it's a duplicate
      if (r.validation.is_duplicate) {
        row.duplicate_action = 'skip'
      }
      return row
    })

    console.log('🚀 Executing import with rows:', rows)

    const response = await axios.post<MaterialImportExecuteResponse>('/api/infor/import/materials/execute', {
      rows
    })

    console.log('[Import] Success:', response.data)

    await alert({
      title: 'Import Complete!',
      message: `Created: ${response.data.created_count}, Updated: ${response.data.updated_count}, Skipped: ${response.data.skipped_count}`,
      type: 'success'
    })

    // Clear
    stagedRows.value = []
    selectedRows.value = []
    inforData.value = []

  } catch (error: any) {
    console.error('[Import] Error:', error)
    console.error('Error response:', error.response?.data)

    const errorDetail = error.response?.data?.detail || error.message
    await alert({
      title: 'Import Failed',
      message: typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail, null, 2),
      type: 'error'
    })
  } finally {
    importing.value = false
  }
}

// Get row status class
function getRowClass(row: StagedMaterialRow): string {
  if (!row.validation.is_valid) return 'row-error'
  if (row.validation.is_duplicate) return 'row-duplicate'
  return 'row-valid'
}

function getStatusIcon(row: StagedMaterialRow): 'error' | 'warning' | 'success' {
  if (!row.validation.is_valid) return 'error'
  if (row.validation.is_duplicate) return 'warning'
  return 'success'
}
</script>

<template>
  <div class="import-panel">
    <div class="split-layout">
      <!-- LEFT: Source Data -->
      <div class="left-panel" :style="{ width: panelSize + '%' }">
        <h4>1. Load from Infor</h4>

        <!-- IDO Name + Field Chooser in 2 columns -->
        <div class="form-grid-ido">
          <div class="form-group">
            <label>IDO Name</label>
            <div class="input-with-button">
              <input v-model="selectedIdo" class="input" placeholder="SLItems" />
              <button @click="fetchFields" :disabled="fetchingFields" class="icon-btn" title="Fetch Fields">
                <FileText :size="ICON_SIZE.STANDARD" v-if="!fetchingFields" />
                <span v-else class="spinner"></span>
              </button>
            </div>
          </div>

          <!-- Field Chooser Dropdown -->
          <div v-if="availableFields.length > 0" class="form-group">
            <label>Selected Fields</label>
            <div class="field-chooser">
              <div class="field-chooser-header" @click="showFieldChooser = !showFieldChooser">
                <span class="field-count">{{ selectedFields.length }} / {{ filteredFields.length }} selected</span>
                <span class="toggle-icon">{{ showFieldChooser ? '▼' : '▶' }}</span>
              </div>

              <div v-show="showFieldChooser" class="field-chooser-content">
                <!-- Search Box -->
                <div class="field-search">
                  <input
                    v-model="fieldSearchQuery"
                    type="text"
                    placeholder="Search fields..."
                    class="input search-input"
                    @click.stop
                  />
                </div>

                <!-- Field Checkboxes -->
                <div class="field-checkboxes">
                  <label v-for="field in filteredFields" :key="field.name" class="field-checkbox">
                    <input
                      type="checkbox"
                      :value="field.name"
                      :checked="selectedFields.includes(field.name)"
                      @change="toggleField(field.name)"
                    />
                    <span class="field-name">{{ field.name }}</span>
                    <span class="field-type">{{ field.type }}</span>
                    <span v-if="field.required" class="field-badge required">required</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Filter & Limit in 2 columns -->
        <div class="form-grid-2">
          <div class="form-group">
            <label>Filter (WHERE clause)</label>
            <input v-model="idoFilter" class="input" placeholder="Item LIKE 'A%'" />
            <small class="help-text">Example: Item LIKE 'A%'</small>
          </div>

          <div class="form-group">
            <label>Limit</label>
            <input v-model.number="idoLimit" type="number" class="input" />
          </div>
        </div>

        <!-- Infor Data Table -->
        <div class="data-section">
          <div class="table-header">
            <div class="table-header-left">
              <button @click="loadInforData" :disabled="loading || !isConnected" class="icon-btn icon-btn-primary" title="Load Data">
                <Search :size="ICON_SIZE.STANDARD" v-if="!loading" />
                <span v-else class="spinner"></span>
              </button>
              <p v-if="inforData.length > 0"><strong>{{ inforData.length }}</strong> rows loaded</p>
            </div>
            <div v-if="inforData.length > 0" class="selection-controls">
              <button @click="stageSelected" :disabled="selectedRows.length === 0" class="icon-btn icon-btn-primary" :title="`Stage Selected (${selectedRows.length})`">
                <ArrowRight :size="ICON_SIZE.STANDARD" />
              </button>
              <button @click="selectAll" class="icon-btn" title="Select All">
                <Check :size="ICON_SIZE.STANDARD" />
              </button>
              <button @click="unselectAll" class="icon-btn" title="Unselect All">
                <X :size="ICON_SIZE.STANDARD" />
              </button>
              <button @click="clearData" class="icon-btn icon-btn-danger" title="Clear Data">
                <Trash2 :size="ICON_SIZE.STANDARD" />
              </button>
            </div>
          </div>

          <div v-if="inforData.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>☑</th>
                  <th v-for="key in Object.keys(inforData[0]).filter(k => !k.startsWith('_'))" :key="key">{{ key }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in inforData" :key="idx" @click="toggleRow(row)">
                  <td><input type="checkbox" :checked="selectedRows.includes(row)" /></td>
                  <td v-for="key in Object.keys(row).filter(k => !k.startsWith('_'))" :key="key">{{ row[key] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- RESIZE HANDLE -->
      <div
        class="resize-handle"
        :class="{ dragging: isDragging }"
        @mousedown="startResize"
      />

      <!-- RIGHT: Staging -->
      <div class="right-panel" :style="{ width: (100 - panelSize) + '%' }">
        <h4>2. Review & Import</h4>

        <div v-if="stagedRows.length > 0">
          <!-- Summary -->
          <div class="summary">
            <span class="badge-valid"><Check :size="ICON_SIZE.SMALL" /> {{ validCount }} valid</span>
            <span class="badge-error"><X :size="ICON_SIZE.SMALL" /> {{ errorCount }} errors</span>
            <span class="badge-duplicate"><AlertTriangle :size="ICON_SIZE.SMALL" /> {{ duplicateCount }} duplicates</span>
          </div>

          <!-- Staging Header -->
          <div class="table-header">
            <div>
              <input
                v-model="stagingSearchQuery"
                type="text"
                placeholder="Search..."
                class="input search-input-inline"
              />
              <small class="help-text-inline">{{ selectedStagedRows.length }} / {{ filteredStagedRows.length }} selected</small>
            </div>
            <div class="selection-controls">
              <button @click="selectAllStaged" class="icon-btn" title="Select All">
                <Check :size="ICON_SIZE.STANDARD" />
              </button>
              <button @click="unselectAllStaged" class="icon-btn" title="Unselect All">
                <X :size="ICON_SIZE.STANDARD" />
              </button>
              <button @click="openTestModal" :disabled="testingPattern || stagedRows.length === 0" class="icon-btn" title="Test Pattern">
                <Settings :size="ICON_SIZE.STANDARD" v-if="!testingPattern" />
                <span v-else class="spinner"></span>
              </button>
              <button @click="clearStaging" class="icon-btn icon-btn-danger" title="Clear Staging">
                <Trash2 :size="ICON_SIZE.STANDARD" />
              </button>
            </div>
          </div>

          <!-- Staging Table -->
          <div class="table-wrapper">
            <table class="staging-table">
              <thead>
                <tr>
                  <th>☑</th>
                  <th>Status</th>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Shape</th>
                  <th>Surf</th>
                  <th>Ø</th>
                  <th>WT</th>
                  <th>W</th>
                  <th>T</th>
                  <th>L</th>
                  <th>kg/m</th>
                  <th>Group</th>
                  <th>Price Cat</th>
                  <th>Supplier</th>
                  <th>Stock</th>
                  <th>Norms</th>
                  <th>Errors</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in filteredStagedRows"
                  :key="row.row_index"
                  :class="getRowClass(row)"
                  @click="toggleStagedRow(row)"
                >
                  <td><input type="checkbox" :checked="selectedStagedRows.includes(row)" @click.stop="toggleStagedRow(row)" /></td>
                  <td class="status-cell">
                    <CheckCircle v-if="getStatusIcon(row) === 'success'" :size="ICON_SIZE.STANDARD" class="status-icon-success" />
                    <AlertTriangle v-else-if="getStatusIcon(row) === 'warning'" :size="ICON_SIZE.STANDARD" class="status-icon-warning" />
                    <XCircle v-else :size="ICON_SIZE.STANDARD" class="status-icon-error" />
                  </td>
                  <td>{{ row.mapped_data.code || '-' }}</td>
                  <td>{{ row.mapped_data.name || '-' }}</td>
                  <td>{{ row.mapped_data.shape || '-' }}</td>
                  <td :title="getSurfaceTreatmentLabel(row.mapped_data.surface_treatment)">{{ row.mapped_data.surface_treatment || '-' }}</td>
                  <td>{{ row.mapped_data.diameter || '-' }}</td>
                  <td>{{ row.mapped_data.wall_thickness || '-' }}</td>
                  <td>{{ row.mapped_data.width || '-' }}</td>
                  <td>{{ row.mapped_data.thickness || '-' }}</td>
                  <td>{{ row.mapped_data.standard_length || '-' }}</td>
                  <td>{{ row.mapped_data.weight_per_meter || '-' }}</td>
                  <td>{{ row.mapped_data.material_group_id || '-' }}</td>
                  <td>{{ row.mapped_data.price_category_id || '-' }}</td>
                  <td>{{ row.mapped_data.supplier || '-' }}</td>
                  <td>{{ row.mapped_data.stock_available || '-' }}</td>
                  <td>{{ row.mapped_data.norms || '-' }}</td>
                  <td class="errors-cell" :title="row.validation.errors.join('\n')">
                    <span v-if="row.validation.errors.length > 0" class="error-text">
                      {{ row.validation.errors.join(', ') }}
                    </span>
                    <span v-else-if="row.validation.warnings.length > 0" class="warning-text">
                      {{ row.validation.warnings.join(', ') }}
                    </span>
                    <span v-else>-</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <button @click="executeImport" :disabled="selectedValidCount === 0 || importing" class="btn btn-success">
            <Download :size="ICON_SIZE.SMALL" v-if="!importing" />
            {{ importing ? 'Importing...' : `Import ${selectedValidCount} Materials` }}
          </button>
        </div>

        <div v-else class="placeholder">
          <p class="empty-state">
            <Package :size="ICON_SIZE.XLARGE" :stroke-width="1.5" />
            <span>Stage rows from left panel to preview here</span>
          </p>
        </div>
      </div>
    </div>

    <!-- Pattern Test Modal -->
    <div v-if="showTestModal && testResult" class="modal-overlay" @click="closeTestModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3><Settings :size="ICON_SIZE.STANDARD" /> Pattern Test Result</h3>
          <button @click="closeTestModal" class="btn-close">×</button>
        </div>

        <div class="modal-body">
          <!-- Description -->
          <div class="test-section">
            <label>Original Description:</label>
            <div class="code-block">{{ testResult.description || 'N/A' }}</div>
          </div>

          <!-- Parsed Results -->
          <div class="test-section">
            <label><CheckCircle :size="ICON_SIZE.SMALL" /> Parsed Results:</label>
            <div class="result-grid">
              <div v-if="testResult.parsed.shape" class="result-item success">
                <span class="result-label">Shape:</span>
                <span class="result-value">{{ testResult.parsed.shape }}</span>
              </div>
              <div v-if="testResult.parsed.material_code" class="result-item success">
                <span class="result-label">Material Code:</span>
                <span class="result-value">{{ testResult.parsed.material_code }}</span>
              </div>
              <div v-if="testResult.parsed.surface_treatment" class="result-item success">
                <span class="result-label">Surface Treatment:</span>
                <span class="result-value">{{ getSurfaceTreatmentLabel(testResult.parsed.surface_treatment) }}</span>
              </div>
              <div v-if="testResult.parsed.diameter" class="result-item success">
                <span class="result-label">Diameter:</span>
                <span class="result-value">{{ testResult.parsed.diameter }} mm</span>
              </div>
              <div v-if="testResult.parsed.wall_thickness" class="result-item success">
                <span class="result-label">Wall Thickness:</span>
                <span class="result-value">{{ testResult.parsed.wall_thickness }} mm</span>
              </div>
              <div v-if="testResult.parsed.width" class="result-item success">
                <span class="result-label">Width:</span>
                <span class="result-value">{{ testResult.parsed.width }} mm</span>
              </div>
              <div v-if="testResult.parsed.thickness" class="result-item success">
                <span class="result-label">Thickness:</span>
                <span class="result-value">{{ testResult.parsed.thickness }} mm</span>
              </div>
              <div v-if="testResult.parsed.standard_length" class="result-item success">
                <span class="result-label">Length:</span>
                <span class="result-value">{{ testResult.parsed.standard_length }} mm</span>
              </div>
            </div>
          </div>

          <!-- Detected Results -->
          <div class="test-section">
            <label><Search :size="ICON_SIZE.SMALL" /> Auto-Detected:</label>
            <div class="result-grid">
              <div v-if="testResult.detected.material_group_id" class="result-item success">
                <span class="result-label">Material Group:</span>
                <span class="result-value">
                  {{ testResult.detected.material_group_name }}
                  <small>(ID: {{ testResult.detected.material_group_id }})</small>
                </span>
              </div>
              <div v-if="testResult.detected.price_category_id" class="result-item success">
                <span class="result-label">Price Category:</span>
                <span class="result-value">
                  {{ testResult.detected.price_category_name }}
                  <small>(ID: {{ testResult.detected.price_category_id }})</small>
                </span>
              </div>
            </div>
          </div>

          <!-- Not Found -->
          <div v-if="testResult.not_found && testResult.not_found.length > 0" class="test-section">
            <label><XCircle :size="ICON_SIZE.SMALL" /> Not Found:</label>
            <div class="not-found-list">
              <span v-for="field in testResult.not_found" :key="field" class="not-found-item">
                {{ field }}
              </span>
            </div>
          </div>

          <!-- Errors -->
          <div v-if="testResult.errors && testResult.errors.length > 0" class="test-section">
            <label><XCircle :size="ICON_SIZE.SMALL" /> Errors:</label>
            <ul class="error-list">
              <li v-for="(error, idx) in testResult.errors" :key="idx" class="error-item">
                {{ error }}
              </li>
            </ul>
          </div>

          <!-- Warnings -->
          <div v-if="testResult.warnings && testResult.warnings.length > 0" class="test-section">
            <label><AlertTriangle :size="ICON_SIZE.SMALL" /> Warnings:</label>
            <ul class="warning-list">
              <li v-for="(warning, idx) in testResult.warnings" :key="idx" class="warning-item">
                {{ warning }}
              </li>
            </ul>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeTestModal" class="btn btn-primary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.import-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-base);
}

.split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel, .right-panel {
  overflow: auto;
  padding: var(--space-5);
  flex-shrink: 0;
  background: var(--bg-base);
}

.resize-handle {
  width: 4px;
  cursor: col-resize;
  background: var(--border-default);
  transition: background 0.2s;
  user-select: none;
  flex-shrink: 0;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--primary);
}

h4 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-grid-ido {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  align-items: start;
}

.form-grid-ido .form-group {
  margin-bottom: 0;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: var(--space-3);
  margin-bottom: var(--space-1);
}

.form-grid-2 .form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-primary);
  background: var(--bg-base);
  transition: border-color 0.15s ease;
}

.input:focus {
  outline: none;
  border-color: var(--primary);
}

.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  transition: all 0.15s ease;
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

.btn-accent {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  margin-top: var(--space-3);
}

.btn-accent:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.btn-success {
  background: var(--status-ok);
  color: white;
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-5);
  font-size: var(--text-base);
}

.btn-success:hover:not(:disabled) {
  background: var(--palette-success-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-secondary {
  background: var(--bg-muted);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.15);
  color: var(--status-error);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.25);
}

.data-section {
  margin-top: var(--space-5);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  gap: var(--space-3);
}

.table-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.table-header p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.table-header strong {
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.selection-controls {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.help-text {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.4;
}

.search-input-inline {
  width: 250px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  margin-right: var(--space-2);
}

.search-input-inline:focus {
  outline: none;
  border-color: var(--primary);
}

.help-text-inline {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-left: var(--space-2);
}

.table-wrapper {
  max-height: 500px;
  overflow: auto;
  margin: var(--space-3) 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-base);
}

.data-table, .staging-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th, .staging-table th {
  background: var(--bg-muted);
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: var(--font-semibold);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--border-default);
}

/* Checkbox column - wider to prevent overlap */
.data-table th:first-child,
.staging-table th:first-child,
.data-table td:first-child,
.staging-table td:first-child {
  width: 48px;
  min-width: 48px;
  text-align: center;
  padding: var(--space-2);
}

/* Status column - adequate width */
.staging-table th:nth-child(2),
.staging-table td:nth-child(2) {
  width: 60px;
  min-width: 60px;
  text-align: center;
}

.data-table td, .staging-table td {
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--border-default);
  white-space: nowrap;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.data-table tbody tr {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.staging-table tbody tr {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.staging-table tbody tr:hover {
  background: var(--bg-hover);
}

.summary {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.badge-valid {
  padding: var(--space-2) var(--space-3);
  background: rgba(34, 197, 94, 0.12);
  color: var(--palette-success-hover);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.badge-error {
  padding: var(--space-2) var(--space-3);
  background: rgba(239, 68, 68, 0.12);
  color: var(--palette-danger-hover);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.badge-duplicate {
  padding: var(--space-2) var(--space-3);
  background: rgba(251, 146, 60, 0.12);
  color: var(--status-warn);
  border: 1px solid rgba(251, 146, 60, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.row-valid {
  background: rgba(34, 197, 94, 0.08);
}

.row-error {
  background: rgba(239, 68, 68, 0.12);
}

.row-duplicate {
  background: rgba(251, 146, 60, 0.12);
}

.status-cell {
  text-align: center;
}

.status-icon-success {
  color: var(--palette-success-hover);
}

.status-icon-warning {
  color: var(--status-warn);
}

.status-icon-error {
  color: var(--palette-danger-hover);
}

.errors-cell {
  max-width: 300px;
  font-size: var(--text-sm);
}

.error-text {
  color: var(--status-error);
  font-weight: 500;
}

.warning-text {
  color: var(--status-warn);
  font-weight: 500;
}

.placeholder {
  text-align: center;
  padding: var(--space-12);
  color: var(--text-secondary);
  font-size: var(--text-base);
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-tertiary);
}

.empty-state span {
  font-size: var(--text-base);
}

/* Field Chooser */
.input-with-button {
  display: flex;
  gap: var(--space-2);
}

.input-with-button .input {
  flex: 1;
}

.field-chooser {
  position: relative;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
}

.field-chooser-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  user-select: none;
  transition: all 0.15s ease;
  min-height: 38px;
}

.field-chooser-header:hover {
  background: var(--bg-hover);
}

.field-count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.toggle-icon {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.field-chooser-content {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: var(--space-1);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

.field-search {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.field-search .search-input {
  width: 100%;
  margin: 0;
  font-size: var(--text-sm);
}

.field-checkboxes {
  max-height: 250px;
  overflow-y: auto;
  padding: var(--space-2);
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.field-checkbox:hover {
  background: var(--bg-hover);
}

.field-checkbox input[type="checkbox"] {
  cursor: pointer;
}

.field-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.field-type {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-family: monospace;
}

.field-badge {
  font-size: var(--text-xs);
  padding: var(--space-0\.5) var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-transform: uppercase;
}

.field-badge.required {
  background: var(--brand);
  color: white;
}

/* Pattern Test Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-base);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-close {
  background: none;
  border: none;
  font-size: var(--text-4xl);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-4);
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
}

.test-section {
  margin-bottom: var(--space-4);
}

.test-section label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.code-block {
  background: var(--bg-muted);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: var(--text-sm);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  word-break: break-word;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-2);
}

.result-item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid;
}

.result-item.success {
  background: rgba(34, 197, 94, 0.08);
  border-color: rgba(34, 197, 94, 0.3);
}

.result-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.result-value {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.result-value small {
  color: var(--text-secondary);
  font-weight: normal;
  margin-left: var(--space-1);
}

.not-found-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.not-found-item {
  padding: var(--space-1) var(--space-2);
  background: rgba(239, 68, 68, 0.1);
  color: var(--status-error);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 500;
}

.error-list, .warning-list {
  margin: 0;
  padding-left: var(--space-4);
}

.error-item {
  color: var(--status-error);
  font-size: var(--text-sm);
  margin-bottom: var(--space-1);
}

.warning-item {
  color: var(--status-warn);
  font-size: var(--text-sm);
  margin-bottom: var(--space-1);
}

.btn-accent {
  background: linear-gradient(135deg, var(--brand), var(--brand-active));
  color: white;
  border: none;
}

.btn-accent:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}
</style>
