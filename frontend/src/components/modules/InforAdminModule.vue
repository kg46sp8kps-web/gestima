<script setup lang="ts">
/**
 * Infor CloudSuite Industrial - Admin & Discovery Module
 *
 * Floating Window Module for Infor integration
 * Features:
 * - Connection test & status
 * - IDO discovery (find available collections)
 * - Data browser (explore IDO data)
 * - READ-ONLY integration (NEVER writes to Infor!)
 */

import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'

// === STATE ===
const loading = ref(false)
const connectionStatus = ref<any>(null)
const connectionError = ref<string | null>(null)

// IDO Discovery
const discoveryLoading = ref(false)
const discoveryResults = ref<{ found: string[]; not_found: string[] } | null>(null)
const customIdoNames = ref('')

// Data Browser
const selectedIdo = ref('')
const idoProperties = ref('')
const idoFilter = ref('')
const idoOrderBy = ref('')
const idoLimit = ref(100)
const idoData = ref<any[] | null>(null)
const idoDataLoading = ref(false)
const idoDataError = ref<string | null>(null)

// Pagination
const currentBookmark = ref<string | null>(null)
const hasMore = ref(false)
const allLoadedData = ref<any[]>([]) // For "Load More" accumulation

// Field Selection (for easy checkbox UI)
const availableFields = ref<Array<{ name: string; type: string; required: boolean }>>([])
const selectedFields = ref<string[]>([])
const fetchingFields = ref(false)
const fieldSearchQuery = ref('')
const hideUdfFields = ref(true) // Hide UDF fields by default

// IDO Info
const selectedIdoForInfo = ref('')
const idoInfo = ref<any>(null)
const idoInfoLoading = ref(false)

// Tabs
const activeTab = ref<'connection' | 'discovery' | 'browser' | 'info'>('connection')

// === COMPUTED ===
const isConnected = computed(() => connectionStatus.value?.connected === true)

const foundIdos = computed(() => {
  if (!discoveryResults.value) return []
  return discoveryResults.value.found || []
})

const filteredFields = computed(() => {
  let fields = availableFields.value

  // Filter out UDF and internal fields if hideUdfFields is true
  if (hideUdfFields.value) {
    fields = fields.filter(field =>
      !field.name.startsWith('UDF') &&
      !field.name.startsWith('_Item') &&
      !field.name.includes('RowPointer')
    )
  }

  // Apply search filter
  if (fieldSearchQuery.value) {
    const query = fieldSearchQuery.value.toLowerCase()
    fields = fields.filter(field =>
      field.name.toLowerCase().includes(query) ||
      field.type.toLowerCase().includes(query)
    )
  }

  return fields
})

// === API CALLS ===

async function testConnection() {
  loading.value = true
  connectionError.value = null

  try {
    const response = await axios.get('/api/infor/test-connection')
    connectionStatus.value = response.data

    if (!response.data.connected) {
      connectionError.value = response.data.error || 'Connection failed'
    }
  } catch (error: any) {
    connectionError.value = error.response?.data?.detail || error.message
    connectionStatus.value = null
  } finally {
    loading.value = false
  }
}

async function runDiscovery() {
  discoveryLoading.value = true

  try {
    const params = customIdoNames.value
      ? { custom_names: customIdoNames.value }
      : {}

    const response = await axios.get('/api/infor/discover-idos', { params })
    discoveryResults.value = response.data
  } catch (error: any) {
    await alert({
      title: 'Chyba',
      message: 'Discovery failed: ' + (error.response?.data?.detail || error.message),
      type: 'error'
    })
  } finally {
    discoveryLoading.value = false
  }
}

