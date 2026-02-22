<script setup lang="ts">
/**
 * TileOperationRow — single operation row for tiling workspace
 * v2 CSS styling: time badges, compact layout, expandable settings
 */

import { ref, computed, watch } from 'vue'
import type { Operation, CuttingMode, WorkCenter } from '@/types/operation'
import type { MaterialInputWithOperations } from '@/types/material'
import CuttingModeButtons from '@/components/ui/CuttingModeButtons.vue'
import CoopSettings from '@/components/ui/CoopSettings.vue'
import MaterialLinksInfo from '@/components/ui/MaterialLinksInfo.vue'
import TypeAheadSelect from '@/components/TypeAheadSelect.vue'
import type { TypeAheadOption } from '@/components/TypeAheadSelect.vue'
import { Trash2, ChevronDown, ChevronRight, RotateCcw, GripVertical } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  operation: Operation
  workCenters: WorkCenter[]
  availableMaterials: MaterialInputWithOperations[]
  expanded: boolean
  saving?: boolean
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  saving: false,
  availableMaterials: () => [],
  selected: false,
})

const emit = defineEmits<{
  'toggle-expanded': []
  'update-field': [field: keyof Operation, value: unknown]
  'update-work-center': [workCenterId: number | null]
  'change-mode': [mode: CuttingMode]
  'toggle-coop': []
  'delete': []
  'link-material': [materialId: number]
  'unlink-material': [materialId: number]
  'select': []
  'restore-ai-time': []
}>()

// Track if operation time was modified by user (for AI reload button)
const timeModified = ref(false)
const lastUserTime = ref<number | null>(null)
const editingWorkCenter = ref(false)
const editingSeq = ref(false)
const editingSeqValue = ref<number>(0)

// WorkCenter options for TypeAheadSelect
const workCenterOptions = computed<TypeAheadOption[]>(() =>
  props.workCenters.map(wc => ({
    value: wc.id,
    label: `${wc.work_center_number} — ${wc.name}`,
  })),
)

// Reset timeModified when operation_time_min changes externally
watch(() => props.operation.operation_time_min, (newVal) => {
  if (lastUserTime.value !== null && newVal !== lastUserTime.value) {
    timeModified.value = false
    lastUserTime.value = null
  }
})

// Work center display name
const wcName = computed(() => {
  const wc = props.workCenters.find(w => w.id === props.operation.work_center_id)
  return wc?.name ?? '—'
})

