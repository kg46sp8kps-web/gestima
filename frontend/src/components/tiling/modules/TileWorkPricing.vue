<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import * as batchesApi from '@/api/batches'
import type { Batch } from '@/types/batch'
import type { ContextGroup } from '@/types/workspace'

// Module-level cache: partId → batches. Survives component unmount/remount.
const _cache = new Map<number, Batch[]>()
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

const batches = ref<Batch[]>([])
const loading = ref(false)
const error = ref(false)

const defaultBatch = computed(
  () => batches.value.find(b => b.is_default) ?? batches.value[0] ?? null,
)
const isRefetching = computed(() => loading.value && batches.value.length > 0)

function pct(value: number): string {
  return formatNumber(value, 1) + ' %'
}

watch(
  part,
  async (p) => {
    if (!p) { batches.value = []; return }
    if (_cache.has(p.id)) batches.value = _cache.get(p.id)!
    // Skip refetch if this leaf already fetched this part (remount with same part)
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    try {
      batches.value = await batchesApi.getByPartId(p.id)
      _cache.set(p.id, batches.value)
    } catch {
      error.value = true
      _fetchedFor.delete(props.leafId)
      if (!batches.value.length) batches.value = []
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div :class="['wprc', { refetching: isRefetching }]">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <!-- Loading -->
    <div v-else-if="loading && !batches.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!batches.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné dávky</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Summary ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div class="rib-i">
            <span class="rib-l">Dávek</span>
            <span class="rib-v m">{{ batches.length }}</span>
          </div>
          <template v-if="defaultBatch">
            <div class="rib-i">
              <span class="rib-l">Výchozí qty</span>
              <span class="rib-v m">{{ formatNumber(defaultBatch.quantity, 0) }} ks</span>
            </div>
            <div class="rib-i">
              <span class="rib-l">Náklady / ks</span>
              <span class="rib-v m">{{ formatCurrency(defaultBatch.unit_cost) }}</span>
            </div>
            <div class="rib-i">
              <span class="rib-l">Cena / ks</span>
              <span class="rib-v m green">{{ formatCurrency(defaultBatch.unit_price) }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- Batches table -->
      <div class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:16px"></th>
              <th class="r" style="width:54px">Qty (ks)</th>
              <th class="r" style="width:80px">Mat. %</th>
              <th class="r" style="width:80px">Stroj. %</th>
              <th class="r" style="width:80px">Sér. %</th>
              <th class="r" style="width:100px">Náklady / ks</th>
              <th class="r" style="width:100px">Cena / ks</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="b in batches"
              :key="b.id"
              :class="{ 'row-default': b.is_default }"
              :data-testid="`batch-row-${b.id}`"
            >
              <td>
                <span v-if="b.is_default" class="def-dot" title="Výchozí dávka" />
                <span v-if="b.is_frozen" class="frozen-badge" title="Zmrazená cena">ZAM</span>
              </td>
              <td class="r">{{ formatNumber(b.quantity, 0) }}</td>
              <td class="r">
                <span class="pct-badge mat">{{ pct(b.material_percent) }}</span>
              </td>
              <td class="r">
                <span class="pct-badge mach">{{ pct(b.machining_percent) }}</span>
              </td>
              <td class="r">
                <span class="pct-badge setup">{{ pct(b.setup_percent) }}</span>
              </td>
              <td class="r">{{ formatCurrency(b.unit_cost) }}</td>
              <td class="r">
                <span class="price-val">{{ formatCurrency(b.unit_price) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wprc {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wprc.refetching { opacity: 0.4; }

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
.rib-l { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { }
.rib-v.green { color: var(--green); }

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 0;
}

/* ─── Table ─── */
.row-default td { background: rgba(255,255,255,0.015); }


/* ─── Indicators ─── */
.def-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--green);
  vertical-align: middle;
}
.frozen-badge {
  display: inline-block;
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 0 3px;
  border-radius: var(--rs);
  background: var(--b2);
  color: var(--t3);
}

/* ─── Percent badges ─── */
.pct-badge {
  display: inline-block;
  font-size: var(--fsm);
  padding: 1px 4px;
  border-radius: var(--rs);
  background: var(--b1);
}
.pct-badge.mat  { color: var(--chart-material); }
.pct-badge.mach { color: var(--chart-machining); }
.pct-badge.setup { color: var(--chart-setup); }

/* ─── Price value ─── */
.price-val {
  font-weight: 600;
  color: var(--green);
}
</style>
