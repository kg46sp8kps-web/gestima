<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import * as wcApi from '@/api/work-centers'
import type { WorkCenter } from '@/types/work-center'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface WcDraft {
  work_center_number: string
  name: string
  work_center_type: string
  hourly_rate_amortization: number | null
  hourly_rate_labor: number | null
  hourly_rate_tools: number | null
  hourly_rate_overhead: number | null
  max_workpiece_diameter: number | null
  axes: number | null
  is_active: boolean
  version: number
}

const centers = ref<WorkCenter[]>([])
const loading = ref(false)
const error = ref(false)
const showInactive = ref(false)
const editingId = ref<number | null>(null)
const editDraft = ref<WcDraft | null>(null)

const ui = useUiStore()

const WC_TYPE_LABELS: Record<string, string> = {
  lathe:   'Soustruh',
  mill:    'Fréza',
  grinder: 'Bruska',
  drill:   'Vrtačka',
  saw:     'Pila',
  other:   'Ostatní',
}

const WC_TYPE_OPTIONS = [
  { value: 'lathe',   label: 'Soustruh' },
  { value: 'mill',    label: 'Fréza' },
  { value: 'grinder', label: 'Bruska' },
  { value: 'drill',   label: 'Vrtačka' },
  { value: 'saw',     label: 'Pila' },
  { value: 'other',   label: 'Ostatní' },
]

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

function startEdit(c: WorkCenter) {
  editingId.value = c.id
  editDraft.value = {
    work_center_number: c.work_center_number,
    name: c.name,
    work_center_type: c.work_center_type,
    hourly_rate_amortization: c.hourly_rate_amortization,
    hourly_rate_labor: c.hourly_rate_labor,
    hourly_rate_tools: c.hourly_rate_tools,
    hourly_rate_overhead: c.hourly_rate_overhead,
    max_workpiece_diameter: c.max_workpiece_diameter,
    axes: c.axes,
    is_active: c.is_active,
    version: c.version,
  }
}

async function saveEdit() {
  const id = editingId.value
  const draft = editDraft.value
  if (!id || !draft) return
  const wcNumber = draft.work_center_number
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await wcApi.update(wcNumber, draft)
    const idx = centers.value.findIndex(c => c.id === id)
    if (idx !== -1) centers.value[idx] = updated
    ui.showSuccess('Pracoviště uloženo')
  } catch {
    ui.showError('Chyba při ukládání pracoviště')
  }
}

function cancelEdit() {
  editingId.value = null
  editDraft.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
  if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
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
            <th style="width:62px"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in displayed"
            :key="c.id"
            :class="['row-clickable', { 'row-editing': editingId === c.id, inactive: !c.is_active && editingId !== c.id }]"
            :data-testid="`wc-row-${c.id}`"
            @click="editingId !== c.id ? startEdit(c) : undefined"
            @keydown.capture="editingId === c.id ? onKeydown($event) : undefined"
          >
            <!-- VIEW MODE -->
            <template v-if="editingId !== c.id">
              <td class="t3">{{ c.work_center_number }}</td>
              <td>{{ c.name }}</td>
              <td class="t4">{{ WC_TYPE_LABELS[c.work_center_type] ?? c.work_center_type }}</td>
              <td class="r">
                {{ c.hourly_rate_total != null ? formatNumber(c.hourly_rate_total, 0) : '—' }}
              </td>
              <td class="r t4">
                {{ c.max_workpiece_diameter != null ? formatNumber(c.max_workpiece_diameter, 0) : '—' }}
              </td>
              <td class="r t4">{{ c.axes ?? '—' }}</td>
              <td>
                <span v-if="c.is_active" class="badge">
                  <span class="badge-dot ok" />Aktiv.
                </span>
                <span v-else class="badge">
                  <span class="badge-dot neutral" />Neakt.
                </span>
              </td>
              <td class="action-cell t4">upravit</td>
            </template>

            <!-- EDIT MODE -->
            <template v-else-if="editDraft">
              <td class="t3">{{ editDraft.work_center_number }}</td>
              <td>
                <input
                  v-model="editDraft.name"
                  type="text"
                  class="ei ei-wide"
                  :data-testid="`wc-edit-name-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
              </td>
              <td>
                <select
                  v-model="editDraft.work_center_type"
                  class="ei-sel"
                  :data-testid="`wc-edit-type-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                >
                  <option
                    v-for="opt in WC_TYPE_OPTIONS"
                    :key="opt.value"
                    :value="opt.value"
                  >{{ opt.label }}</option>
                </select>
              </td>
              <td class="rates-cell">
                <input
                  class="ei ei-sm"
                  type="number"
                  v-model.number="editDraft.hourly_rate_amortization"
                  placeholder="Amor"
                  :data-testid="`wc-rate-amor-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
                <input
                  class="ei ei-sm"
                  type="number"
                  v-model.number="editDraft.hourly_rate_labor"
                  placeholder="Práce"
                  :data-testid="`wc-rate-labor-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
                <input
                  class="ei ei-sm"
                  type="number"
                  v-model.number="editDraft.hourly_rate_tools"
                  placeholder="Nář."
                  :data-testid="`wc-rate-tools-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
                <input
                  class="ei ei-sm"
                  type="number"
                  v-model.number="editDraft.hourly_rate_overhead"
                  placeholder="Rež."
                  :data-testid="`wc-rate-overhead-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
              </td>
              <td>
                <input
                  v-model.number="editDraft.max_workpiece_diameter"
                  type="number"
                  class="ei ei-num"
                  :data-testid="`wc-edit-diameter-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
              </td>
              <td>
                <input
                  v-model.number="editDraft.axes"
                  type="number"
                  step="1"
                  class="ei ei-num"
                  :data-testid="`wc-edit-axes-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                />
              </td>
              <td>
                <select
                  v-model="editDraft.is_active"
                  class="ei-sel"
                  :data-testid="`wc-edit-status-${c.id}`"
                  @keydown="onKeydown"
                  @click.stop
                >
                  <option :value="true">Aktivní</option>
                  <option :value="false">Neaktivní</option>
                </select>
              </td>
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="wc-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="wc-cancel-btn"
                  title="Zrušit (Esc)"
                  @click.stop="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </template>
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
.srch-count { font-size: var(--fsm); color: var(--t4); white-space: nowrap; margin-left: auto; }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ot tbody tr.inactive td { opacity: 0.45; }

.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }
.badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px;
  font-size: var(--fsm); font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2);
}
.badge-dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }

/* Inline editing */
.row-editing td { background: var(--raised); border-bottom-color: var(--b3); }
.row-editing:hover td { background: var(--raised); }
.row-clickable { cursor: pointer; }
.action-cell { font-size: var(--fsm); color: var(--t4); white-space: nowrap; }
.ei {
  background: var(--surface); border: 1px solid var(--b3); border-radius: var(--rs);
  color: var(--t1); font-size: var(--fs); padding: 2px 4px; outline: none;
}
.ei:focus { border-color: rgba(255,255,255,0.3); }
.ei-num { font-family: var(--mono); width: 56px; text-align: right; }
.ei-sm { font-family: var(--mono); width: 48px; }
.ei-wide { width: 100%; }
.ei-sel {
  background: var(--surface); border: 1px solid var(--b3); border-radius: var(--rs);
  color: var(--t1); font-size: var(--fs); padding: 2px 4px; outline: none; cursor: pointer;
}
.ei-sel:focus { border-color: rgba(255,255,255,0.3); }
.rates-cell { display: flex; gap: 2px; flex-wrap: wrap; }
</style>
