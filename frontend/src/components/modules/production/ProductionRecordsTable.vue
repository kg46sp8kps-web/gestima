<script setup lang="ts">
/**
 * Production Records Table — grouped by Job (collapsible rows)
 *
 * Two modes:
 * 1. Default (no filter): grouped by Job, avg actual time per record
 * 2. machineTypeFilter: grouped by Job, SUM of times across matching operations
 *    — shows aggregated row per VP with sum of machine times
 *
 * All per-piece times are pre-computed in backend — NO calculations here.
 */
import { ref, computed } from 'vue'
import { ChevronRight, ChevronDown, Trash2 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { ProductionRecord } from '@/types/productionRecord'

interface Props {
  records: ProductionRecord[]
  machineTypeFilter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  machineTypeFilter: false
})

const emit = defineEmits<{
  (e: 'delete', id: number): void
}>()

// Expanded state
const expandedJobs = ref<Set<string>>(new Set())

function toggleJob(key: string) {
  if (expandedJobs.value.has(key)) {
    expandedJobs.value.delete(key)
  } else {
    expandedJobs.value.add(key)
  }
}

/** Group records by infor_order_number (Job) */
interface JobGroup {
  key: string
  orderNumber: string
  batchQuantity: number | null
  operationCount: number
  records: ProductionRecord[]
  avgActualTime: number | null
  // Aggregated sums (for machineTypeFilter mode)
  sumActualTime: number | null
  sumPlannedTime: number | null
  sumSetupActual: number | null
  sumSetupPlanned: number | null
  avgManning: number | null
  productionDate: string | null
}

const jobGroups = computed<JobGroup[]>(() => {
  const map = new Map<string, ProductionRecord[]>()
  for (const r of props.records) {
    const key = r.infor_order_number ?? `manual_${r.id}`
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }

  const groups: JobGroup[] = []
  for (const [key, recs] of map) {
    // Sort operations by seq within group
    recs.sort((a, b) => (a.operation_seq ?? 0) - (b.operation_seq ?? 0))

    const times = recs.map(r => r.actual_time_min).filter((v): v is number => v != null)

    // Sum aggregations for machine-type mode
    let sumActual = 0, sumPlanned = 0, sumSetupActual = 0, sumSetupPlanned = 0
    const manningVals: number[] = []
    for (const r of recs) {
      if (r.actual_time_min != null) sumActual += r.actual_time_min
      if (r.planned_time_min != null) sumPlanned += r.planned_time_min
      if (r.actual_setup_min != null) sumSetupActual += r.actual_setup_min
      if (r.planned_setup_min != null) sumSetupPlanned += r.planned_setup_min
      if (r.actual_manning_coefficient != null) manningVals.push(r.actual_manning_coefficient)
    }

    groups.push({
      key,
      orderNumber: recs[0]?.infor_order_number ?? 'Ruční',
      batchQuantity: recs[0]?.batch_quantity ?? null,
      operationCount: recs.length,
      records: recs,
      avgActualTime: times.length > 0 ? times.reduce((a, b) => a + b, 0) / times.length : null,
      sumActualTime: times.length > 0 ? sumActual : null,
      sumPlannedTime: recs.some(r => r.planned_time_min != null) ? sumPlanned : null,
      sumSetupActual: recs.some(r => r.actual_setup_min != null) ? sumSetupActual : null,
      sumSetupPlanned: recs.some(r => r.planned_setup_min != null) ? sumSetupPlanned : null,
      avgManning: manningVals.length > 0 ? manningVals.reduce((a, b) => a + b, 0) / manningVals.length : null,
      productionDate: recs[0]?.production_date ?? null,
    })
  }

  return groups
})

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '—'
  return val.toFixed(decimals)
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return '—'
  return val.toFixed(0) + '%'
}
</script>

