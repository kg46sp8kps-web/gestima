<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as wcApi from '@/api/work-centers'
import type { WorkCenter } from '@/types/work-center'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

const centers = ref<WorkCenter[]>([])
const loading = ref(false)
const error = ref(false)
const showInactive = ref(false)

const WC_TYPE_LABELS: Record<string, string> = {
  lathe:       'Soustruh',
  mill:        'Fréza',
  grinder:     'Bruska',
  drill:       'Vrtačka',
  saw:         'Pila',
  other:       'Ostatní',
}

const displayed = computed(() =>
  showInactive.value ? centers.value : centers.value.filter(c => c.is_active),
)

async function load() {
  loading.value = true
  error.value = false
  try {
    centers.value = await wcApi.getAll()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="srch-bar">
      <label class="toggle-label">
        <input
          v-model="showInactive"
          type="checkbox"
          data-testid="wc-show-inactive"
          class="toggle-cb"
        />
        Zobrazit neaktivní
      </label>
      <span class="srch-count">{{ displayed.length }} / {{ centers.length }}</span>
    </div>

    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!displayed.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádná pracoviště</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:82px">Číslo</th>
            <th>Název</th>
            <th style="width:70px">Typ</th>
            <th class="r" style="width:72px">Sazba/hod</th>
            <th class="r" style="width:50px">Max ∅</th>
            <th class="r" style="width:38px">Osy</th>
            <th style="width:50px">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in displayed"
            :key="c.id"
            :class="{ inactive: !c.is_active }"
            :data-testid="`wc-row-${c.id}`"
          >
            <td class="mono t3">{{ c.work_center_number }}</td>
            <td>{{ c.name }}</td>
            <td class="t4">{{ WC_TYPE_LABELS[c.work_center_type] ?? c.work_center_type }}</td>
            <td class="r mono">
              {{ c.hourly_rate_total != null ? formatNumber(c.hourly_rate_total, 0) : '—' }}
            </td>
            <td class="r mono t4">
              {{ c.max_workpiece_diameter != null ? formatNumber(c.max_workpiece_diameter, 0) : '—' }}
            </td>
            <td class="r mono t4">{{ c.axes ?? '—' }}</td>
            <td>
              <span v-if="c.is_active" class="badge">
                <span class="badge-dot ok" />Aktiv.
              </span>
              <span v-else class="badge">
                <span class="badge-dot neutral" />Neakt.
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.srch-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.toggle-label {
  display: flex; align-items: center; gap: 5px;
  font-size: var(--fsl); color: var(--t3); cursor: pointer; user-select: none;
}
.toggle-cb { accent-color: var(--t1); cursor: pointer; }
.srch-count { font-size: 10px; color: var(--t4); white-space: nowrap; font-family: var(--mono); margin-left: auto; }
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
.ot tbody tr.inactive td { opacity: 0.45; }
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }
.badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px;
  font-size: 10px; font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2);
}
.badge-dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }
</style>
