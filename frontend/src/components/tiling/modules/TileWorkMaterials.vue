<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import * as materialInputsApi from '@/api/material-inputs'
import type { MaterialInput, StockShape } from '@/types/material-input'
import type { ContextGroup } from '@/types/workspace'

// Module-level cache: partId → items. Survives component unmount/remount (panel moves).
const _cache = new Map<number, MaterialInput[]>()
// Tracks which leafId has already fetched data for which partId — skips refetch on remount.
const _fetchedFor = new Map<string, number>()
import { formatCurrency, formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const items = ref<MaterialInput[]>([])
const loading = ref(false)
const error = ref(false)

const totalWeight = computed(() => items.value.reduce((s, m) => s + (m.weight_kg ?? 0), 0))
const totalCost = computed(() => items.value.reduce((s, m) => s + (m.cost_per_piece ?? 0), 0))
const isRefetching = computed(() => loading.value && items.value.length > 0)

const SHAPE_LABELS: Record<StockShape, string> = {
  round_bar:     'Tyč kulatá',
  square_bar:    'Tyč čtvercová',
  flat_bar:      'Tyč plochá',
  hexagonal_bar: 'Tyč šestihranná',
  plate:         'Plech',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

function dimLabel(m: MaterialInput): string {
  const d = (v: number | null) => v != null ? String(v) : '?'
  switch (m.stock_shape) {
    case 'round_bar':
    case 'hexagonal_bar':
      return `\u00D8${d(m.stock_diameter)} \u00D7 ${d(m.stock_length)} mm`
    case 'square_bar':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_length)} mm`
    case 'flat_bar':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_height)} \u00D7 ${d(m.stock_length)} mm`
    case 'plate':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_height)} mm`
    case 'tube':
      return `\u00D8${d(m.stock_diameter)} \u00D7 ${d(m.stock_length)}, t=${d(m.stock_wall_thickness)} mm`
    default:
      return m.stock_length != null ? `${d(m.stock_length)} mm` : '—'
  }
}

watch(
  part,
  async (p) => {
    if (!p) { items.value = []; return }
    if (_cache.has(p.id)) items.value = _cache.get(p.id)!
    // Skip refetch if this leaf already fetched this part (remount with same part)
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    try {
      items.value = await materialInputsApi.getByPartId(p.id)
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
  <div :class="['wmat', { refetching: isRefetching }]">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
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
      <span class="mod-label">Díl nemá žádné materiály</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Summary ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div class="rib-i">
            <span class="rib-l">Materiálů</span>
            <span class="rib-v m">{{ items.length }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Hmotnost / ks</span>
            <span class="rib-v m">{{ formatNumber(totalWeight, 3) }} kg</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Náklady / ks</span>
            <span class="rib-v m green">{{ formatCurrency(totalCost) }}</span>
          </div>
        </div>
      </div>

      <!-- Table -->
      <div class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:24px">#</th>
              <th>Materiál</th>
              <th>Tvar / rozměry</th>
              <th class="r" style="width:80px">Hmotnost</th>
              <th class="r" style="width:100px">Cena / ks</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="m in items"
              :key="m.id"
              :data-testid="`mat-row-${m.id}`"
            >
              <td class="mono t4">{{ m.seq + 1 }}</td>
              <td>
                <div class="mat-name">{{ m.price_category?.name ?? '—' }}</div>
                <div class="mat-sub t4">{{ m.price_category?.code ?? '' }}</div>
              </td>
              <td>
                <div>{{ SHAPE_LABELS[m.stock_shape] }}</div>
                <div class="mat-sub t4 mono">{{ dimLabel(m) }}</div>
              </td>
              <td class="r mono">
                {{ m.weight_kg != null ? formatNumber(m.weight_kg, 3) + ' kg' : '—' }}
              </td>
              <td class="r">
                <span class="price-badge">{{ formatCurrency(m.cost_per_piece) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wmat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wmat.refetching { opacity: 0.4; }

/* ─── Placeholder ─── */
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

/* ─── Ribbon ─── */
.rib {
  padding: 6px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.rib-r { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: 10px; color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { font-family: var(--mono); }
.rib-v.green { color: var(--green); }

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Table ─── */
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
  padding: 4px var(--pad);
  font-size: var(--fs);
  color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025);
}
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }

.mat-name { font-weight: 500; color: var(--t1); }
.mat-sub { font-size: 10px; margin-top: 1px; }

/* ─── Price badge ─── */
.price-badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 99px;
  background: var(--b1);
  color: var(--green);
  white-space: nowrap;
}
</style>
