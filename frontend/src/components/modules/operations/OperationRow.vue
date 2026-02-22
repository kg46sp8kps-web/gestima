<script setup lang="ts">
/**
 * OperationRow - Single operation row with inline editing
 * BUILDING BLOCKS (L-039): Molekulární komponent používající atomic UI komponenty
 * LOC TARGET: <200 LOC
 */

import { ref, computed, watch } from 'vue'
import type { Operation, CuttingMode, WorkCenter } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import type { MaterialInputWithOperations } from '@/types/material'
import CuttingModeButtons from '@/components/ui/CuttingModeButtons.vue'
import CoopSettings from '@/components/ui/CoopSettings.vue'
import MaterialLinksInfo from '@/components/ui/MaterialLinksInfo.vue'
import TypeAheadSelect from '@/components/TypeAheadSelect.vue'
import type { TypeAheadOption } from '@/components/TypeAheadSelect.vue'
import { Trash2, ChevronDown, ChevronRight, AlertTriangle, RotateCcw, GripVertical } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  operation: Operation
  workCenters: WorkCenter[]
  availableMaterials: MaterialInputWithOperations[]  // All materials for the part
  expanded: boolean
  saving?: boolean
  selected?: boolean
}

interface Emits {
  (e: 'toggle-expanded'): void
  (e: 'update-field', field: keyof Operation, value: unknown): void
  (e: 'update-work-center', workCenterId: number | null): void
  (e: 'change-mode', mode: CuttingMode): void
  (e: 'toggle-coop'): void
  (e: 'delete'): void
  (e: 'link-material', materialId: number): void
  (e: 'unlink-material', materialId: number): void
  (e: 'select'): void
  (e: 'restore-ai-time'): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false,
  availableMaterials: () => [],
  selected: false
})

const emit = defineEmits<Emits>()

// Track if operation time was modified by user (for AI reload button)
const timeModified = ref(false)
// Track last user-set value to distinguish user edits from external updates
const lastUserTime = ref<number | null>(null)
// Track WorkCenter editing state
const editingWorkCenter = ref(false)
// Track seq editing
const editingSeq = ref(false)
const editingSeqValue = ref<number>(0)

// WorkCenter options for TypeAheadSelect
const workCenterOptions = computed<TypeAheadOption[]>(() =>
  props.workCenters.map(wc => ({
    value: wc.id,
    label: `${wc.work_center_number} — ${wc.name}`
  }))
)

// Fix #3: Reset timeModified when operation_time_min changes externally
// (e.g. AI panel update, restore from parent, store reload)
watch(() => props.operation.operation_time_min, (newVal) => {
  if (lastUserTime.value !== null && newVal !== lastUserTime.value) {
    // External change (not from user input) — reset modified flag
    timeModified.value = false
    lastUserTime.value = null
  }
})

// Compute max work center name width for dropdown sizing
const maxWorkCenterWidth = computed(() => {
  if (props.workCenters.length === 0) return 180
  const maxName = props.workCenters.reduce((max, wc) => {
    return wc.name.length > max.length ? wc.name : max
  }, '')
  // Approximate: 7px per character + padding
  return Math.min(Math.max(maxName.length * 7 + 40, 180), 320)
})

// Time sums calculations (OPRAVENÝ VZOREC)
const timeSums = computed(() => {
  const tp = props.operation.setup_time_min

  // Tj = strojní čas × (1 + (100 - Ke) / 100)
  // Příklad: 10min × (1 + (100-90)/100) = 10 × 1.1 = 11min
  const kePercent = (100 - props.operation.machine_utilization_coefficient) / 100
  const tj = props.operation.operation_time_min * (1 + kePercent)

  // To = čas obsluhy = Tj × (Ko / 100) - JEN ZE STROJNÍHO ČASU!
  const to = tj * (props.operation.manning_coefficient / 100)

  return {
    tp: tp.toFixed(1),
    tj: tj.toFixed(1),
    to: to.toFixed(1)
  }
})

function handleTimeInput(field: 'setup_time_min' | 'operation_time_min', event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (field === 'operation_time_min' && props.operation.ai_estimation_id) {
    timeModified.value = true
    lastUserTime.value = value
  }
  emit('update-field', field, value)
}

function handleRestoreAITime() {
  timeModified.value = false
  emit('restore-ai-time')
}

function handleWorkCenterChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('update-work-center', value ? Number(value) : null)
}

function handleWorkCenterSelect(value: string | number | null) {
  editingWorkCenter.value = false
  emit('update-work-center', value ? Number(value) : null)
}

function handleWorkCenterCancel() {
  editingWorkCenter.value = false
}

function startEditSeq() {
  editingSeq.value = true
  editingSeqValue.value = props.operation.seq
}

function saveSeq() {
  if (editingSeqValue.value !== props.operation.seq) {
    emit('update-field', 'seq', editingSeqValue.value)
  }
  editingSeq.value = false
}

