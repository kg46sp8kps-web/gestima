<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import * as ccApi from '@/api/cutting-conditions'
import type { CuttingConditionPivotResponse } from '@/types/cutting-condition'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

type Mode = 'low' | 'mid' | 'high'

const mode = ref<Mode>('mid')
const pivot = ref<CuttingConditionPivotResponse | null>(null)
const loading = ref(false)
const error = ref(false)
const search = ref('')

interface FlatRow {
  material: string
  operation: string
  operationType: string
  Vc: number | null
  f: number | null
  Ap: number | null
}

const flatRows = computed<FlatRow[]>(() => {
  if (!pivot.value) return []
  const { materials, material_names, operations, cells } = pivot.value
  const rows: FlatRow[] = []
  for (const matCode of materials) {
    const matCells = cells[matCode] ?? {}
    for (const op of operations) {
      const key = `${op.operation_type}/${op.operation}`
      const cell = matCells[key]
      if (!cell) continue
      rows.push({
        material: material_names[matCode] ?? matCode,
        operation: op.label,
        operationType: op.operation_type,
        Vc: cell.Vc,
        f: cell.f,
        Ap: cell.Ap,
      })
    }
  }
  return rows
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return flatRows.value
  return flatRows.value.filter(r =>
    r.material.toLowerCase().includes(q) ||
    r.operation.toLowerCase().includes(q) ||
    r.operationType.toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    pivot.value = await ccApi.getPivot(mode.value)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(mode, load)
onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="toolbar">
      <div class="mode-tabs">
        <button
          v-for="m in (['low', 'mid', 'high'] as Mode[])"
          :key="m"
          :class="['mtab', mode === m ? 'on' : '']"
          :data-testid="`cc-mode-${m}`"
          @click="mode = m"
        >
          {{ m === 'low' ? 'Nízká' : m === 'mid' ? 'Střední' : 'Vysoká' }}
        </button>
      </div>
      <input
        v-model="search"
        class="srch-inp"
        type="text"
        placeholder="Hledat materiál, operaci…"
        data-testid="cc-search-input"
      />
      <span class="srch-count">{{ filtered.length }}</span>
    </div>

    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!filtered.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádná data' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th>Materiál</th>
            <th>Operace</th>
            <th class="r" style="width:72px">Vc (m/min)</th>
            <th class="r" style="width:72px">f (mm/ot)</th>
            <th class="r" style="width:72px">Ap (mm)</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in filtered"
            :key="i"
            :data-testid="`cc-row-${i}`"
          >
            <td>{{ row.material }}</td>
            <td class="t4">{{ row.operation }}</td>
            <td class="r mono">{{ row.Vc != null ? formatNumber(row.Vc, 0) : '—' }}</td>
            <td class="r mono t4">{{ row.f != null ? formatNumber(row.f, 4) : '—' }}</td>
            <td class="r mono t4">{{ row.Ap != null ? formatNumber(row.Ap, 2) : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.toolbar {
  display: flex; align-items: center; gap: 8px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.mode-tabs { display: flex; gap: 2px; }
.mtab {
  padding: 2px 7px; font-size: var(--fsl); font-weight: 500; color: var(--t4);
  background: transparent; border: none; border-radius: var(--rs); cursor: pointer; font-family: var(--font);
}
.mtab:hover { color: var(--t3); }
.mtab.on { color: var(--t1); background: var(--b1); }
.srch-inp {
  flex: 1; background: var(--b1); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t1); font-size: var(--fs);
  padding: 3px 6px; outline: none;
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); }
.srch-count { font-size: 10px; color: var(--t4); white-space: nowrap; font-family: var(--mono); }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ot { width: 100%; border-collapse: collapse; }
.ot thead { background: rgba(255,255,255,0.025); position: sticky; top: 0; z-index: 2; }
.ot th {
  padding: 4px var(--pad); font-size: 10px; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.04em; text-align: left;
  border-bottom: 1px solid var(--b2); white-space: nowrap;
}
.ot th.r { text-align: right; }
.ot td {
  padding: 4px var(--pad); font-size: var(--fs); color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025); vertical-align: middle;
}
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }
.r { text-align: right; }
</style>
