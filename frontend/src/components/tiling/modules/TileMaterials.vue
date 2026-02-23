<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as materialsApi from '@/api/materials'
import type { MaterialItem } from '@/types/material-item'
import type { ContextGroup } from '@/types/workspace'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<MaterialItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref(false)
const searchQuery = ref('')

const SHAPE_LABELS: Record<string, string> = {
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Plech',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

function dimLabel(m: MaterialItem): string {
  const d = (v: number | null) => v != null ? String(v) : '?'
  switch (m.shape) {
    case 'round_bar':
    case 'hexagonal_bar':
      return m.diameter != null ? `${d(m.diameter)} mm` : '—'
    case 'square_bar':
      return m.width != null ? `${d(m.width)} mm` : '—'
    case 'flat_bar':
      return (m.width != null && m.thickness != null) ? `${d(m.width)}×${d(m.thickness)} mm` : '—'
    case 'plate':
      return (m.width != null && m.thickness != null) ? `${d(m.width)}×${d(m.thickness)} mm` : '—'
    case 'tube':
      return (m.diameter != null && m.wall_thickness != null)
        ? `∅${d(m.diameter)} t${d(m.wall_thickness)} mm`
        : '—'
    default:
      return '—'
  }
}

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(m =>
    m.code.toLowerCase().includes(q) ||
    m.name.toLowerCase().includes(q) ||
    (m.material_number ?? '').includes(q) ||
    (m.norms ?? '').toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    const res = await materialsApi.getItems({ limit: 500 })
    items.value = res.items
    total.value = res.total
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wmat">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Search toolbar -->
      <div class="srch-bar">
        <input
          v-model="searchQuery"
          class="srch-inp"
          type="text"
          placeholder="Hledat kód, název, normu…"
          data-testid="materials-search-input"
        />
        <span class="srch-count">{{ filtered.length }} / {{ total }}</span>
      </div>

      <!-- Empty -->
      <div v-if="!filtered.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">{{ searchQuery ? 'Žádné výsledky' : 'Žádné položky' }}</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:82px">Číslo</th>
              <th style="width:90px">Kód</th>
              <th>Název</th>
              <th style="width:70px">Tvar</th>
              <th style="width:80px">Rozměr</th>
              <th class="r" style="width:64px">kg/m</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="m in filtered"
              :key="m.id"
              :data-testid="`material-row-${m.id}`"
            >
              <td class="t4">{{ m.material_number }}</td>
              <td class="">{{ m.code }}</td>
              <td>
                <div class="mat-name">{{ m.name }}</div>
                <div v-if="m.norms" class="mat-sub t4">{{ m.norms }}</div>
              </td>
              <td class="t4">{{ SHAPE_LABELS[m.shape] ?? m.shape }}</td>
              <td class="t3">{{ dimLabel(m) }}</td>
              <td class="r t4">
                {{ m.weight_per_meter != null ? formatNumber(m.weight_per_meter, 3) : '—' }}
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
}

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

/* Search bar */
.srch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.srch-inp {
  flex: 1;
  height: 28px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  padding: 3px 6px;
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.srch-count {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}

/* Table wrapper */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* Table */

.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }

.mat-name { font-weight: 500; color: var(--t1); }
.mat-sub { font-size: var(--fsm); margin-top: 1px; }
</style>