<template>
  <div class="records-table">
    <!-- MACHINE TYPE FILTER MODE: grouped by Job with SUM of times -->
    <template v-if="machineTypeFilter">
      <!-- Header -->
      <div class="mt-header-row">
        <div class="mt-expand"></div>
        <div class="mt-order">Příkaz</div>
        <div class="mt-batch">Ks</div>
        <div class="mt-ops">OP</div>
        <div class="mt-val">Σ Setup pl</div>
        <div class="mt-val">Σ Stroj pl</div>
        <div class="mt-val">Σ Setup re</div>
        <div class="mt-val highlight-header">Σ Stroj re</div>
        <div class="mt-pct">Man</div>
        <div class="mt-date">Datum</div>
      </div>

      <!-- Job rows with sums -->
      <div v-for="group in jobGroups" :key="group.key" class="job-group">
        <div class="mt-row" @click="toggleJob(group.key)">
          <div class="mt-expand">
            <component :is="expandedJobs.has(group.key) ? ChevronDown : ChevronRight" :size="ICON_SIZE.SMALL" class="chevron-icon" />
          </div>
          <div class="mt-order">{{ group.orderNumber }}</div>
          <div class="mt-batch mono">{{ group.batchQuantity ?? '—' }}</div>
          <div class="mt-ops mono">{{ group.operationCount }}</div>
          <div class="mt-val mono">{{ fmt(group.sumSetupPlanned, 1) }}</div>
          <div class="mt-val mono">{{ fmt(group.sumPlannedTime) }}</div>
          <div class="mt-val mono">{{ fmt(group.sumSetupActual, 1) }}</div>
          <div class="mt-val mono highlight">{{ fmt(group.sumActualTime) }}</div>
          <div class="mt-pct mono">{{ fmtPct(group.avgManning) }}</div>
          <div class="mt-date mono">{{ group.productionDate?.slice(5) ?? '—' }}</div>
        </div>

        <!-- Expanded: individual operation detail rows -->
        <template v-if="expandedJobs.has(group.key)">
          <div class="op-header-row mt-sub">
            <div class="op-seq">OP</div>
            <div class="op-wc">Pracoviště</div>
            <div class="op-val">Setup pl</div>
            <div class="op-val">Stroj pl</div>
            <div class="op-val">Setup re</div>
            <div class="op-val highlight-header">Stroj re</div>
            <div class="op-pct">Man re</div>
            <div class="op-action"></div>
          </div>
          <div v-for="record in group.records" :key="record.id" class="op-row mt-sub">
            <div class="op-seq">{{ record.operation_seq ?? '—' }}</div>
            <div class="op-wc">{{ record.work_center_name ?? '—' }}</div>
            <div class="op-val mono">{{ fmt(record.planned_setup_min, 1) }}</div>
            <div class="op-val mono">{{ fmt(record.planned_time_min) }}</div>
            <div class="op-val mono">{{ fmt(record.actual_setup_min, 1) }}</div>
            <div class="op-val mono highlight">{{ fmt(record.actual_time_min) }}</div>
            <div class="op-pct mono">{{ fmtPct(record.actual_manning_coefficient) }}</div>
            <div class="op-action">
              <button class="btn-icon" title="Smazat" @click.stop="emit('delete', record.id)">
                <Trash2 :size="ICON_SIZE.SMALL" />
              </button>
            </div>
          </div>
        </template>
      </div>
    </template>

    <!-- GROUPED MODE: default Job grouping (no filter) -->
    <template v-else>
      <!-- Header -->
      <div class="job-header-row">
        <div class="jh-expand"></div>
        <div class="jh-order">Příkaz</div>
        <div class="jh-batch">Ks</div>
        <div class="jh-ops">OP</div>
        <div class="jh-time">Ø stroj real</div>
      </div>

      <!-- Job rows -->
      <div v-for="group in jobGroups" :key="group.key" class="job-group">
        <!-- Job summary row (collapsible) -->
        <div class="job-row" @click="toggleJob(group.key)">
          <div class="jh-expand">
            <component :is="expandedJobs.has(group.key) ? ChevronDown : ChevronRight" :size="ICON_SIZE.SMALL" class="chevron-icon" />
          </div>
          <div class="jh-order">{{ group.orderNumber }}</div>
          <div class="jh-batch mono">{{ group.batchQuantity ?? '—' }}</div>
          <div class="jh-ops mono">{{ group.operationCount }}</div>
          <div class="jh-time mono highlight">{{ fmt(group.avgActualTime) }}</div>
        </div>

        <!-- Expanded: operation detail rows -->
        <template v-if="expandedJobs.has(group.key)">
          <!-- Sub-header -->
          <div class="op-header-row">
            <div class="op-seq">OP</div>
            <div class="op-wc">Pracoviště</div>
            <div class="op-val">Setup pl</div>
            <div class="op-val">Stroj pl</div>
            <div class="op-val">Obsl pl</div>
            <div class="op-pct">Man pl</div>
            <div class="op-val">Setup re</div>
            <div class="op-val highlight-header">Stroj re</div>
            <div class="op-val">Obsl re</div>
            <div class="op-pct">Man re</div>
            <div class="op-action"></div>
          </div>
          <div v-for="record in group.records" :key="record.id" class="op-row">
            <div class="op-seq">{{ record.operation_seq ?? '—' }}</div>
            <div class="op-wc">{{ record.work_center_name ?? '—' }}</div>
            <div class="op-val mono">{{ fmt(record.planned_setup_min, 1) }}</div>
            <div class="op-val mono">{{ fmt(record.planned_time_min) }}</div>
            <div class="op-val mono">{{ fmt(record.planned_labor_time_min) }}</div>
            <div class="op-pct mono">{{ fmtPct(record.manning_coefficient) }}</div>
            <div class="op-val mono">{{ fmt(record.actual_setup_min, 1) }}</div>
            <div class="op-val mono highlight">{{ fmt(record.actual_time_min) }}</div>
            <div class="op-val mono">{{ fmt(record.actual_labor_time_min) }}</div>
            <div class="op-pct mono">{{ fmtPct(record.actual_manning_coefficient) }}</div>
            <div class="op-action">
              <button class="btn-icon" title="Smazat" @click.stop="emit('delete', record.id)">
                <Trash2 :size="ICON_SIZE.SMALL" />
              </button>
            </div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Machine-type filter mode: grouped by Job with SUM of times */
