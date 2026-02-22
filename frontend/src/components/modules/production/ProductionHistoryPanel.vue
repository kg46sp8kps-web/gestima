<script setup lang="ts">
/**
 * Production History Panel - Collapsible panel for displaying production records
 *
 * Filtering by work_center_type (machine type): when user clicks an operation
 * in technology, all production records with same machine type are shown,
 * aggregated per Job (sum of times across matching operations in each VP).
 *
 * All per-piece times are pre-computed in backend — NO calculations here.
 */
import { ref, computed, watch } from 'vue'
import { ChevronRight, ChevronDown, Plus, Info } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { ProductionRecord } from '@/types/productionRecord'
import {
  getProductionRecords,
  createProductionRecord,
  deleteProductionRecord
} from '@/api/productionRecords'
import ProductionRecordsTable from './ProductionRecordsTable.vue'
import ProductionRecordForm from './ProductionRecordForm.vue'

/** Human-readable labels for work center types */
const WC_TYPE_LABELS: Record<string, string> = {
  CNC_LATHE: 'Soustruhy',
  CNC_MILL_3AX: 'Frézy 3ax',
  CNC_MILL_4AX: 'Frézy 4ax',
  CNC_MILL_5AX: 'Frézy 5ax',
  SAW: 'Pily',
  DRILL: 'Vrtačky',
  QUALITY_CONTROL: 'Kontrola',
  MANUAL_ASSEMBLY: 'Montáž',
  EXTERNAL: 'Kooperace',
}

/** Group mill types together for filtering */
const MILL_TYPES = new Set(['CNC_MILL_3AX', 'CNC_MILL_4AX', 'CNC_MILL_5AX'])

function isSameMachineGroup(wcType: string | null, filterType: string): boolean {
  if (!wcType) return false
  if (wcType === filterType) return true
  // Group all mill types together
  if (MILL_TYPES.has(wcType) && MILL_TYPES.has(filterType)) return true
  return false
}

function getFilterLabel(wcType: string): string {
  if (MILL_TYPES.has(wcType)) return 'Frézy'
  return WC_TYPE_LABELS[wcType] ?? wcType
}

interface Props {
  partId: number | null
  workCenterType?: string | null
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  workCenterType: null,
  collapsed: true
})

const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
}>()

