<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import * as productionRecordsApi from '@/api/production-records'
import type { ProductionRecord } from '@/types/production-record'
import type { ContextGroup } from '@/types/workspace'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

// Module-level cache: partId → records
const _cache = new Map<number, ProductionRecord[]>()
const _fetchedFor = new Map<string, number>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const items = ref<ProductionRecord[]>([])
const loading = ref(false)
const error = ref(false)
const isRefetching = computed(() => loading.value && items.value.length > 0)

function deltaClass(rec: ProductionRecord): string {
  if (rec.actual_time_min == null || rec.planned_time_min == null) return ''
  const diff = rec.actual_time_min - rec.planned_time_min
  const pct = rec.planned_time_min > 0 ? diff / rec.planned_time_min : 0
  if (pct > 0.15) return 'delta-err'
  if (pct > 0.05) return 'delta-warn'
  return 'delta-ok'
}

function deltaLabel(rec: ProductionRecord): string {
  if (rec.actual_time_min == null || rec.planned_time_min == null) return '—'
  const diff = rec.actual_time_min - rec.planned_time_min
  return (diff >= 0 ? '+' : '') + formatNumber(diff, 2)
}

watch(
  part,
  async (p) => {
    if (!p) { items.value = []; return }
    if (_cache.has(p.id)) items.value = _cache.get(p.id)!
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    try {
      items.value = await productionRecordsApi.getByPartId(p.id)
      _cache.set(p.id, items.value)
    } catch {
      error.value = true
      _fetchedFor.delete(props.leafId)
      if (!items.value.length) items.value = []
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div :class="['wprod', { refetching: isRefetching }]">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
      <span class="mod-hint">Záznamy výroby pro vybraný díl</span>
    </div>

    <!-- Loading -->
    <div v-else-if="loading && !items.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!items.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádné záznamy výroby</span>
    </div>

    <!-- Data -->
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:80px">Datum</th>
            <th style="width:90px">Infor č.</th>
            <th class="r" style="width:42px">Qty</th>
            <th class="r" style="width:36px">Op</th>
            <th>Pracoviště</th>
            <th class="r" style="width:72px">Plán min</th>
            <th class="r" style="width:72px">Skut. min</th>
            <th class="r" style="width:56px">Δ</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in items"
            :key="r.id"
            :data-testid="`prod-row-${r.id}`"
          >
            <td class="t4 mono">{{ r.production_date ?? '—' }}</td>
            <td class="mono t4">{{ r.infor_order_number ?? '—' }}</td>
            <td class="r mono">{{ r.batch_quantity ?? '—' }}</td>
            <td class="r t4 mono">{{ r.operation_seq != null ? r.operation_seq * 10 : '—' }}</td>
            <td class="t3">{{ r.work_center_name ?? '—' }}</td>
            <td class="r mono">{{ r.planned_time_min != null ? formatNumber(r.planned_time_min, 2) : '—' }}</td>
            <td class="r mono">{{ r.actual_time_min != null ? formatNumber(r.actual_time_min, 2) : '—' }}</td>
            <td :class="['r', 'mono', deltaClass(r)]">{{ deltaLabel(r) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.wprod {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wprod.refetching { opacity: 0.4; }

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.mod-hint { font-size: 10px; opacity: 0.6; }

.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 0;
}
.ot {
  width: 100%;
  border-collapse: collapse;
}
.ot thead {
  background: rgba(255,255,255,0.025);
  position: sticky;
  top: 0;
  z-index: 2;
}
.ot th {
  padding: 4px var(--pad);
  font-size: 10px;
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}
.ot th.r { text-align: right; }
.ot td {
  padding: 3px var(--pad);
  font-size: var(--fs);
  color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025);
}
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }

.delta-ok  { color: var(--ok); }
.delta-warn { color: var(--warn); }
.delta-err  { color: var(--err); }
</style>