async function browseIdo(loadType?: 'FIRST' | 'NEXT' | 'PREVIOUS' | 'LAST') {
  if (!selectedIdo.value || !idoProperties.value) {
    await alert({
      title: 'Chyba validace',
      message: 'Please select IDO and specify properties',
      type: 'warning'
    })
    return
  }

  idoDataLoading.value = true
  idoDataError.value = null

  // Reset if loading FIRST or no load type specified
  if (!loadType || loadType === 'FIRST') {
    idoData.value = null
    currentBookmark.value = null
    allLoadedData.value = []
  }

  try {
    const params: any = {
      properties: idoProperties.value,
      limit: idoLimit.value
    }

    if (idoFilter.value) params.filter = idoFilter.value
    if (idoOrderBy.value) params.order_by = idoOrderBy.value
    if (loadType) params.load_type = loadType
    if (currentBookmark.value && loadType === 'NEXT') params.bookmark = currentBookmark.value

    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/data`, { params })

    const newData = response.data.data || []
    idoData.value = newData
    currentBookmark.value = response.data.bookmark || null
    hasMore.value = response.data.has_more || false

  } catch (error: any) {
    idoDataError.value = error.response?.data?.detail || error.message
  } finally {
    idoDataLoading.value = false
  }
}

async function loadMore() {
  if (!currentBookmark.value) {
    await alert({
      title: 'Nelze načíst více',
      message: 'Backend nevrátil bookmark - nemůžu načíst další data. Zkontroluj že backend běží s novým kódem.',
      type: 'warning'
    })
    return
  }

  idoDataLoading.value = true

  try {
    const params: any = {
      properties: idoProperties.value,
      limit: idoLimit.value,
      load_type: 'NEXT',
      bookmark: currentBookmark.value
    }

    if (idoFilter.value) params.filter = idoFilter.value
    if (idoOrderBy.value) params.order_by = idoOrderBy.value

    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/data`, { params })

    const newData = response.data.data || []

    // Append to existing data
    if (idoData.value) {
      idoData.value = [...idoData.value, ...newData]
    } else {
      idoData.value = newData
    }

    allLoadedData.value = idoData.value
    currentBookmark.value = response.data.bookmark || null
    hasMore.value = response.data.has_more || false

  } catch (error: any) {
    idoDataError.value = error.response?.data?.detail || error.message
  } finally {
    idoDataLoading.value = false
  }
}

async function getIdoInfo() {
  if (!selectedIdoForInfo.value) {
    await alert({
      title: 'Chyba validace',
      message: 'Please enter IDO name',
      type: 'warning'
    })
    return
  }

  idoInfoLoading.value = true
  idoInfo.value = null

  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdoForInfo.value}/info`)
    idoInfo.value = response.data.info
  } catch (error: any) {
    await alert({
      title: 'Chyba',
      message: 'Failed to get IDO info: ' + (error.response?.data?.detail || error.message),
      type: 'error'
    })
  } finally {
    idoInfoLoading.value = false
  }
}

// Auto-fill properties from discovery
function useIdoForBrowse(idoName: string) {
  selectedIdo.value = idoName
  activeTab.value = 'browser'
}

// Fetch available fields for selected IDO
async function fetchFieldsForIdo() {
  if (!selectedIdo.value) {
    await alert({
      title: 'Chyba validace',
      message: 'Please enter IDO name first',
      type: 'warning'
    })
    return
  }

  fetchingFields.value = true
  availableFields.value = []
  selectedFields.value = []
  fieldSearchQuery.value = '' // Clear search when fetching new IDO

  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/info`)
    const fields = response.data.info || []

    // Parse fields and extract useful info
    availableFields.value = fields.map((field: any) => ({
      name: field.name,
      type: field.dataType || 'String',
      required: field.required || false,
      readOnly: field.readOnly || false
    }))

    // Auto-select required fields
    selectedFields.value = availableFields.value
      .filter(f => f.required && !f.readOnly)
      .map(f => f.name)
      .slice(0, 5) // Max 5 auto-selected

  } catch (error: any) {
    await alert({
      title: 'Chyba',
      message: 'Failed to fetch fields: ' + (error.response?.data?.detail || error.message),
      type: 'error'
    })
  } finally {
    fetchingFields.value = false
  }
}

// Update properties string when fields are selected/deselected
function toggleField(fieldName: string) {
  const index = selectedFields.value.indexOf(fieldName)
  if (index > -1) {
    selectedFields.value.splice(index, 1)
  } else {
    selectedFields.value.push(fieldName)
  }
  updatePropertiesString()
}

function updatePropertiesString() {
  idoProperties.value = selectedFields.value.join(',')
}

// Select/Deselect all fields
function selectAllFields() {
  selectedFields.value = filteredFields.value.map(f => f.name)
  updatePropertiesString()
}

function deselectAllFields() {
  selectedFields.value = []
  updatePropertiesString()
}

// === LIFECYCLE ===
onMounted(() => {
  testConnection()
})
</script>

