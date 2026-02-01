<script setup lang="ts">
/**
 * Operations Detail Panel Component
 * Inline editing pattern - edit tp/tj/work center directly on row
 * Expand only for advanced settings (cutting mode, coop)
 */

import { ref, computed, watch, reactive } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import type { Operation, CuttingMode } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import DeleteOperationModal from './DeleteOperationModal.vue'
import { Settings, Trash2, Lock, Unlock, Wrench, RotateCw, Scissors, Gem } from 'lucide-vue-next'
import type { Component } from 'vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const operationsStore = useOperationsStore()

// Local state
const expandedOps = reactive<Record<number, boolean>>({})
const showDeleteConfirm = ref(false)
const operationToDelete = ref<Operation | null>(null)

// Debounce timers per operation
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()

// Computed from store (per-context)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)

// Computed from store (global)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// Compute max work center name width for dropdown sizing
const maxWorkCenterWidth = computed(() => {
  if (activeWorkCenters.value.length === 0) return 180
  const maxName = activeWorkCenters.value.reduce((max, wc) => {
    const name = `${wc.work_center_number} - ${wc.name}`
    return name.length > max.length ? name : max
  }, '')
  // Approximate: 7px per character + padding
  return Math.min(Math.max(maxName.length * 7 + 40, 180), 320)
})

// Watch partId change (when linked)
watch(() => props.partId, async (newPartId) => {
  if (newPartId) {
    await loadData(newPartId)
  }
}, { immediate: true })

// Load data
async function loadData(partId: number) {
  await Promise.all([
    operationsStore.loadWorkCenters(),
    operationsStore.loadOperations(partId, props.linkingGroup)
  ])
}

// Toggle expanded state
function toggleExpanded(opId: number) {
  expandedOps[opId] = !expandedOps[opId]
}

// Debounced update operation
function debouncedUpdateOperation(op: Operation, field: keyof Operation, value: any) {
  // Update local state immediately for responsive UI
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1) {
    ;(operations.value[opIndex] as any)[field] = value
  }

  // Clear existing timer for this operation
  const existingTimer = debounceTimers.get(op.id)
  if (existingTimer) {
    clearTimeout(existingTimer)
  }

  // Set new timer
  const timer = setTimeout(async () => {
    debounceTimers.delete(op.id)
    await operationsStore.updateOperation(op.id, { [field]: value }, props.linkingGroup)
  }, 500)

  debounceTimers.set(op.id, timer)
}

// Handle work center change
async function onWorkCenterChange(op: Operation, newWorkCenterId: number | null) {
  // Update work center
  const updates: Partial<Operation> = {
    work_center_id: newWorkCenterId
  }

  // Update type/icon/name based on work center
  if (newWorkCenterId) {
    const wc = activeWorkCenters.value.find(w => w.id === newWorkCenterId)
    if (wc) {
      const wcType = wc.work_center_type.toLowerCase().replace('cnc_', '').replace('_', '')
      const mapping = OPERATION_TYPE_MAP[wcType] ?? OPERATION_TYPE_MAP.generic
      if (mapping) {
        updates.name = `OP${op.seq} - ${mapping.label}`
        updates.type = mapping.type
        updates.icon = mapping.icon
      }
    }
  }

  // Update local state immediately
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  const opToUpdate = operations.value[opIndex]
  if (opIndex !== -1 && opToUpdate) {
    Object.assign(opToUpdate, updates)
  }

  // Save to backend
  await operationsStore.updateOperation(op.id, updates, props.linkingGroup)
}

// Change cutting mode
async function changeMode(op: Operation, mode: CuttingMode) {
  await operationsStore.changeMode(op.id, mode, props.linkingGroup)
}

// Toggle coop mode
async function toggleCoop(op: Operation) {
  const newValue = !op.is_coop
  // Update local state immediately
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1 && operations.value[opIndex]) {
    operations.value[opIndex]!.is_coop = newValue
  }
  await operationsStore.updateOperation(op.id, { is_coop: newValue }, props.linkingGroup)
}

// Update coop fields with debounce
function updateCoopField(op: Operation, field: 'coop_price' | 'coop_min_price' | 'coop_days', value: number) {
  debouncedUpdateOperation(op, field, value)
}

// Add new operation
async function handleAddOperation() {
  if (!props.partId) return

  const newOp = await operationsStore.addOperation(props.partId, props.linkingGroup)
  if (newOp) {
    // Expand new operation to show settings
    expandedOps[newOp.id] = true
  }
}

