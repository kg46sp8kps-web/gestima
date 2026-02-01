<script setup lang="ts">
/**
 * OperationRow - Single operation row with inline editing
 * BUILDING BLOCKS (L-039): Molekulární komponent používající atomic UI komponenty
 * LOC TARGET: <200 LOC
 */

import { ref, computed } from 'vue'
import type { Operation, CuttingMode, WorkCenter } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import CuttingModeButtons from '@/components/ui/CuttingModeButtons.vue'
import CoopSettings from '@/components/ui/CoopSettings.vue'
import MaterialLinksInfo from '@/components/ui/MaterialLinksInfo.vue'
import { Trash2, ChevronDown, ChevronRight } from 'lucide-vue-next'

interface Props {
  operation: Operation
  workCenters: WorkCenter[]
  expanded: boolean
  saving?: boolean
}

interface Emits {
  (e: 'toggle-expanded'): void
  (e: 'update-field', field: keyof Operation, value: any): void
  (e: 'update-work-center', workCenterId: number | null): void
  (e: 'change-mode', mode: CuttingMode): void
  (e: 'toggle-coop'): void
  (e: 'delete'): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
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

// Time sums calculations (podle schváleného vzorce)
const timeSums = computed(() => {
  const tp = props.operation.setup_time_min
  const tj = props.operation.operation_time_min / (props.operation.machine_utilization_coefficient / 100)
  const to = (tp + tj) * (props.operation.manning_coefficient / 100)

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
  <div
    class="operation-card"
    :class="{ 'is-coop': operation.is_coop, 'is-expanded': expanded }"
  >
    <!-- Inline Row - clickable to expand/collapse -->
    <div class="op-row" @click="emit('toggle-expanded')">
      <!-- Seq -->
      <div class="op-seq-icon">
        <span class="op-seq">{{ operation.seq }}</span>
      </div>

      <!-- Work Center Dropdown (inline) -->
      <div class="op-work-center" @click.stop>
        <select
          :value="operation.work_center_id"
          @change="handleWorkCenterChange"
          class="wc-select"
          :style="{ width: maxWorkCenterWidth + 'px' }"
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
      </div>

      <!-- tp - setup time (inline editable) -->
      <div class="time-field" @click.stop>
        <span class="time-label tp">tp:</span>
        <input
          type="number"
          step="0.1"
          min="0"
          :value="operation.setup_time_min"
          @input="handleTimeInput('setup_time_min', $event)"
          class="time-input"
          :disabled="operation.setup_time_locked"
        />
        <span class="time-unit">min</span>
      </div>

      <!-- tj - operation time (inline editable) -->
      <div class="time-field" @click.stop>
        <span class="time-label tj">tj:</span>
        <input
          type="number"
          step="0.01"
          min="0"
          :value="operation.operation_time_min"
          @input="handleTimeInput('operation_time_min', $event)"
          class="time-input"
          :disabled="operation.operation_time_locked"
        />
        <span class="time-unit">min</span>
      </div>

      <!-- Coefficients (inline editable) -->
      <div class="coef-field" @click.stop>
        <span class="coef-label">Plnění:</span>
        <input
          type="number"
          step="5"
          min="0"
          max="200"
          :value="operation.manning_coefficient"
          @input="handleCoefficientInput('manning_coefficient', $event)"
          class="coef-input"
        />
        <span class="coef-unit">%</span>
      </div>

      <div class="coef-field" @click.stop>
        <span class="coef-label">Využití:</span>
        <input
          type="number"
          step="5"
          min="0"
          max="200"
          :value="operation.machine_utilization_coefficient"
          @input="handleCoefficientInput('machine_utilization_coefficient', $event)"
          class="coef-input"
        />
        <span class="coef-unit">%</span>
      </div>

      <!-- Time Sums (Tp, Tj, To) -->
      <div class="time-sums">
        <span class="sum-item tp">Tp: {{ timeSums.tp }}</span>
        <span class="sum-item tj">Tj: {{ timeSums.tj }}</span>
        <span class="sum-item to">To: {{ timeSums.to }}</span>
      </div>

      <!-- Coop badge -->
      <span v-if="operation.is_coop" class="coop-badge">Koop</span>

      <!-- Delete button -->
      <button
        class="delete-btn"
        @click.stop="emit('delete')"
        title="Smazat operaci"
      >
        <Trash2 :size="16" />
      </button>

      <!-- Expand toggle -->
      <button
        class="expand-btn"
        @click.stop="emit('toggle-expanded')"
        :title="expanded ? 'Sbalit' : 'Rozbalit nastavení'"
      >
        <ChevronDown v-if="expanded" :size="16" />
        <ChevronRight v-else :size="16" />
      </button>
    </div>

    <!-- Expanded Settings (cutting mode, coop, materials) -->
    <div v-if="expanded" class="op-settings">
      <!-- Cutting Mode -->
      <div class="setting-group">
        <label class="setting-label">Režim řezání</label>
        <CuttingModeButtons
          :mode="operation.cutting_mode"
          :disabled="saving"
          @change="emit('change-mode', $event)"
        />
      </div>

      <!-- Coop Settings -->
      <CoopSettings
        :is-coop="operation.is_coop"
        :coop-price="operation.coop_price"
        :coop-min-price="operation.coop_min_price"
        :coop-days="operation.coop_days"
        :disabled="saving"
        @toggle="emit('toggle-coop')"
        @update:price="emit('update-field', 'coop_price', $event)"
        @update:min-price="emit('update-field', 'coop_min_price', $event)"
        @update:days="emit('update-field', 'coop_days', $event)"
      />

      <!-- Material Links -->
      <div class="setting-group">
        <MaterialLinksInfo :operation-id="operation.id" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === OPERATION CARD === */
.operation-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: var(--transition-fast);
}

.operation-card.is-coop {
  border-left: 3px solid var(--color-warning);
}

.operation-card.is-expanded {
  border-color: var(--color-primary);
}

/* === INLINE ROW === */
.op-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  cursor: pointer;
}

.op-row:hover {
  background: var(--state-hover);
}

.op-seq-icon {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  min-width: 50px;
}

.op-seq {
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

/* Work Center Select */
.op-work-center {
  flex-shrink: 0;
}

.wc-select {
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

/* Time Fields */
.time-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.time-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.time-label.tp {
  color: var(--color-warning);
}

.time-label.tj {
  color: var(--color-primary);
}

.time-input {
  width: 55px;
  padding: var(--space-1) var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
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

.time-unit {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* Coefficient Fields */
.coef-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.coef-label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.coef-input {
  width: 45px;
  padding: var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-align: right;
}

.coef-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.coef-unit {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* Time Sums */
.time-sums {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.sum-item {
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.sum-item.tp {
  color: var(--color-warning);
}

.sum-item.tj {
  color: var(--color-info);
}

.sum-item.to {
  color: var(--color-success);
}

/* Coop Badge */
.coop-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

/* Delete Button */
.delete-btn {
  padding: var(--space-1);
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--text-sm);
  opacity: 0.4;
  transition: var(--transition-fast);
}

.delete-btn:hover {
  opacity: 1;
  color: var(--color-danger);
}

/* Expand Button */
.expand-btn {
  padding: var(--space-1) var(--space-2);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--text-xs);
  color: var(--text-muted);
  transition: var(--transition-fast);
}

.expand-btn:hover {
  color: var(--text-primary);
}

/* === EXPANDED SETTINGS === */
.op-settings {
  padding: var(--space-3);
  border-top: 1px solid var(--border-default);
  background: var(--bg-muted);
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