function cancelSeq() {
  editingSeq.value = false
}

function handleCoefficientInput(field: 'manning_coefficient' | 'machine_utilization_coefficient', event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update-field', field, value)
}
</script>

<template>
  <!-- Main data row -->
  <tr
    class="operation-row"
    :class="{ 'is-coop': operation.is_coop, 'is-expanded': expanded, 'is-selected': selected }"
    @click="emit('select')"
  >
    <!-- Drag handle -->
    <td class="col-drag drag-handle" @click.stop>
      <GripVertical :size="ICON_SIZE.SMALL" />
    </td>

    <!-- Seq -->
    <td class="col-seq" @dblclick.stop="startEditSeq">
      <div class="seq-cell">
        <input
          v-if="editingSeq"
          v-model.number="editingSeqValue"
          type="number"
          class="seq-input"
          min="1"
          step="10"
          @click.stop
          @blur="saveSeq"
          @keydown.enter="saveSeq"
          @keydown.escape="cancelSeq"
          @focus="($event.target as HTMLInputElement).select()"
        />
        <span v-else class="op-seq">{{ operation.seq }}</span>
        <AlertTriangle
          v-if="operation.ai_estimation_id"
          :size="ICON_SIZE.SMALL"
          class="ai-indicator"
          title="Existuje AI odhad"
        />
      </div>
    </td>

    <!-- Work Center -->
    <td class="col-workcenter">
      <div v-if="editingWorkCenter" class="typeahead-wrapper" @click.stop>
        <TypeAheadSelect
          :options="workCenterOptions"
          :model-value="operation.work_center_id"
          placeholder="Začni psát..."
          @select="handleWorkCenterSelect"
          @cancel="handleWorkCenterCancel"
        />
      </div>
      <div
        v-else
        class="wc-display"
        :title="workCenters.find(w => w.id === operation.work_center_id)?.name || 'Klikni pro výběr'"
        @click.stop="editingWorkCenter = true"
      >
        {{ workCenters.find(w => w.id === operation.work_center_id)?.work_center_number || '—' }}
      </div>
    </td>

    <!-- tp - setup time -->
    <td class="col-time" @click.stop>
      <input
        type="number"
        step="0.1"
        min="0"
        :value="operation.setup_time_min"
        @focus="($event.target as HTMLInputElement).select()"
        @input="handleTimeInput('setup_time_min', $event)"
        class="time-input"
      />
    </td>

    <!-- tj - operation time (with AI restore button) -->
    <td class="col-time" @click.stop>
      <div class="time-with-restore">
        <input
          type="number"
          step="0.01"
          min="0"
          :value="operation.operation_time_min"
          @focus="($event.target as HTMLInputElement).select()"
          @input="handleTimeInput('operation_time_min', $event)"
          class="time-input"
        />
        <button
          v-if="operation.ai_estimation_id && timeModified"
          class="restore-btn"
          @click="handleRestoreAITime"
          title="Vrátit AI čas"
        >
          <RotateCcw :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </td>

    <!-- Ko coefficient -->
    <td class="col-coef" @click.stop>
      <input
        type="number"
        step="5"
        min="0"
        max="200"
        :value="operation.manning_coefficient"
        @focus="($event.target as HTMLInputElement).select()"
        @input="handleCoefficientInput('manning_coefficient', $event)"
        class="coef-input"
        title="Koeficient obsluhy"
      />
    </td>

    <!-- Ke coefficient -->
    <td class="col-coef" @click.stop>
      <input
        type="number"
        step="5"
        min="0"
        max="200"
        :value="operation.machine_utilization_coefficient"
        @focus="($event.target as HTMLInputElement).select()"
        @input="handleCoefficientInput('machine_utilization_coefficient', $event)"
        class="coef-input"
        title="Koeficient efektivity"
      />
    </td>

    <!-- Tp sum -->
    <td class="col-sum">
      <span class="sum-value tp">{{ timeSums.tp }}</span>
    </td>

    <!-- Tj sum -->
    <td class="col-sum">
      <span class="sum-value tj">{{ timeSums.tj }}</span>
    </td>

    <!-- To sum -->
    <td class="col-sum">
      <span class="sum-value to">{{ timeSums.to }}</span>
    </td>

    <!-- Actions -->
    <td class="col-actions" @click.stop>
      <div class="action-buttons">
        <span v-if="operation.is_coop" class="coop-badge">K</span>
        <button
          class="action-btn delete-btn"
          @click="emit('delete')"
          title="Smazat operaci"
        >
          <Trash2 :size="ICON_SIZE.SMALL" />
        </button>
        <button
          class="action-btn expand-btn"
          @click="emit('toggle-expanded')"
          :title="expanded ? 'Sbalit' : 'Rozbalit nastavení'"
        >
          <ChevronDown v-if="expanded" :size="ICON_SIZE.SMALL" />
          <ChevronRight v-else :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </td>
  </tr>

  <!-- Expanded settings row -->
  <tr v-if="expanded" class="expanded-row">
    <td colspan="11" class="expanded-cell">
      <div class="op-settings">
        <!-- Material Links ONLY -->
        <MaterialLinksInfo
          :operation-id="operation.id"
          :editable="true"
          :available-materials="availableMaterials"
          @link-material="emit('link-material', $event)"
          @unlink-material="emit('unlink-material', $event)"
        />
      </div>
    </td>
  </tr>