// Delete confirmation
function confirmDelete(op: Operation) {
  operationToDelete.value = op
  showDeleteConfirm.value = true
}

async function executeDelete() {
  if (!operationToDelete.value) return

  const opId = operationToDelete.value.id
  await operationsStore.deleteOperation(opId, props.linkingGroup)
  delete expandedOps[opId]

  showDeleteConfirm.value = false
  operationToDelete.value = null
}

// Icon mapping: string → Lucide component
const iconMap: Record<string, Component> = {
  'wrench': Wrench,
  'rotate-cw': RotateCw,
  'scissors': Scissors,
  'gem': Gem,
  'settings': Settings
}

function getIconComponent(iconName: string): Component {
  return iconMap[iconName] || Wrench
}

// Expose operationsCount for parent
defineExpose({
  operationsCount: computed(() => operations.value.length)
})
</script>

<template>
  <div class="operations-detail-panel">
    <!-- Header with Add button -->
    <div class="panel-header">
      <h3>Operace</h3>
      <button
        class="btn-add"
        @click="handleAddOperation"
        :disabled="!partId || loading"
      >
        + Přidat operaci
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Načítám operace...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="operations.length === 0" class="empty">
      <Settings :size="48" class="empty-icon" />
      <p>Žádné operace</p>
      <p class="hint">Klikni na "+ Přidat operaci" pro začátek</p>
    </div>

    <!-- Operations List -->
    <div v-else class="operations-list">
      <div
        v-for="op in sortedOperations"
        :key="op.id"
        class="operation-card"
        :class="{ 'is-coop': op.is_coop, 'is-expanded': expandedOps[op.id] }"
      >
        <!-- Inline Row - editable fields directly visible -->
        <div class="op-row">
          <!-- Seq only -->
          <div class="op-seq-icon">
            <span class="op-seq">{{ op.seq }}</span>
          </div>

          <!-- Work Center Dropdown (inline) -->
          <div class="op-work-center" @click.stop>
            <select
              :value="op.work_center_id"
              @change="onWorkCenterChange(op, ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
              class="wc-select"
              :style="{ width: maxWorkCenterWidth + 'px' }"
            >
              <option :value="null">- Pracoviště -</option>
              <option
                v-for="wc in activeWorkCenters"
                :key="wc.id"
                :value="wc.id"
              >
                {{ wc.work_center_number }} - {{ wc.name }}
              </option>
            </select>
          </div>

          <!-- tp - setup time (inline editable) -->
          <div class="time-field" @click.stop>
            <span class="time-label tp">tp:</span>
            <input
              v-select-on-focus
              type="number"
              step="0.1"
              min="0"
              :value="op.setup_time_min"
              @input="debouncedUpdateOperation(op, 'setup_time_min', Number(($event.target as HTMLInputElement).value))"
              class="time-input"
              :disabled="op.setup_time_locked"
            />
            <span class="time-unit">min</span>
            <button
              class="lock-btn"
              :class="{ 'is-locked': op.setup_time_locked }"
              @click="debouncedUpdateOperation(op, 'setup_time_locked', !op.setup_time_locked)"
              :title="op.setup_time_locked ? 'Odemknout' : 'Zamknout'"
            >
              <Lock v-if="op.setup_time_locked" :size="12" />
              <Unlock v-else :size="12" />
            </button>
          </div>

          <!-- tj - operation time (inline editable) -->
          <div class="time-field" @click.stop>
            <span class="time-label tj">tj:</span>
            <input
              v-select-on-focus
              type="number"
              step="0.01"
              min="0"
              :value="op.operation_time_min"
              @input="debouncedUpdateOperation(op, 'operation_time_min', Number(($event.target as HTMLInputElement).value))"
              class="time-input"
              :disabled="op.operation_time_locked"
            />
            <span class="time-unit">min</span>
            <button
              class="lock-btn"
              :class="{ 'is-locked': op.operation_time_locked }"
              @click="debouncedUpdateOperation(op, 'operation_time_locked', !op.operation_time_locked)"
              :title="op.operation_time_locked ? 'Odemknout' : 'Zamknout'"
            >
              <Lock v-if="op.operation_time_locked" :size="12" />
              <Unlock v-else :size="12" />
            </button>
          </div>

          <!-- Coop badge -->
          <span v-if="op.is_coop" class="coop-badge">Koop</span>

          <!-- Delete button -->
          <button
            class="delete-btn"
            @click.stop="confirmDelete(op)"
            title="Smazat operaci"
          >
            <Trash2 :size="16" />
          </button>

          <!-- Expand toggle -->
          <button
            class="expand-btn"
            @click="toggleExpanded(op.id)"
            :title="expandedOps[op.id] ? 'Sbalit' : 'Rozbalit nastavení'"
          >
            {{ expandedOps[op.id] ? '▼' : '▶' }}
          </button>
        </div>

        <!-- Expanded Settings (cutting mode, coop) -->
        <div v-if="expandedOps[op.id]" class="op-settings">
          <!-- Cutting Mode -->
          <div class="setting-group">
            <label class="setting-label">Režim řezání</label>
            <div class="mode-buttons">
              <button
                @click="changeMode(op, 'low')"
                :class="{ active: op.cutting_mode === 'low' }"
                class="mode-btn mode-low"
                :disabled="saving"
              >
                LOW
              </button>
              <button
                @click="changeMode(op, 'mid')"
                :class="{ active: op.cutting_mode === 'mid' }"
                class="mode-btn mode-mid"
                :disabled="saving"
              >
                MID
              </button>
              <button
                @click="changeMode(op, 'high')"
                :class="{ active: op.cutting_mode === 'high' }"
                class="mode-btn mode-high"
                :disabled="saving"
              >
                HIGH
              </button>
            </div>
          </div>

          <!-- Coop Toggle -->
          <div class="setting-group">
            <label class="coop-toggle">
              <input
                type="checkbox"
                :checked="op.is_coop"
                @change="toggleCoop(op)"
              />
              Kooperace (externí dodavatel)
            </label>
          </div>

          <!-- Coop Fields (conditional) -->
          <div v-if="op.is_coop" class="coop-fields">
            <div class="coop-field">
              <label>Cena [Kč]</label>
              <input
                v-select-on-focus
                type="number"
                min="0"
                step="1"
                :value="op.coop_price"
                @input="updateCoopField(op, 'coop_price', Number(($event.target as HTMLInputElement).value))"
                class="coop-input"
              />
            </div>
            <div class="coop-field">
              <label>Min. cena [Kč]</label>
              <input
                v-select-on-focus
                type="number"
                min="0"
                step="1"
                :value="op.coop_min_price"
                @input="updateCoopField(op, 'coop_min_price', Number(($event.target as HTMLInputElement).value))"
                class="coop-input"
              />
            </div>
            <div class="coop-field">
              <label>Dní</label>
              <input
                v-select-on-focus
                type="number"
                min="0"
                :value="op.coop_days"
                @input="updateCoopField(op, 'coop_days', Number(($event.target as HTMLInputElement).value))"
                class="coop-input"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <DeleteOperationModal
      :show="showDeleteConfirm"
      :operation="operationToDelete"
      @confirm="executeDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<style scoped>
