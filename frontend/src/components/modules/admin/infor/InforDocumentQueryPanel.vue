<script setup lang="ts">
/**
 * Document Query Panel — generic IDO loading (same pattern as PartsImportTab)
 *
 * Uses /api/infor/ido/{ido_name}/data endpoint with pre-filled defaults
 * for SLDocumentObjects_Exts.
 *
 * Emits:
 *   data-loaded(rows) — raw IDO rows fetched from Infor
 *   stage-all         — trigger preview/matching step in parent
 */

import { ref } from 'vue'
import { getInforIdoData, type InforIdoDataParams } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { Search, Download } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import InforDataTable from './InforDataTable.vue'

const DEFAULT_IDO = 'SLDocumentObjects_Exts'
const DEFAULT_PROPERTIES = 'DocumentName,DocumentExtension,DocumentType,RowPointer,Sequence,Description,StorageMethod'
const DEFAULT_FILTER = "DocumentType IN ('Výkres-platný', 'PDF', 'Výkres')"

const props = defineProps<{
  isConnected: boolean
  inforDataCount: number
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'data-loaded', rows: Record<string, unknown>[]): void
  (e: 'stage-all'): void
}>()

const uiStore = useUiStore()

const selectedIdo = ref(DEFAULT_IDO)
const idoProperties = ref(DEFAULT_PROPERTIES)
const idoFilter = ref(DEFAULT_FILTER)
const idoLimit = ref(5000)
const inforData = ref<Record<string, unknown>[]>([])
const localLoading = ref(false)

async function loadInforData() {
  if (!props.isConnected) { uiStore.showError('Nejste připojeni k Infor ION API'); return }
  if (!idoProperties.value) { uiStore.showError('Žádné sloupce k načtení'); return }
  localLoading.value = true
  try {
    const params: InforIdoDataParams = {
      properties: idoProperties.value,
      limit: idoLimit.value,
      ...(idoFilter.value ? { filter: idoFilter.value } : {})
    }
    const data = await getInforIdoData(selectedIdo.value, params)
    inforData.value = data.data || []
    emit('data-loaded', inforData.value)
    uiStore.showSuccess(`Načteno ${inforData.value.length} řádků z ${selectedIdo.value}`)
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    uiStore.showError(err.response?.data?.detail || err.message || 'Chyba načtení dat')
  } finally {
    localLoading.value = false
  }
}
</script>

<template>
  <div class="section">
    <h4>1. Načíst dokumenty z Infor</h4>

    <div class="query-row">
      <div class="form-group">
        <label>IDO</label>
        <input v-model="selectedIdo" type="text" class="input" />
      </div>
      <div class="form-group fg-wide">
        <label>Properties</label>
        <input v-model="idoProperties" type="text" class="input" />
      </div>
    </div>
    <div class="query-row">
      <div class="form-group fg-wide">
        <label>Filter (SQL WHERE)</label>
        <input v-model="idoFilter" type="text" class="input" :placeholder="DEFAULT_FILTER" />
      </div>
      <div class="form-group">
        <label>Limit</label>
        <input v-model.number="idoLimit" type="number" class="input" min="-1" max="50000" />
      </div>
    </div>

    <div class="toolbar">
      <button @click="loadInforData" :disabled="localLoading || !isConnected" class="btn-ghost">
        <Search :size="ICON_SIZE.STANDARD" /> {{ localLoading ? 'Načítám...' : 'Načíst dokumenty' }}
      </button>
      <button @click="emit('stage-all')" :disabled="inforDataCount === 0 || loading || localLoading" class="btn-ghost">
        <Download :size="ICON_SIZE.STANDARD" /> Napárovat na díly ({{ inforDataCount }})
      </button>
    </div>

    <InforDataTable :data="inforData" />
  </div>
</template>

<style scoped>
.section { margin-bottom: var(--space-6); }
h4 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-3) 0; }
.query-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
.query-row .fg-wide { flex: 3; }
.toolbar { display: flex; gap: var(--space-2); margin: var(--space-3) 0; flex-wrap: wrap; }
</style>