<template>
  <div class="infor-admin-module">
    <!-- Header -->
    <div class="module-header">
      <div class="header-content">
        <h2 class="module-title">Infor CloudSuite Integration</h2>
        <div class="connection-badge" v-if="connectionStatus">
          <span v-if="isConnected" class="badge badge-success">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            Connected
          </span>
          <span v-else class="badge badge-error">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
            Disconnected
          </span>
        </div>
      </div>
      <div class="security-note">
        🔒 READ-ONLY mode - Safe to explore, NEVER writes to Infor
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'connection'"
        :class="['tab', { active: activeTab === 'connection' }]"
      >
        🔌 Connection
      </button>
      <button
        @click="activeTab = 'discovery'"
        :class="['tab', { active: activeTab === 'discovery' }]"
      >
        🔍 Discovery
      </button>
      <button
        @click="activeTab = 'browser'"
        :class="['tab', { active: activeTab === 'browser' }]"
      >
        📊 Browser
      </button>
      <button
        @click="activeTab = 'info'"
        :class="['tab', { active: activeTab === 'info' }]"
      >
        ℹ️ Info
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">

      <!-- CONNECTION TAB -->
      <div v-if="activeTab === 'connection'" class="tab-pane">
        <button
          @click="testConnection"
          :disabled="loading"
          class="btn btn-primary mb-4"
        >
          <svg v-if="loading" class="icon spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ loading ? 'Testing...' : 'Test Connection' }}
        </button>

        <div v-if="connectionStatus" class="connection-info">
          <div class="info-grid">
            <div class="info-card">
              <div class="info-label">Status</div>
              <div class="info-value" :class="isConnected ? 'success' : 'error'">
                {{ connectionStatus.status }}
              </div>
            </div>

            <div class="info-card">
              <div class="info-label">Token</div>
              <div class="info-value" :class="connectionStatus.token_acquired ? 'success' : 'error'">
                {{ connectionStatus.token_acquired ? 'Acquired' : 'Not acquired' }}
              </div>
            </div>

            <div class="info-card full-width">
              <div class="info-label">Base URL</div>
              <div class="info-value mono">{{ connectionStatus.base_url }}</div>
            </div>

            <div class="info-card">
              <div class="info-label">Config</div>
              <div class="info-value mono">{{ connectionStatus.config }}</div>
            </div>

            <div class="info-card">
              <div class="info-label">Available Configs</div>
              <div class="info-value mono">{{ connectionStatus.configurations?.join(', ') || 'N/A' }}</div>
            </div>
          </div>

          <div v-if="connectionError" class="error-box">
            <strong>Error:</strong> {{ connectionError }}
          </div>
        </div>
      </div>

      <!-- DISCOVERY TAB -->
      <div v-if="activeTab === 'discovery'" class="tab-pane">
        <p class="description">Find available IDO (Intelligent Data Objects) collections</p>

        <div class="form-group">
          <label>Custom IDO Names (comma-separated, optional)</label>
          <input
            v-model="customIdoNames"
            type="text"
            placeholder="e.g., SLItems,Items,ItemMaster"
            class="input"
          />
        </div>

        <button
          @click="runDiscovery"
          :disabled="discoveryLoading || !isConnected"
          class="btn btn-primary"
        >
          {{ discoveryLoading ? 'Discovering...' : 'Run Discovery' }}
        </button>

        <div v-if="discoveryResults" class="discovery-results">
          <div v-if="foundIdos.length > 0" class="found-box">
            <div class="result-header">Found IDOs ({{ foundIdos.length }})</div>
            <div class="ido-list">
              <div v-for="ido in foundIdos" :key="ido" class="ido-item">
                <span class="ido-name">{{ ido }}</span>
                <button @click="useIdoForBrowse(ido)" class="btn-link">Browse →</button>
              </div>
            </div>
          </div>

          <div v-if="discoveryResults.not_found.length > 0" class="not-found-box">
            <div class="result-header">Not Found ({{ discoveryResults.not_found.length }})</div>
            <div class="tag-list">
              <span v-for="ido in discoveryResults.not_found" :key="ido" class="tag">
                {{ ido }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- BROWSER TAB -->
      <div v-if="activeTab === 'browser'" class="tab-pane">
        <!-- Step 1: IDO Name + Fetch Fields -->
        <div class="form-group">
          <label>IDO Name * <span class="case-warning">(case-sensitive!)</span></label>
          <div class="input-with-button">
            <input v-model="selectedIdo" type="text" placeholder="e.g., IteCzDics" class="input" />
            <button
              @click="fetchFieldsForIdo"
              :disabled="fetchingFields || !selectedIdo"
              class="btn btn-secondary"
            >
              {{ fetchingFields ? 'Loading...' : '📋 Fetch Fields' }}
            </button>
          </div>
          <small class="help-text">⚠️ Use exact case: IteCzDics, NOT iteczdics</small>
        </div>

        <!-- Step 2: Field Selection (Checkboxes) -->
        <div v-if="availableFields.length > 0" class="field-selector">
          <div class="field-selector-header">
            <label>Select Fields ({{ selectedFields.length }}/{{ filteredFields.length }} shown)</label>
            <div class="field-actions">
              <label class="checkbox-label">
                <input type="checkbox" v-model="hideUdfFields" />
                <span>Hide UDF/Internal</span>
              </label>
              <button @click="selectAllFields" class="btn-link">Select All</button>
              <button @click="deselectAllFields" class="btn-link">Clear</button>
            </div>
          </div>

          <!-- Search Box -->
          <div class="field-search">
            <input
              v-model="fieldSearchQuery"
              type="text"
              placeholder="🔍 Search fields..."
              class="input search-input"
            />
            <span v-if="filteredFields.length !== availableFields.length" class="search-results">
              {{ filteredFields.length }} / {{ availableFields.length }}
            </span>
          </div>

          <div class="field-checkboxes">
            <label
              v-for="field in filteredFields"
              :key="field.name"
              class="field-checkbox"
            >
              <input
                type="checkbox"
                :value="field.name"
                :checked="selectedFields.includes(field.name)"
                @change="toggleField(field.name)"
              />
              <span class="field-name">{{ field.name }}</span>
              <span class="field-type">{{ field.type }}</span>
              <span v-if="field.required" class="field-badge required">required</span>
              <span v-if="field.readOnly" class="field-badge readonly">readonly</span>
            </label>
          </div>
        </div>

        <!-- Step 3: Additional Options -->
        <div class="form-grid">
          <div class="form-group">
            <label>Properties (auto-filled from selection above)</label>
            <input v-model="idoProperties" type="text" placeholder="Or enter manually" class="input" />
          </div>

          <div class="form-group">
            <label>Filter (SQL WHERE)</label>
            <input v-model="idoFilter" type="text" placeholder="Item LIKE 'A%'" class="input" />
            <small class="help-text">SQL syntax: Item = 'ABC' OR Item LIKE 'A%'</small>
          </div>

          <div class="form-group">
            <label>Order By</label>
            <input v-model="idoOrderBy" type="text" placeholder="Item ASC" class="input" />
          </div>

          <div class="form-group">
            <label>Limit per page</label>
            <input v-model.number="idoLimit" type="number" min="-1" max="10000" class="input" />
            <small class="help-text">
              <strong>-1</strong> = API default (200) | <strong>0</strong> = unlimited (API hard limit 200) | <strong>>0</strong> = specific limit
            </small>
          </div>
        </div>

        <div class="action-buttons">
          <button
            @click="browseIdo('FIRST')"
            :disabled="idoDataLoading || !isConnected"
            class="btn btn-primary"
          >
            {{ idoDataLoading ? 'Loading...' : '🔍 Load Data' }}
          </button>

          <button
            v-if="idoData && idoData.length > 0"
            @click="loadMore"
            :disabled="idoDataLoading || !currentBookmark"
            class="btn btn-secondary"
            :title="!currentBookmark ? 'No bookmark - cannot load more' : 'Load next page'"
          >
            {{ idoDataLoading ? 'Loading...' : '➕ Load More' }}
          </button>
        </div>

        <div v-if="idoDataError" class="error-box">{{ idoDataError }}</div>

        <div v-if="idoData && idoData.length > 0" class="data-table-wrapper">
          <div class="table-info-bar">
            <div class="table-info">
              Loaded <strong>{{ idoData.length }}</strong> records
              <span v-if="hasMore" class="more-indicator">• More available</span>
            </div>
            <div v-if="currentBookmark" class="bookmark-info">
              Bookmark: <code>{{ currentBookmark.substring(0, 20) }}...</code>
            </div>
          </div>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="key in Object.keys(idoData[0])" :key="key">{{ key }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in idoData" :key="idx">
                  <td v-for="key in Object.keys(row)" :key="key">{{ row[key] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="idoData && idoData.length === 0" class="empty-state">
          No data found
        </div>
      </div>

      <!-- INFO TAB -->
      <div v-if="activeTab === 'info'" class="tab-pane">
        <p class="description">Get detailed metadata about IDO properties and schema</p>

        <div class="form-row">
          <input
            v-model="selectedIdoForInfo"
            type="text"
            placeholder="Enter IDO name (e.g., SLItems)"
            class="input flex-1"
          />
          <button
            @click="getIdoInfo"
            :disabled="idoInfoLoading || !isConnected"
            class="btn btn-primary"
          >
            {{ idoInfoLoading ? 'Loading...' : 'Get Info' }}
          </button>
        </div>

        <div v-if="idoInfo" class="info-box">
          <pre class="json-preview">{{ JSON.stringify(idoInfo, null, 2) }}</pre>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.infor-admin-module {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

/* Header */
.module-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.module-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
}

.connection-badge .badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: 6px;
  font-size: var(--text-sm);
  font-weight: 500;
}

.badge-success {
  background: var(--success-bg);
  color: var(--success-text);
}

.badge-error {
  background: var(--error-bg);
  color: var(--error-text);
}

.security-note {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.icon {
  width: 16px;
  height: 16px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-secondary);
}

.tab {
  padding: var(--space-3) var(--space-5);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.tab-pane {
  max-width: 1200px;
}

.description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
}

/* Forms */
.form-group {
  margin-bottom: var(--space-4);
}

.form-group label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.flex-1 {
  flex: 1;
}

.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.input:focus {
  outline: none;
  border-color: var(--primary);
}

/* Buttons */
.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: 6px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: var(--text-xs);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
}

.mb-4 {
  margin-bottom: var(--space-4);
}

/* Connection Info */
.connection-info {
  margin-top: var(--space-4);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.info-card {
  padding: var(--space-3);
  background: var(--bg-secondary);
  border-radius: 6px;
}

.info-card.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.info-value {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.mono {
  font-family: 'Monaco', monospace;
  font-size: var(--text-xs);
  word-break: break-all;
}

.info-value.success {
  color: var(--success-text);
}

.info-value.error {
  color: var(--error-text);
}

/* Discovery Results */
.discovery-results {
  margin-top: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.found-box {
  padding: var(--space-4);
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 6px;
}

.not-found-box {
  padding: var(--space-4);
  background: var(--bg-secondary);
  border-radius: 6px;
}

.result-header {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-bottom: var(--space-3);
}

.ido-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ido-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2);
  background: var(--bg-primary);
  border-radius: 4px;
}

.ido-name {
  font-family: 'Monaco', monospace;
  font-size: var(--text-sm);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 4px;
  font-size: var(--text-xs);
  font-family: 'Monaco', monospace;
}

/* Data Table */
.data-table-wrapper {
  margin-top: var(--space-4);
}

.table-info {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.table-scroll {
  overflow-x: auto;
  border: 1px solid var(--border-default);
  border-radius: 6px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th {
  background: var(--bg-secondary);
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-default);
  color: var(--text-primary);
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

/* Error/Info Boxes */
.error-box {
  padding: var(--space-3);
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: 6px;
  color: var(--error-text);
  font-size: var(--text-sm);
  margin-top: var(--space-4);
}

.info-box {
  padding: var(--space-3);
  background: var(--bg-secondary);
  border-radius: 6px;
  margin-top: var(--space-4);
}

.json-preview {
  font-family: 'Monaco', monospace;
  font-size: var(--text-xs);
  color: var(--text-primary);
  overflow-x: auto;
  margin: 0;
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 6px;
}

/* Field Selector (Checkbox UI) */
.input-with-button {
  display: flex;
  gap: var(--space-2);
}

.input-with-button .input {
  flex: 1;
}

.field-selector {
  margin: var(--space-4) 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
}

.field-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-muted);
}

.field-selector-header label {
  margin: 0;
  font-weight: 600;
  color: var(--text-primary);
}

.field-actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  margin: 0;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.field-search {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.field-search .search-input {
  flex: 1;
  margin: 0;
}

.search-results {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent-red);
  cursor: pointer;
  font-size: var(--text-sm);
  padding: 0;
  text-decoration: underline;
}

.btn-link:hover {
  color: var(--accent-red-hover);
}

.field-checkboxes {
  max-height: 300px;
  overflow-y: auto;
  padding: var(--space-2);
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: 4px;
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
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 600;
  text-transform: uppercase;
}

.field-badge.required {
  background: var(--accent-red);
  color: white;
}

.field-badge.readonly {
  background: var(--bg-muted);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.case-warning {
  color: var(--accent-red);
  font-size: var(--text-sm);
  font-weight: 600;
}

.help-text {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

/* Table Info Bar */
.table-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-muted);
  border-radius: 4px;
}

.table-info strong {
  color: var(--primary);
  font-weight: 600;
}

.more-indicator {
  color: var(--success-text);
  font-weight: 500;
}

.bookmark-info {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.bookmark-info code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--primary);
}
</style>