const isCollapsed = ref(props.collapsed)
const records = ref<ProductionRecord[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const showAddForm = ref(false)

/** Filtered records by work_center_type (machine group) */
const filteredRecords = computed(() => {
  if (!props.workCenterType) return records.value
  return records.value.filter(r => isSameMachineGroup(r.work_center_type, props.workCenterType!))
})

/** Helper: average of non-null numbers */
function avg(nums: (number | null | undefined)[]): number | null {
  const valid = nums.filter((v): v is number => v != null)
  return valid.length > 0 ? valid.reduce((a, b) => a + b, 0) / valid.length : null
}

/** Summary computed from filtered records
 * In machine-type mode: aggregates SUM of times per job, then averages across jobs
 * In default mode: simple average across all records
 */
const summary = computed(() => {
  const recs = filteredRecords.value
  if (recs.length === 0) return null

  // Group by infor_order_number to get unique jobs
  const jobMap = new Map<string, { batchQty: number; sumActual: number; sumPlanned: number; sumSetupActual: number; sumSetupPlanned: number; manningValues: number[]; count: number }>()

  for (const r of recs) {
    const key = r.infor_order_number ?? `manual_${r.id}`
    if (!jobMap.has(key)) {
      jobMap.set(key, { batchQty: r.batch_quantity ?? 0, sumActual: 0, sumPlanned: 0, sumSetupActual: 0, sumSetupPlanned: 0, manningValues: [], count: 0 })
    }
    const job = jobMap.get(key)!
    if (r.actual_time_min != null) job.sumActual += r.actual_time_min
    if (r.planned_time_min != null) job.sumPlanned += r.planned_time_min
    if (r.actual_setup_min != null) job.sumSetupActual += r.actual_setup_min
    if (r.planned_setup_min != null) job.sumSetupPlanned += r.planned_setup_min
    if (r.actual_manning_coefficient != null) job.manningValues.push(r.actual_manning_coefficient)
    job.count++
  }

  const jobs = Array.from(jobMap.values())
  const totalPieces = jobs.reduce((a, j) => a + j.batchQty, 0)

  // For machine-type mode: use per-job sums for avg/min/max
  const jobActualSums = jobs.filter(j => j.count > 0).map(j => j.sumActual)
  const jobPlannedSums = jobs.filter(j => j.count > 0).map(j => j.sumPlanned)
  const jobSetupActualSums = jobs.filter(j => j.count > 0).map(j => j.sumSetupActual)
  const jobSetupPlannedSums = jobs.filter(j => j.count > 0).map(j => j.sumSetupPlanned)

  // Manning: average across all records (not per-job — it's a coefficient, not time)
  const allManningValues = jobs.flatMap(j => j.manningValues)

  return {
    total_records: recs.length,
    total_jobs: jobMap.size,
    avg_actual_time_min: jobActualSums.length > 0 ? jobActualSums.reduce((a, b) => a + b, 0) / jobActualSums.length : null,
    min_actual_time_min: jobActualSums.length > 0 ? Math.min(...jobActualSums) : null,
    max_actual_time_min: jobActualSums.length > 0 ? Math.max(...jobActualSums) : null,
    total_pieces: totalPieces,
    avg_planned_time_min: jobPlannedSums.length > 0 ? jobPlannedSums.reduce((a, b) => a + b, 0) / jobPlannedSums.length : null,
    avg_setup_planned: jobSetupPlannedSums.length > 0 ? jobSetupPlannedSums.reduce((a, b) => a + b, 0) / jobSetupPlannedSums.length : null,
    avg_setup_actual: jobSetupActualSums.length > 0 ? jobSetupActualSums.reduce((a, b) => a + b, 0) / jobSetupActualSums.length : null,
    avg_manning: allManningValues.length > 0 ? allManningValues.reduce((a, b) => a + b, 0) / allManningValues.length : null,
  }
})

watch(() => props.partId, async (newPartId) => {
  // Reset stale data immediately on part switch
  records.value = []
  error.value = null
  showAddForm.value = false

  // Always load records (summary in header needs data even when collapsed)
  if (newPartId) {
    await loadRecords()
  }
}, { immediate: true })

watch(isCollapsed, async (collapsed) => {
  emit('update:collapsed', collapsed)
  // Re-fetch on expand only if no records loaded yet (e.g. initial mount)
  if (!collapsed && props.partId && records.value.length === 0) {
    await loadRecords()
  }
})

async function loadRecords() {
  if (!props.partId) return

  loading.value = true
  error.value = null

  try {
    records.value = await getProductionRecords(props.partId)
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

async function handleAddRecord(record: Partial<ProductionRecord>) {
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
        <span v-if="workCenterType" class="filter-badge">{{ getFilterLabel(workCenterType) }}</span>
        <span v-if="summary" class="record-badge">{{ summary.total_jobs }}</span>
        <!-- Collapsed summary -->
        <span v-if="isCollapsed && summary" class="collapsed-summary">
          <!-- Machine-type filtered mode: show per-job sum averages -->
          <template v-if="workCenterType">
            <span class="cs-label">Ø Σ pl</span>
            <span class="cs-item">{{ summary.avg_planned_time_min?.toFixed(2) ?? '—' }}</span>
            <span class="cs-sep">|</span>
            <span class="cs-label">Ø Σ re</span>
            <span class="cs-item highlight">{{ summary.avg_actual_time_min?.toFixed(2) ?? '—' }}</span>
            <span class="cs-sep">|</span>
            <span class="cs-label">Man</span>
            <span class="cs-item">{{ summary.avg_manning != null ? summary.avg_manning.toFixed(0) + '%' : '—' }}</span>
            <span class="cs-sep">|</span>
            <span class="cs-item">{{ summary.total_jobs }} VP</span>
          </template>
          <!-- Default: compact summary -->
          <template v-else>
            <span class="cs-label">Ø</span>
            <span class="cs-item">{{ summary.avg_actual_time_min?.toFixed(2) ?? '—' }}</span>
            <span class="cs-sep">|</span>
            <span class="cs-item">{{ summary.total_pieces }} ks</span>
          </template>
        </span>
      </div>
    </div>

    <div v-if="!isCollapsed" class="panel-content">
      <div v-if="loading" class="loading-state">
        <span class="loading-spinner"></span>
        <span>Načítám záznamy...</span>
      </div>

      <div v-if="error" class="error-bar">{{ error }}</div>

      <div v-if="!loading && summary" class="summary-ribbon">
        <div class="summary-item">
          <span class="summary-label">Ø stroj:</span>
          <span class="summary-value">{{ summary.avg_actual_time_min?.toFixed(2) ?? '—' }} min</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Min:</span>
          <span class="summary-value">{{ summary.min_actual_time_min?.toFixed(2) ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Max:</span>
          <span class="summary-value">{{ summary.max_actual_time_min?.toFixed(2) ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Manning:</span>
          <span class="summary-value">{{ summary.avg_manning != null ? summary.avg_manning.toFixed(0) + '%' : '—' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Dávky:</span>
          <span class="summary-value">{{ summary.total_jobs }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Celkem:</span>
          <span class="summary-value">{{ summary.total_pieces }} ks</span>
        </div>
      </div>

      <div v-if="!loading && filteredRecords.length === 0 && !showAddForm" class="empty-state">
        <Info :size="ICON_SIZE.LARGE" class="empty-icon" />
        <p>Žádné výrobní záznamy</p>
      </div>

      <ProductionRecordsTable
        v-if="!loading && filteredRecords.length > 0"
        :records="filteredRecords"
        :machineTypeFilter="!!workCenterType"
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
  background: var(--surface);
}
.panel-header {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 6px var(--pad);
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface);
}
.panel-header:hover { background: var(--raised); }
.header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}
.chevron { transition: transform 0.2s; color: var(--t3); }
.filter-badge {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--red);
  padding: 0 4px;
  background: rgba(37,99,235,0.1);
  border-radius: var(--rs);
}
.record-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 4px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
}
.collapsed-summary {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  font-family: var(--mono);
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
}
.cs-label { color: var(--t3); font-weight: 500; font-family: inherit; }
.cs-item.highlight { color: var(--t1); font-weight: 700; }
.cs-sep { color: var(--t3); }
.panel-content { padding: 0 var(--pad) var(--pad); }
.error-bar { padding: 6px var(--pad); background: var(--red-10); color: var(--red); border-radius: var(--rs); font-size: var(--fs); margin-bottom: var(--pad); }
.summary-ribbon { display: flex; flex-wrap: wrap; gap: 12px; padding: 6px var(--pad); background: var(--raised); border-radius: var(--rs); margin-bottom: var(--pad); }
.summary-item { display: flex; gap: 4px; font-size: var(--fs); }
.summary-label { color: var(--t3); }
.summary-value { font-weight: 600; color: var(--t1); font-family: var(--mono); }
.empty-icon { opacity: 0.5; }
.btn-add { display: inline-flex; align-items: center; gap: 6px; padding: 6px var(--pad); background: transparent; border: 1px solid var(--b2); border-radius: var(--r); font-size: var(--fs); cursor: pointer; color: var(--t1); width: 100%; justify-content: center; }
.btn-add:hover { border-color: var(--red); color: var(--red); }
</style>
