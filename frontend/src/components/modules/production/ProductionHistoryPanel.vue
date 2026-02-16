<script setup lang="ts">
/**
 * Production History Panel - Collapsible panel for displaying production records
 * Can be used standalone or embedded in OperationsRightPanel
 */
import { ref, watch } from 'vue'
import { ChevronRight, ChevronDown, Plus, Info } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { ProductionRecord, ProductionSummary } from '@/types/productionRecord'
import {
  getProductionRecords,
  getProductionSummary,
  createProductionRecord,
  deleteProductionRecord
} from '@/api/productionRecords'
import ProductionRecordsTable from './ProductionRecordsTable.vue'
import ProductionRecordForm from './ProductionRecordForm.vue'

interface Props {
  partId: number | null
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: true
})

const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
}>()

const isCollapsed = ref(props.collapsed)
const records = ref<ProductionRecord[]>([])
const summary = ref<ProductionSummary | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const showAddForm = ref(false)

watch(() => props.partId, async (newPartId) => {
  if (newPartId && !isCollapsed.value) {
    await loadRecords()
  }
}, { immediate: true })

watch(isCollapsed, async (collapsed) => {
  emit('update:collapsed', collapsed)
  if (!collapsed && props.partId) {
    await loadRecords()
  }
})

async function loadRecords() {
  if (!props.partId) return

  loading.value = true
  error.value = null

  try {
    const [recordsData, summaryData] = await Promise.all([
      getProductionRecords(props.partId),
      getProductionSummary(props.partId)
    ])
    records.value = recordsData
    summary.value = summaryData
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Nepodařilo se načíst výrobní záznamy'
  } finally {
    loading.value = false
  }
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function toggleAddForm() {
  showAddForm.value = !showAddForm.value
}

async function handleAddRecord(record: any) {
  if (!props.partId) return

  loading.value = true
  error.value = null

  try {
    await createProductionRecord({
      part_id: props.partId,
      production_date: record.production_date || null,
      batch_quantity: record.batch_quantity,
      operation_seq: record.operation_seq,
      planned_time_min: record.planned_time_min,
      actual_time_min: record.actual_time_min,
      infor_order_number: record.infor_order_number || null,
      notes: record.notes || null,
      source: 'manual'
    })

    showAddForm.value = false
    await loadRecords()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Nepodařilo se přidat záznam'
  } finally {
    loading.value = false
  }
}

async function handleDeleteRecord(id: number) {
  if (!confirm('Opravdu smazat tento záznam?')) return

  loading.value = true
  error.value = null

  try {
    await deleteProductionRecord(id)
    await loadRecords()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Nepodařilo se smazat záznam'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="production-panel">
    <div class="panel-header" @click="toggleCollapse">
      <div class="header-title">
        <component :is="isCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" class="chevron" />
        <span class="title-text">Výrobní historie</span>
        <span v-if="summary" class="record-badge">{{ summary.total_records }}</span>
      </div>
    </div>

    <div v-if="!isCollapsed" class="panel-content">
      <div v-if="loading" class="loading-state">
        <span class="loading-spinner"></span>
        <span>Načítám záznamy...</span>
      </div>

      <div v-if="error" class="error-bar">{{ error }}</div>

      <div v-if="!loading && summary && summary.total_records > 0" class="summary-ribbon">
        <div class="summary-item">
          <span class="summary-label">Ø čas:</span>
          <span class="summary-value">{{ summary.avg_actual_time_min?.toFixed(1) ?? '—' }} min</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Min:</span>
          <span class="summary-value">{{ summary.min_actual_time_min?.toFixed(1) ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Max:</span>
          <span class="summary-value">{{ summary.max_actual_time_min?.toFixed(1) ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Celkem:</span>
          <span class="summary-value">{{ summary.total_pieces_produced }} ks</span>
        </div>
      </div>

      <div v-if="!loading && records.length === 0 && !showAddForm" class="empty-state">
        <Info :size="ICON_SIZE.LARGE" class="empty-icon" />
        <p>Žádné výrobní záznamy</p>
      </div>

      <ProductionRecordsTable
        v-if="!loading && records.length > 0"
        :records="records"
        @delete="handleDeleteRecord"
      />

      <ProductionRecordForm
        v-if="showAddForm"
        @submit="handleAddRecord"
        @cancel="toggleAddForm"
      />

      <button v-if="!showAddForm" class="btn-add" @click="toggleAddForm">
        <Plus :size="ICON_SIZE.SMALL" />
        <span>Přidat záznam</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.production-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  margin-bottom: var(--space-3);
}
.panel-header {
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-header:hover { background: var(--bg-raised); }
.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}
.chevron { transition: transform 0.2s; }
.record-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 var(--space-1);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
}
.panel-content { padding: 0 var(--space-3) var(--space-3); }
.loading-state {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-bar {
  padding: var(--space-2) var(--space-3);
  background: rgba(153, 27, 27, 0.1);
  color: var(--color-brand);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  margin-bottom: var(--space-3);
}
.summary-ribbon {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
}
.summary-item { display: flex; gap: var(--space-1); font-size: var(--text-xs); }
.summary-label { color: var(--text-tertiary); }
.summary-value { font-weight: 600; color: var(--text-primary); font-family: 'Space Mono', monospace; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6);
  color: var(--text-tertiary);
}
.empty-icon { opacity: 0.5; }
.btn-add {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--text-primary);
  width: 100%;
  justify-content: center;
}
.btn-add:hover { border-color: var(--color-brand); color: var(--color-brand); }
</style>