</template>

<style scoped>
/* === OPERATION ROW === */
.operation-row {
  cursor: pointer;
  min-height: 28px;
  transition: background 0.04s;
}

.operation-row:hover td {
  background: var(--b1);
}

.operation-row.is-coop {
  border-left: 3px solid var(--warn);
}

.operation-row.is-expanded td {
  background: var(--b1);
}

.operation-row.is-selected td {
  background: var(--red-dim);
}

.operation-row.is-selected:hover td {
  background: var(--red-dim);
}

/* === TABLE CELLS === */
.operation-row td {
  padding: 4px var(--pad);
  font-size: var(--fs);
  border-bottom: 1px solid rgba(255,255,255,0.025);
  vertical-align: middle;
}

/* Drag handle */
.col-drag {
  width: 30px;
  text-align: center;
  cursor: grab;
  padding: 4px;
  color: var(--t3);
  opacity: 0.4;
  transition: opacity all 100ms var(--ease);
}

.col-drag:hover {
  opacity: 1;
  color: var(--t3);
}

.col-drag:active {
  cursor: grabbing;
}

/* Seq input */
.seq-input {
  width: 50px;
  padding: 2px 4px;
  border: 1px solid var(--red);
  border-radius: 4px;
  font-size: var(--fs);
  font-weight: inherit;
  font-family: var(--mono);
  text-align: center;
  background: var(--ground);
  color: var(--t1);
  outline: none;
}

/* WorkCenter display and typeahead */
.wc-display {
  padding: 4px 6px;
  font-size: var(--fs);
  font-weight: inherit;
  color: var(--t2);
  cursor: pointer;
  border-radius: var(--rs);
  transition: background all 100ms var(--ease);
}

.wc-display:hover {
  background: var(--b1);
}

.typeahead-wrapper {
  position: relative;
  min-width: 200px;
}

/* Seq column */
.col-seq {
  text-align: center;
}

.op-seq {
  font-weight: inherit;
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--mono);
}

/* Work Center Select */
.wc-select {
  padding: 4px 6px;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
}

.wc-select:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}

/* Time Inputs — minimal, blend into table like v2 */
.time-input {
  width: 100%;
  padding: 4px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: inherit;
  font-family: var(--mono);
  text-align: right;
  transition: all 100ms var(--ease);
}

.time-input:hover {
  border-color: var(--b1);
}

.time-input:focus {
  outline: none;
  border-color: var(--b3);
  background: rgba(255,255,255,0.03);
}

.time-input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Time input with restore button beside it */
.time-with-restore {
  display: flex;
  align-items: center;
  gap: 2px;
}

.time-with-restore .time-input {
  flex: 1;
  min-width: 0;
}

.restore-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--rs);
  color: var(--err);
  cursor: pointer;
  opacity: 0.6;
  transition: all 100ms var(--ease);
}

.restore-btn:hover {
  opacity: 1;
  background: rgba(248,113,113,0.1);
}

/* Seq cell with AI indicator */
.seq-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.ai-indicator {
  color: var(--ok);
  flex-shrink: 0;
}

/* Coefficient Inputs — minimal, blend into table like v2 */
.coef-input {
  width: 100%;
  padding: 4px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: inherit;
  font-family: var(--mono);
  text-align: right;
  transition: all 100ms var(--ease);
}

.coef-input:hover {
  border-color: var(--b1);
}

.coef-input:focus {
  outline: none;
  border-color: var(--b3);
  background: rgba(255,255,255,0.03);
}

/* Sum values */
.sum-value {
  font-family: var(--mono);
  font-size: var(--fs);
  font-weight: inherit;
  color: var(--t1);
}

.sum-value.tp {
  color: var(--warn);
}

.sum-value.tj {
  color: var(--t3);
}

.sum-value.to {
  color: var(--ok);
}

/* Actions column */
.col-actions {
  text-align: right;
  padding-right: 6px;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--t3);
  transition: all 100ms var(--ease);
}

.action-btn:hover {
  color: var(--t1);
}

.delete-btn:hover {
  color: var(--err);
}

/* Coop Badge (compact) */
.coop-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: var(--warn);
  color: white;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
}

/* === EXPANDED ROW === */
.expanded-row {
  background: var(--surface);
}

.expanded-row td {
  border-bottom: 1px solid var(--b2);
}

.expanded-cell {
  padding: 0;
}

.op-settings {
  padding: var(--pad);
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-label {
  font-size: var(--fs);
  color: var(--t3);
  font-weight: 500;
}
</style>