.mt-header-row, .mt-row {
  display: grid;
  grid-template-columns: 20px minmax(60px, 1fr) 40px 28px 52px 52px 52px 52px 40px 48px;
  gap: 4px;
  padding: 4px 6px;
}

.mt-header-row {
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  border-bottom: 1px solid var(--b2);
  font-size: var(--fs);
}

.mt-row {
  cursor: pointer;
  border-bottom: 1px solid var(--b1);
  color: var(--t1);
  font-weight: 500;
}
.mt-row:hover { background: var(--raised); }

.mt-expand { display: flex; align-items: center; }
.mt-order { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mt-batch { text-align: right; }
.mt-ops { text-align: center; }
.mt-val { text-align: right; }
.mt-pct { text-align: right; }
.mt-date { font-size: var(--fs); color: var(--t3); }

/* Sub-rows in machine-type filter mode (narrower columns) */
.op-header-row.mt-sub, .op-row.mt-sub {
  grid-template-columns: 32px 1fr 48px 52px 48px 52px 44px 28px;
}

.records-table { margin-bottom: 6px; overflow-x: auto; font-size: var(--fs); }
.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.highlight { font-weight: 600; color: var(--t1); }
.highlight-header { font-weight: 700; }

/* Job header + rows */
.job-header-row {
  display: grid;
  grid-template-columns: 20px 1fr 48px 32px 72px;
  gap: 4px;
  padding: 4px 6px;
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  border-bottom: 1px solid var(--b2);
}

.job-row {
  display: grid;
  grid-template-columns: 20px 1fr 48px 32px 72px;
  gap: 4px;
  padding: 4px 6px;
  cursor: pointer;
  border-bottom: 1px solid var(--b1);
  color: var(--t1);
  font-weight: 500;
}
.job-row:hover { background: var(--raised); }

.chevron-icon { color: var(--t3); transition: transform 0.15s; }

.job-group { border-bottom: 1px solid var(--b2); }
.job-group:last-child { border-bottom: none; }

/* Operation sub-rows (expanded) */
.op-header-row {
  display: grid;
  grid-template-columns: 32px 1fr 48px 52px 52px 44px 48px 52px 52px 44px 28px;
  gap: 4px;
  padding: 2px 6px 2px calc(6px + 20px);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  background: var(--raised);
  border-bottom: 1px solid var(--b1);
  font-size: var(--fs);
}

.op-row {
  display: grid;
  grid-template-columns: 32px 1fr 48px 52px 52px 44px 48px 52px 52px 44px 28px;
  gap: 4px;
  padding: 4px 6px 4px calc(6px + 20px);
  border-bottom: 1px solid var(--b1);
  color: var(--t3);
  background: var(--raised);
}
.op-row:last-child { border-bottom: none; }
.op-row:hover { background: var(--b1); }

/* Shared */
.op-val, .op-pct { text-align: left; }
.op-action { text-align: right; }
.btn-icon {
  background: transparent;
  border: none;
  padding: 2px;
  cursor: pointer;
  color: var(--t3);
  border-radius: var(--rs);
  opacity: 0;
  transition: opacity 0.15s;
}
.op-row:hover .btn-icon,
.job-row:hover .btn-icon { opacity: 1; }
.btn-icon:hover { color: var(--red); background: var(--red-10); }
</style>