// Format time as MM:SS for time badges
function formatTime(minutes: number): string {
  if (!minutes || minutes <= 0) return '—'
  const mins = Math.floor(minutes)
  const secs = Math.round((minutes - mins) * 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

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
    class="op-row"
    :class="{ sel: selected, coop: operation.is_coop }"
    @click="emit('select')"
  >
    <!-- Drag handle -->
    <td class="col-drag drag-handle" @click.stop>
      <GripVertical :size="ICON_SIZE.SMALL" />
    </td>

    <!-- Seq -->
    <td class="col-seq" @dblclick.stop="startEditSeq">
      <input
        v-if="editingSeq"
        v-model.number="editingSeqValue"
        type="number"
        class="seq-input"
        min="1"
        step="10"
        data-testid="seq-input"
        @click.stop
        @blur="saveSeq"
        @keydown.enter="saveSeq"
        @keydown.escape="cancelSeq"
        @focus="($event.target as HTMLInputElement).select()"
      />
      <span v-else class="seq-val">{{ operation.seq }}</span>
    </td>

    <!-- Pracoviště -->
    <td class="col-wc" @click.stop>
      <div v-if="editingWorkCenter" class="wc-typeahead" @click.stop>
        <TypeAheadSelect
          :options="workCenterOptions"
          :model-value="operation.work_center_id"
          placeholder="Hledat..."
          @select="handleWorkCenterSelect"
          @cancel="handleWorkCenterCancel"
        />
      </div>
      <div
        v-else
        class="wc-display"
        :title="wcName"
        data-testid="wc-select"
        @click="editingWorkCenter = true"
      >
        {{ wcName }}
      </div>
    </td>

    <!-- Operace -->
    <td class="col-name">{{ operation.name }}</td>

    <!-- Seříz. (setup time badge) -->
    <td class="col-r" @click.stop>
      <span v-if="operation.setup_time_min > 0" class="tb s">
        <span class="d" />{{ formatTime(operation.setup_time_min) }}
      </span>
      <span v-else class="no-time">—</span>
    </td>

    <!-- Čas/ks (operation time badge) -->
    <td class="col-r" @click.stop>
      <span v-if="operation.operation_time_min > 0" class="tb o">
        <span class="d" />{{ formatTime(operation.operation_time_min) }}
      </span>
      <span v-else class="no-time">—</span>
      <button
        v-if="operation.ai_estimation_id && timeModified"
        class="restore-btn"
        data-testid="restore-ai-time"
        title="Vrátit AI čas"
        @click.stop="handleRestoreAITime"
      >
        <RotateCcw :size="10" />
      </button>
    </td>

    <!-- Actions -->
    <td class="col-acts" @click.stop>
      <div class="acts-row">
        <span v-if="operation.is_coop" class="coop-tag">K</span>
        <button
          class="act-btn del"
          data-testid="delete-operation"
          title="Smazat operaci"
          @click="emit('delete')"
        >
          <Trash2 :size="ICON_SIZE.SMALL" />
        </button>
        <button
          class="act-btn exp"
          :data-testid="'expand-op-' + operation.id"
          :title="expanded ? 'Sbalit' : 'Rozbalit'"
          @click="emit('toggle-expanded')"
        >
          <ChevronDown v-if="expanded" :size="ICON_SIZE.SMALL" />
          <ChevronRight v-else :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </td>
  </tr>

  <!-- Expanded settings row -->
  <tr v-if="expanded" class="exp-row">
    <td :colspan="7" class="exp-cell">
      <div class="exp-content">
        <!-- Settings row: times + coefficients + cutting mode + coop -->
        <div class="settings-grid">
          <div class="setting-group">
            <label class="s-label">tp (min)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="operation.setup_time_min"
              class="s-input"
              data-testid="setup-time-input"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleTimeInput('setup_time_min', $event)"
            />
          </div>
          <div class="setting-group">
            <label class="s-label">tj (min)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              :value="operation.operation_time_min"
              class="s-input"
              data-testid="op-time-input"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleTimeInput('operation_time_min', $event)"
            />
          </div>
          <div class="setting-group">
            <label class="s-label">Ko (%)</label>
            <input
              type="number"
              step="5"
              min="0"
              max="200"
              :value="operation.manning_coefficient"
              class="s-input"
              data-testid="ko-input"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleCoefficientInput('manning_coefficient', $event)"
            />
          </div>
          <div class="setting-group">
            <label class="s-label">Ke (%)</label>
            <input
              type="number"
              step="5"
              min="0"
              max="200"
              :value="operation.machine_utilization_coefficient"
              class="s-input"
              data-testid="ke-input"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleCoefficientInput('machine_utilization_coefficient', $event)"
            />
          </div>
          <div class="setting-group mode-group">
            <label class="s-label">Režim</label>
            <CuttingModeButtons
              :mode="operation.cutting_mode"
              :disabled="saving"
              @change="(mode: CuttingMode) => emit('change-mode', mode)"
            />
          </div>
          <div class="setting-group coop-group">
            <CoopSettings
              :is-coop="operation.is_coop"
              :coop-price="operation.coop_price"
              :coop-min-price="operation.coop_min_price"
              :coop-days="operation.coop_days"
              :disabled="saving"
              @toggle="emit('toggle-coop')"
              @update:price="(v: number) => emit('update-field', 'coop_price', v)"
              @update:min-price="(v: number) => emit('update-field', 'coop_min_price', v)"
              @update:days="(v: number) => emit('update-field', 'coop_days', v)"
            />
          </div>
        </div>

        <!-- Material links -->
        <MaterialLinksInfo
          :operation-id="operation.id"
          :editable="true"
          :available-materials="availableMaterials"
          @link-material="(id: number) => emit('link-material', id)"
          @unlink-material="(id: number) => emit('unlink-material', id)"
        />
      </div>
    </td>
  </tr>
</template>

<style scoped>
/* ═══ ROW STYLES (v2 tiling) ═══ */
.op-row {
  cursor: pointer;
  transition: background 0.04s;
}

.op-row:hover {
  background: var(--b1);
}

.op-row.sel {
  background: var(--red-dim);
}

.op-row.coop {
  border-left: 2px solid var(--warn);
}

.op-row td {
  padding: 4px var(--pad);
  border-bottom: 1px solid rgba(255, 255, 255, 0.025);
  vertical-align: middle;
  font-size: var(--fs);
  color: var(--t2);
}

/* ═══ COLUMNS ═══ */
.col-drag {
  width: 24px;
  text-align: center;
  cursor: grab;
  color: var(--t4);
  opacity: 0.4;
  transition: opacity 0.08s;
  padding: 4px 2px;
}

.col-drag:hover {
  opacity: 1;
  color: var(--t3);
}

.col-drag:active {
  cursor: grabbing;
}

.col-seq {
  width: 40px;
  text-align: center;
  font-family: var(--mono);
  font-weight: 600;
  color: var(--t1);
}

.seq-val {
  font-family: var(--mono);
  font-weight: 600;
  color: var(--t1);
}

.seq-input {
  width: 44px;
  padding: 1px 2px;
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-family: var(--mono);
  font-weight: 600;
  text-align: center;
  background: var(--ground);
  color: var(--t1);
  outline: none;
}

.col-wc {
  min-width: 120px;
}

.wc-display {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  cursor: pointer;
  padding: 1px 4px;
  border-radius: var(--rs);
  transition: background 0.08s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.wc-display:hover {
  background: var(--b1);
}

.wc-typeahead {
  position: relative;
  min-width: 180px;
}

.col-name {
  color: var(--t3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.col-r {
  text-align: right;
  white-space: nowrap;
}

.no-time {
  color: var(--t4);
  font-size: var(--fs);
}

/* ═══ TIME BADGES (v2) ═══ */
.tb {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-family: var(--mono);
  font-size: var(--fsl);
  border-radius: 99px;
  background: var(--b1);
  color: var(--t3);
}

.tb .d {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tb.s .d {
  background: var(--red);
}

.tb.o .d {
  background: var(--ok);
}

.restore-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  margin-left: 2px;
  background: none;
  border: none;
  border-radius: var(--rs);
  color: var(--err);
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.08s;
}

.restore-btn:hover {
  opacity: 1;
}

/* ═══ ACTIONS ═══ */
.col-acts {
  width: 70px;
  text-align: right;
  padding-right: 6px;
}

.acts-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

.act-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--t4);
  transition: color 0.08s;
  border-radius: var(--rs);
}

.act-btn:hover {
  color: var(--t1);
}

.act-btn.del:hover {
  color: var(--err);
}

.coop-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: var(--warn);
  color: var(--base);
  border-radius: var(--rs);
  font-size: var(--fsl);
  font-weight: 700;
}

/* ═══ EXPANDED ROW ═══ */
.exp-row {
  background: var(--raised);
}

.exp-row td {
  border-bottom: 1px solid var(--b1);
}

.exp-cell {
  padding: 0;
}

.exp-content {
  padding: var(--pad);
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.settings-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--pad);
  align-items: flex-end;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.s-label {
  font-size: var(--fsl);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}

.s-input {
  width: 72px;
  padding: 2px 4px;
  background: var(--ground);
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 600;
  font-family: var(--mono);
  text-align: right;
}

.s-input:focus {
  outline: none;
  border-color: var(--b3);
}

.mode-group,
.coop-group {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
</style>
