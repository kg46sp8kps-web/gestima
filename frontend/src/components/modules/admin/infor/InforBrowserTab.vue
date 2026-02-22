<script setup lang="ts">
import { ref, watch } from 'vue'
import { getInforIdoInfo, getInforIdoData, type InforIdoDataParams } from '@/api/infor-import'
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
    const data = await getInforIdoInfo(selectedIdo.value)
    const fields = data.info || []
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
    const params: InforIdoDataParams = {
      properties: idoProperties.value,
      limit: idoLimit.value,
      ...(idoFilter.value ? { filter: idoFilter.value } : {}),
      ...(idoOrderBy.value ? { order_by: idoOrderBy.value } : {})
    }
    const data = await getInforIdoData(selectedIdo.value, params)
    idoData.value = data.data || []
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
.browser-tab { padding: 12px; max-width: 1200px; overflow: auto; }
.input-with-button { display: flex; gap: 6px; }
.input-with-button .input { flex: 1; }
.case-warning { color: var(--red); font-size: var(--fs); font-weight: 600; }
.help-text { display: block; margin-top: 4px; font-size: var(--fs); color: var(--t3); }
.warning-text { display: inline-flex; align-items: center; gap: 4px; color: var(--warn); }
.error-box { padding: var(--pad); background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.15); border-radius: var(--r); color: var(--err); font-size: var(--fs); margin-top: 12px; }
</style>