/* === PANEL LAYOUT === */
.operations-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  padding: var(--space-3);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-add {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-add:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* === LOADING === */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6);
  color: var(--text-secondary);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* === EMPTY === */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-icon {
  color: var(--text-secondary);
}

.empty p {
  margin: 0;
  font-size: var(--text-sm);
}

.empty .hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* === OPERATIONS LIST === */
.operations-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  overflow-y: auto;
  flex: 1;
}

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

.op-icon {
  font-size: var(--text-sm);
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
  border-color: var(--color-primary);
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

.lock-btn {
  padding: var(--space-1);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--text-xs);
  opacity: 0.5;
  transition: var(--transition-fast);
}

.lock-btn:hover {
  opacity: 1;
}

.lock-btn.is-locked {
  opacity: 1;
}

/* Coop Badge */
.coop-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  margin-left: auto;
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

/* Mode Buttons */
.mode-buttons {
  display: flex;
  gap: var(--space-1);
}

.mode-btn {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: var(--transition-fast);
}

.mode-btn:hover:not(:disabled) {
  background: var(--state-hover);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-btn.active {
  color: white;
}

.mode-btn.mode-low.active {
  background: #10b981;
  border-color: #10b981;
}

.mode-btn.mode-mid.active {
  background: #f59e0b;
  border-color: #f59e0b;
}

.mode-btn.mode-high.active {
  background: #ef4444;
  border-color: #ef4444;
}

/* Coop Toggle */
.coop-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.coop-toggle input {
  cursor: pointer;
}

/* Coop Fields */
.coop-fields {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-warning);
}

.coop-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.coop-field label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.coop-input {
  width: 80px;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.coop-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}
</style>
