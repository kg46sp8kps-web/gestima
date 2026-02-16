<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'
import { Search, FileText, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforFieldSelector from './InforFieldSelector.vue'
import InforQueryForm from './InforQueryForm.vue'
import InforDataTable from './InforDataTable.vue'

const props = defineProps<{
  isConnected: boolean
  initialIdo?: string
}>()

const selectedIdo = ref('')
const idoProperties = ref('')
const idoFilter = ref('')
const idoOrderBy = ref('')
const idoLimit = ref(100)
const idoData = ref<Record<string, unknown>[] | null>(null)
const idoDataLoading = ref(false)
const idoDataError = ref<string | null>(null)
const availableFields = ref<Array<{ name: string; type: string; required: boolean; readOnly: boolean }>>([])
const selectedFields = ref<string[]>([])
const fetchingFields = ref(false)
const hideUdfFields = ref(true)

watch(() => props.initialIdo, (newIdo) => { if (newIdo) selectedIdo.value = newIdo }, { immediate: true })

async function fetchFieldsForIdo() {
  if (!selectedIdo.value) {
    await alert({ title: 'Chyba validace', message: 'Please enter IDO name first', type: 'warning' })
    return
  }
  fetchingFields.value = true
  availableFields.value = []
  selectedFields.value = []
  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/info`)
    const fields = response.data.info || []
    availableFields.value = fields.map((field: { name: string; dataType?: string; required?: boolean; readOnly?: boolean }) => ({
      name: field.name,
      type: field.dataType || 'String',
      required: field.required || false,
      readOnly: field.readOnly || false
    }))
    selectedFields.value = availableFields.value.filter((f) => f.required && !f.readOnly).map((f) => f.name).slice(0, 5)
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    await alert({ title: 'Chyba', message: 'Failed to fetch fields: ' + (err.response?.data?.detail || err.message), type: 'error' })
  } finally {
    fetchingFields.value = false
  }
}

function toggleField(fieldName: string) {
  const index = selectedFields.value.indexOf(fieldName)
  if (index > -1) {
    selectedFields.value.splice(index, 1)
  } else {
    selectedFields.value.push(fieldName)
  }
  idoProperties.value = selectedFields.value.join(',')
}

function selectAllFields() {
  selectedFields.value = availableFields.value.map((f) => f.name)
  idoProperties.value = selectedFields.value.join(',')
}

function deselectAllFields() {
  selectedFields.value = []
  idoProperties.value = ''
}

async function browseIdo() {
  if (!selectedIdo.value || !idoProperties.value) {
    await alert({ title: 'Chyba validace', message: 'Please select IDO and specify properties', type: 'warning' })
    return
  }
  idoDataLoading.value = true
  idoDataError.value = null
  idoData.value = null
  try {
    const params: Record<string, string | number> = { properties: idoProperties.value, limit: idoLimit.value }
    if (idoFilter.value) params.filter = idoFilter.value
    if (idoOrderBy.value) params.order_by = idoOrderBy.value
    const response = await axios.get(`/api/infor/ido/${selectedIdo.value}/data`, { params })
    idoData.value = response.data.data || []
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    idoDataError.value = err.response?.data?.detail || err.message || 'Unknown error'
  } finally {
    idoDataLoading.value = false
  }
}

defineExpose({ setIdo: (ido: string) => (selectedIdo.value = ido) })
</script>

<template>
  <div class="browser-tab">
    <div class="form-group">
      <label>IDO Name * <span class="case-warning">(case-sensitive!)</span></label>
      <div class="input-with-button">
        <input v-model="selectedIdo" type="text" placeholder="e.g., IteCzDics" class="input" />
        <button @click="fetchFieldsForIdo" :disabled="fetchingFields || !selectedIdo" class="btn btn-secondary">
          <FileText :size="ICON_SIZE.STANDARD" v-if="!fetchingFields" />
          {{ fetchingFields ? 'Loading...' : 'Fetch Fields' }}
        </button>
      </div>
      <small class="help-text warning-text"><AlertTriangle :size="ICON_SIZE.SMALL" /> Use exact case</small>
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
      :properties="idoProperties"
      :filter="idoFilter"
      :order-by="idoOrderBy"
      :limit="idoLimit"
      @update:properties="idoProperties = $event"
      @update:filter="idoFilter = $event"
      @update:order-by="idoOrderBy = $event"
      @update:limit="idoLimit = $event"
    />
    <button @click="browseIdo" :disabled="idoDataLoading || !props.isConnected" class="btn btn-primary">
      <Search :size="ICON_SIZE.STANDARD" v-if="!idoDataLoading" />
      {{ idoDataLoading ? 'Loading...' : 'Load Data' }}
    </button>
    <div v-if="idoDataError" class="error-box">{{ idoDataError }}</div>
    <InforDataTable :data="idoData || []" />
  </div>
</template>

<style scoped>
.browser-tab { padding: var(--space-4); max-width: 1200px; overflow: auto; }
.form-group { margin-bottom: var(--space-3); }
.form-group label { display: block; font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); margin-bottom: var(--space-1); }
.input { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-input); color: var(--text-primary); font-size: var(--text-sm); }
.input:focus { outline: none; border-color: var(--color-primary); }
.input-with-button { display: flex; gap: var(--space-2); }
.input-with-button .input { flex: 1; }
.btn { padding: var(--space-2) var(--space-4); border: none; border-radius: var(--radius-md); font-size: var(--text-sm); font-weight: 500; cursor: pointer; transition: all var(--duration-fast); display: inline-flex; align-items: center; gap: var(--space-2); }
.btn-primary { background: transparent; color: var(--text-primary); border: 1px solid var(--border-default); }
.btn-primary:hover:not(:disabled) { background: var(--brand-subtle); border-color: var(--brand); color: var(--brand-text); }
.btn-secondary { background: var(--bg-raised); color: var(--text-primary); border: 1px solid var(--border-default); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.case-warning { color: var(--color-primary); font-size: var(--text-sm); font-weight: 600; }
.help-text { display: block; margin-top: var(--space-1); font-size: var(--text-xs); color: var(--text-secondary); }
.warning-text { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-warning); }
.error-box { padding: var(--space-3); background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius-md); color: var(--color-danger); font-size: var(--text-sm); margin-top: var(--space-4); }
</style>
