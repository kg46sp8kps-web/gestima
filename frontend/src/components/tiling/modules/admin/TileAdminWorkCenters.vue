<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { PlusIcon } from 'lucide-vue-next'
import * as wcApi from '@/api/work-centers'
import type { WorkCenter, WorkCenterCreate, WorkCenterUpdate } from '@/types/work-center'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import Modal from '@/components/ui/Modal.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface ModalDraft {
  work_center_number: string
  name: string
  work_center_type: string
  subtype: string | null
  hourly_rate_amortization: number | null
  hourly_rate_labor: number | null
  hourly_rate_tools: number | null
  hourly_rate_overhead: number | null
  max_workpiece_diameter: number | null
  max_workpiece_length: number | null
  min_workpiece_diameter: number | null
  axes: number | null
  has_bar_feeder: boolean
  has_sub_spindle: boolean
  has_milling: boolean
  suitable_for_series: boolean
  suitable_for_single: boolean
  setup_base_min: number
  setup_per_tool_min: number
  is_active: boolean
  priority: number
  notes: string | null
  version: number
}

const centers = ref<WorkCenter[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref(false)
const showInactive = ref(false)

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('edit')
const modalDraft = ref<ModalDraft>(makeDefaultDraft())

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

const computedSetupRate = computed(() => {
  const d = modalDraft.value
  const a = d.hourly_rate_amortization, l = d.hourly_rate_labor, o = d.hourly_rate_overhead
  if (a == null && l == null && o == null) return null
  return (a ?? 0) + (l ?? 0) + (o ?? 0)
})

const computedOperationRate = computed(() => {
  const d = modalDraft.value
  const a = d.hourly_rate_amortization, l = d.hourly_rate_labor
  const t = d.hourly_rate_tools, o = d.hourly_rate_overhead
  if (a == null && l == null && t == null && o == null) return null
  return (a ?? 0) + (l ?? 0) + (t ?? 0) + (o ?? 0)
})

function numVal(v: number | null): string {
  return v != null ? String(v) : ''
}

function toStr(v: string | number | null): string {
  return v == null ? '' : String(v)
}

function toStrOpt(v: string | number | null): string | null {
  const s = v == null ? '' : String(v)
  return s || null
}

function parseOpt(v: string | number | null): number | null {
  if (v == null || v === '') return null
  const n = typeof v === 'number' ? v : parseFloat(String(v))
  return isNaN(n) ? null : n
}

function parseReq(v: string | number | null, fallback: number): number {
  if (v == null || v === '') return fallback
  const n = typeof v === 'number' ? v : parseFloat(String(v))
  return isNaN(n) ? fallback : n
}

function makeDefaultDraft(): ModalDraft {
  return {
    work_center_number: '',
    name: '',
    work_center_type: 'lathe',
    subtype: null,
    hourly_rate_amortization: null,
    hourly_rate_labor: null,
    hourly_rate_tools: null,
    hourly_rate_overhead: null,
    max_workpiece_diameter: null,
    max_workpiece_length: null,
    min_workpiece_diameter: null,
    axes: null,
    has_bar_feeder: false,
    has_sub_spindle: false,
    has_milling: false,
    suitable_for_series: true,
    suitable_for_single: true,
    setup_base_min: 30,
    setup_per_tool_min: 3,
    is_active: true,
    priority: 99,
    notes: null,
    version: 0,
  }
}

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

function openEdit(wc: WorkCenter) {
  modalMode.value = 'edit'
  modalDraft.value = {
    work_center_number: wc.work_center_number,
    name: wc.name,
    work_center_type: wc.work_center_type,
    subtype: wc.subtype,
    hourly_rate_amortization: wc.hourly_rate_amortization,
    hourly_rate_labor: wc.hourly_rate_labor,
    hourly_rate_tools: wc.hourly_rate_tools,
    hourly_rate_overhead: wc.hourly_rate_overhead,
    max_workpiece_diameter: wc.max_workpiece_diameter,
    max_workpiece_length: wc.max_workpiece_length,
    min_workpiece_diameter: wc.min_workpiece_diameter,
    axes: wc.axes,
    has_bar_feeder: wc.has_bar_feeder,
    has_sub_spindle: wc.has_sub_spindle,
    has_milling: wc.has_milling,
    suitable_for_series: wc.suitable_for_series,
    suitable_for_single: wc.suitable_for_single,
    setup_base_min: wc.setup_base_min,
    setup_per_tool_min: wc.setup_per_tool_min,
    is_active: wc.is_active,
    priority: wc.priority,
    notes: wc.notes,
    version: wc.version,
  }
  modalOpen.value = true
}

function openCreate() {
  modalMode.value = 'create'
  modalDraft.value = makeDefaultDraft()
  modalOpen.value = true
}

async function onSave() {
  const d = modalDraft.value
  saving.value = true
  try {
    if (modalMode.value === 'create') {
      const payload: WorkCenterCreate = {
        name: d.name,
        work_center_type: d.work_center_type,
        subtype: d.subtype,
        hourly_rate_amortization: d.hourly_rate_amortization,
        hourly_rate_labor: d.hourly_rate_labor,
        hourly_rate_tools: d.hourly_rate_tools,
        hourly_rate_overhead: d.hourly_rate_overhead,
        max_workpiece_diameter: d.max_workpiece_diameter,
        max_workpiece_length: d.max_workpiece_length,
        min_workpiece_diameter: d.min_workpiece_diameter,
        axes: d.axes,
        has_bar_feeder: d.has_bar_feeder,
        has_sub_spindle: d.has_sub_spindle,
        has_milling: d.has_milling,
        suitable_for_series: d.suitable_for_series,
        suitable_for_single: d.suitable_for_single,
        setup_base_min: d.setup_base_min,
        setup_per_tool_min: d.setup_per_tool_min,
        is_active: d.is_active,
        priority: d.priority,
        notes: d.notes,
      }
      await wcApi.create(payload)
      ui.showSuccess('Pracoviště vytvořeno')
    } else {
      const payload: WorkCenterUpdate = {
        name: d.name,
        work_center_type: d.work_center_type,
        subtype: d.subtype,
        hourly_rate_amortization: d.hourly_rate_amortization,
        hourly_rate_labor: d.hourly_rate_labor,
        hourly_rate_tools: d.hourly_rate_tools,
        hourly_rate_overhead: d.hourly_rate_overhead,
        max_workpiece_diameter: d.max_workpiece_diameter,
        max_workpiece_length: d.max_workpiece_length,
        min_workpiece_diameter: d.min_workpiece_diameter,
        axes: d.axes,
        has_bar_feeder: d.has_bar_feeder,
        has_sub_spindle: d.has_sub_spindle,
        has_milling: d.has_milling,
        suitable_for_series: d.suitable_for_series,
        suitable_for_single: d.suitable_for_single,
        setup_base_min: d.setup_base_min,
        setup_per_tool_min: d.setup_per_tool_min,
        is_active: d.is_active,
        priority: d.priority,
        notes: d.notes,
        version: d.version,
      }
      await wcApi.update(d.work_center_number, payload)
      ui.showSuccess('Pracoviště uloženo')
    }
    modalOpen.value = false
    await load()
  } catch {
    ui.showError(
      modalMode.value === 'create'
        ? 'Chyba při vytváření pracoviště'
        : 'Chyba při ukládání pracoviště',
    )
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="tab-content">
    <!-- Toolbar -->
    <div class="srch-bar">
      <label class="toggle-label">
        <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
        <input v-model="showInactive" type="checkbox" data-testid="wc-show-inactive" class="toggle-cb" />
        Zobrazit neaktivní
      </label>
      <span class="srch-count">{{ displayed.length }} / {{ centers.length }}</span>
      <button
        class="icon-btn icon-btn-brand"
        data-testid="wc-create-btn"
        title="Nové pracoviště"
        @click="openCreate"
      >
        <PlusIcon :size="ICON_SIZE_SM" />
      </button>
    </div>

    <!-- States -->
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

    <!-- Table -->
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:82px">Číslo</th>
            <th>Název</th>
            <th style="width:68px">Typ</th>
            <th style="width:64px">Subtyp</th>
            <th class="r" style="width:68px">Seř. Kč/h</th>
            <th class="r" style="width:68px">Výr. Kč/h</th>
            <th class="r" style="width:50px">Max ∅</th>
            <th class="r" style="width:38px">Osy</th>
            <th class="r" style="width:44px">Prior.</th>
            <th style="width:90px">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in displayed"
            :key="c.id"
            :class="['row-clickable', { inactive: !c.is_active }]"
            :data-testid="`wc-row-${c.id}`"
            @click="openEdit(c)"
          >
            <td class="t3">{{ c.work_center_number }}</td>
            <td>{{ c.name }}</td>
            <td class="t4">{{ WC_TYPE_LABELS[c.work_center_type] ?? c.work_center_type }}</td>
            <td class="t4">{{ c.subtype ?? '—' }}</td>
            <td class="r">
              {{ c.hourly_rate_setup != null ? formatNumber(c.hourly_rate_setup, 0) : '—' }}
            </td>
            <td class="r">
              {{ c.hourly_rate_operation != null ? formatNumber(c.hourly_rate_operation, 0) : '—' }}
            </td>
            <td class="r t4">
              {{ c.max_workpiece_diameter != null ? formatNumber(c.max_workpiece_diameter, 0) : '—' }}
            </td>
            <td class="r t4">{{ c.axes ?? '—' }}</td>
            <td class="r t4">{{ c.priority }}</td>
            <td>
              <div class="status-cell">
                <span v-if="c.is_active" class="badge">
                  <span class="badge-dot-ok" />Aktiv.
                </span>
                <span v-else class="badge">
                  <span class="badge-dot-neutral" />Neakt.
                </span>
                <span v-if="c.needs_batch_recalculation" class="badge badge-recalc">
                  <span class="badge-dot-warn" />Přep.
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Edit / Create modal -->
    <Modal
      v-model="modalOpen"
      :title="modalMode === 'create' ? 'Nové pracoviště' : `Pracoviště ${modalDraft.work_center_number}`"
      size="lg"
    >
      <div class="modal-form">

        <!-- Sekce 1: Základní info -->
        <div class="form-section">
          <div class="section-title">Základní info</div>
          <div class="form-grid">
            <div class="span-2">
              <Input
                label="Název pracoviště"
                :modelValue="modalDraft.name"
                @update:modelValue="modalDraft.name = toStr($event)"
                data-testid="wc-modal-name"
              />
            </div>
            <Select
              label="Typ pracoviště"
              :modelValue="modalDraft.work_center_type"
              @update:modelValue="modalDraft.work_center_type = toStr($event)"
              :options="WC_TYPE_OPTIONS"
              data-testid="wc-modal-type"
            />
            <Input
              label="Subtyp"
              :modelValue="modalDraft.subtype ?? ''"
              @update:modelValue="modalDraft.subtype = toStrOpt($event)"
              placeholder="horizontal, vertical…"
              data-testid="wc-modal-subtype"
            />
          </div>
        </div>

        <!-- Sekce 2: Hodinové sazby -->
        <div class="form-section">
          <div class="section-title">Hodinové sazby (Kč/h)</div>
          <div class="form-grid-4">
            <Input
              label="Odpisy"
              type="number"
              :modelValue="numVal(modalDraft.hourly_rate_amortization)"
              @update:modelValue="modalDraft.hourly_rate_amortization = parseOpt($event)"
              data-testid="wc-modal-rate-amor"
            />
            <Input
              label="Práce"
              type="number"
              :modelValue="numVal(modalDraft.hourly_rate_labor)"
              @update:modelValue="modalDraft.hourly_rate_labor = parseOpt($event)"
              data-testid="wc-modal-rate-labor"
            />
            <Input
              label="Nástroje"
              type="number"
              :modelValue="numVal(modalDraft.hourly_rate_tools)"
              @update:modelValue="modalDraft.hourly_rate_tools = parseOpt($event)"
              data-testid="wc-modal-rate-tools"
            />
            <Input
              label="Režie"
              type="number"
              :modelValue="numVal(modalDraft.hourly_rate_overhead)"
              @update:modelValue="modalDraft.hourly_rate_overhead = parseOpt($event)"
              data-testid="wc-modal-rate-overhead"
            />
          </div>
          <div class="rates-computed">
            <span>Seřízení: <strong>{{ computedSetupRate != null ? formatNumber(computedSetupRate, 0) : '—' }} Kč/h</strong></span>
            <span>Výroba: <strong>{{ computedOperationRate != null ? formatNumber(computedOperationRate, 0) : '—' }} Kč/h</strong></span>
          </div>
        </div>

        <!-- Sekce 3: Technické parametry -->
        <div class="form-section">
          <div class="section-title">Technické parametry</div>
          <div class="form-grid-4">
            <Input
              label="Max ∅ mm"
              type="number"
              :modelValue="numVal(modalDraft.max_workpiece_diameter)"
              @update:modelValue="modalDraft.max_workpiece_diameter = parseOpt($event)"
              data-testid="wc-modal-diameter"
            />
            <Input
              label="Min ∅ mm"
              type="number"
              :modelValue="numVal(modalDraft.min_workpiece_diameter)"
              @update:modelValue="modalDraft.min_workpiece_diameter = parseOpt($event)"
              data-testid="wc-modal-min-diameter"
            />
            <Input
              label="Max délka mm"
              type="number"
              :modelValue="numVal(modalDraft.max_workpiece_length)"
              @update:modelValue="modalDraft.max_workpiece_length = parseOpt($event)"
              data-testid="wc-modal-length"
            />
            <Input
              label="Osy"
              type="number"
              :modelValue="numVal(modalDraft.axes)"
              @update:modelValue="modalDraft.axes = parseOpt($event)"
              data-testid="wc-modal-axes"
            />
          </div>
        </div>

        <!-- Sekce 4: Schopnosti -->
        <div class="form-section">
          <div class="section-title">Schopnosti</div>
          <div class="caps-row">
            <label class="cap-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.has_bar_feeder" type="checkbox" data-testid="wc-modal-bar-feeder" class="toggle-cb" />
              Podavač tyčí
            </label>
            <label class="cap-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.has_sub_spindle" type="checkbox" data-testid="wc-modal-sub-spindle" class="toggle-cb" />
              Protivřeteno
            </label>
            <label class="cap-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.has_milling" type="checkbox" data-testid="wc-modal-milling" class="toggle-cb" />
              Live tooling
            </label>
            <label class="cap-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.suitable_for_series" type="checkbox" data-testid="wc-modal-series" class="toggle-cb" />
              Sériová výroba
            </label>
            <label class="cap-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.suitable_for_single" type="checkbox" data-testid="wc-modal-single" class="toggle-cb" />
              Kusová výroba
            </label>
          </div>
        </div>

        <!-- Sekce 5: Seřízení -->
        <div class="form-section">
          <div class="section-title">Seřízení</div>
          <div class="form-grid">
            <Input
              label="Základ (min)"
              type="number"
              :modelValue="String(modalDraft.setup_base_min)"
              @update:modelValue="modalDraft.setup_base_min = parseReq($event, 30)"
              data-testid="wc-modal-setup-base"
            />
            <Input
              label="Na nástroj (min)"
              type="number"
              :modelValue="String(modalDraft.setup_per_tool_min)"
              @update:modelValue="modalDraft.setup_per_tool_min = parseReq($event, 3)"
              data-testid="wc-modal-setup-tool"
            />
          </div>
        </div>

        <!-- Sekce 6: Organizace -->
        <div class="form-section">
          <div class="section-title">Organizace</div>
          <div class="form-grid">
            <Input
              label="Priorita"
              type="number"
              :modelValue="String(modalDraft.priority)"
              @update:modelValue="modalDraft.priority = parseReq($event, 99)"
              data-testid="wc-modal-priority"
            />
            <label class="active-check">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input v-model="modalDraft.is_active" type="checkbox" data-testid="wc-modal-active" class="toggle-cb" />
              Aktivní
            </label>
            <div class="span-2">
              <Textarea
                label="Poznámky"
                :modelValue="modalDraft.notes ?? ''"
                @update:modelValue="modalDraft.notes = toStrOpt($event)"
                :rows="3"
                data-testid="wc-modal-notes"
              />
            </div>
          </div>
        </div>

      </div>

      <template #footer>
        <button class="btn-secondary" data-testid="wc-modal-cancel" @click="modalOpen = false">
          Zrušit
        </button>
        <button
          class="btn-primary"
          data-testid="wc-modal-save"
          :disabled="saving || !modalDraft.name"
          @click="onSave"
        >
          {{ saving ? 'Ukládám…' : 'Uložit' }}
        </button>
      </template>
    </Modal>
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
  font-size: var(--fsm); color: var(--t3); cursor: pointer; user-select: none;
}
.toggle-cb { accent-color: var(--t1); cursor: pointer; }
.srch-count { font-size: var(--fsm); color: var(--t4); white-space: nowrap; margin-left: auto; }

.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ot tbody tr.inactive td { opacity: 0.45; }
.row-clickable { cursor: pointer; }

.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }

.status-cell { display: flex; flex-direction: column; gap: 2px; }
.badge-recalc { margin-top: 1px; }

/* Modal form */
.modal-form { display: flex; flex-direction: column; gap: 20px; }

.form-section { display: flex; flex-direction: column; gap: 10px; }

.section-title {
  font-size: var(--fsm); color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid var(--b1); padding-bottom: 4px;
}

.form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.form-grid-4 {
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px;
}
.span-2 { grid-column: 1 / -1; }

.rates-computed {
  display: flex; gap: 20px;
  font-size: var(--fsm); color: var(--t3); padding-top: 2px;
}
.rates-computed strong { color: var(--t1); font-weight: 600; }

.caps-row {
  display: flex; flex-wrap: wrap; gap: 16px;
}
.cap-check {
  display: flex; align-items: center; gap: 5px;
  font-size: var(--fsm); color: var(--t2); cursor: pointer; user-select: none;
}

.active-check {
  display: flex; align-items: center; gap: 6px;
  font-size: var(--fsm); color: var(--t2); cursor: pointer; user-select: none;
  align-self: flex-end; padding-bottom: 8px;
}
</style>
