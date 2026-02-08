<script setup lang="ts">
/**
 * OperationRow - Single operation row with inline editing
 * BUILDING BLOCKS (L-039): Molekulární komponent používající atomic UI komponenty
 * LOC TARGET: <200 LOC
 */

import { ref, computed } from 'vue'
import type { Operation, CuttingMode, WorkCenter } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import type { MaterialInputWithOperations } from '@/types/material'
import CuttingModeButtons from '@/components/ui/CuttingModeButtons.vue'
import CoopSettings from '@/components/ui/CoopSettings.vue'
import MaterialLinksInfo from '@/components/ui/MaterialLinksInfo.vue'
import { Trash2, ChevronDown, ChevronRight } from 'lucide-vue-next'
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
  (e: 'update-field', field: keyof Operation, value: any): void
  (e: 'update-work-center', workCenterId: number | null): void
  (e: 'change-mode', mode: CuttingMode): void
  (e: 'toggle-coop'): void
  (e: 'delete'): void
  (e: 'link-material', materialId: number): void
  (e: 'unlink-material', materialId: number): void
  (e: 'select'): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false,
  availableMaterials: () => [],
  selected: false
})

const emit = defineEmits<Emits>()

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
  emit('update-field', field, value)
}

function handleWorkCenterChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('update-work-center', value ? Number(value) : null)
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
    <!-- Seq -->
    <td class="col-seq">
      <span class="op-seq">{{ operation.seq }}</span>
    </td>

    <!-- Work Center -->
    <td class="col-workcenter" @click.stop>
      <select
        :value="operation.work_center_id"
        @change="handleWorkCenterChange"
        class="wc-select"
      >
        <option :value="null">- Pracoviště -</option>
        <option
          v-for="wc in workCenters"
          :key="wc.id"
          :value="wc.id"
        >
          {{ wc.name }}
        </option>
      </select>
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
        :disabled="operation.setup_time_locked"
      />
    </td>

    <!-- tj - operation time -->
    <td class="col-time" @click.stop>
      <input
        type="number"
        step="0.01"
        min="0"
        :value="operation.operation_time_min"
        @focus="($event.target as HTMLInputElement).select()"
        @input="handleTimeInput('operation_time_min', $event)"
        class="time-input"
        :disabled="operation.operation_time_locked"
      />
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
    <td colspan="10" class="expanded-cell">
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
  transition: var(--transition-fast);
}

.operation-row:hover {
  background: var(--state-hover);
}

.operation-row.is-coop {
  border-left: 3px solid var(--color-warning);
}

.operation-row.is-expanded {
  background: var(--state-selected);
}

.operation-row.is-selected {
  background: var(--state-selected);
  border-left: 3px solid var(--color-primary);
}

.operation-row.is-selected:hover {
  background: var(--state-selected);
}

/* === TABLE CELLS === */
.operation-row td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--border-default);
  vertical-align: middle;
}

/* Seq column */
.col-seq {
  text-align: center;
}

.op-seq {
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

/* Work Center Select */
.wc-select {
  width: 100%;
  padding: var(--space-1) var(--space-2);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.wc-select:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Time Inputs */
.time-input {
  width: 100%;
  padding: var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  text-align: right;
}

.time-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.time-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-muted);
}

/* Coefficient Inputs */
.coef-input {
  width: 100%;
  padding: var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  text-align: right;
}

.coef-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Sum values */
.sum-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.sum-value.tp {
  color: var(--color-warning);
}

.sum-value.tj {
  color: var(--color-info);
}

.sum-value.to {
  color: var(--color-success);
}

/* Actions column */
.col-actions {
  text-align: right;
  padding-right: var(--space-2);
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-1);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  transition: var(--transition-fast);
}

.action-btn:hover {
  color: var(--text-primary);
}

.delete-btn:hover {
  color: var(--color-danger);
}

/* Coop Badge (compact) */
.coop-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: var(--color-warning);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: var(--font-semibold);
}

/* === EXPANDED ROW === */
.expanded-row {
  background: var(--bg-muted);
}

.expanded-row td {
  border-bottom: 1px solid var(--border-default);
}

.expanded-cell {
  padding: 0 !important;
}

.op-settings {
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.setting-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}
</style>
