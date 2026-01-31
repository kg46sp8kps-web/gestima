<script setup lang="ts">
/**
 * Operations Detail Panel Component
 * Manages operations list with expand/collapse and inline editing
 */

import { ref, computed, watch, reactive } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import type { Operation, CuttingMode } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import DeleteOperationModal from './DeleteOperationModal.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

interface EditForm {
  name: string
  work_center_id: number | null
  setup_time_min: number
  operation_time_min: number
  setup_time_locked: boolean
  operation_time_locked: boolean
  cutting_mode: CuttingMode
  is_coop: boolean
  coop_price: number
  coop_min_price: number
  coop_days: number
}

const operationsStore = useOperationsStore()

// Local state
const editForms = reactive<Record<number, EditForm>>({})
const showDeleteConfirm = ref(false)
const operationToDelete = ref<Operation | null>(null)

// Computed from store (per-context)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const expandedOps = computed(() => operationsStore.getContext(props.linkingGroup).expandedOps)
// Computed from store (global)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// Helper to safely get form (used in template after v-if guard)
function form(opId: number): EditForm {
  return editForms[opId]!
}

// Initialize edit forms for all operations
function initEditForms() {
  for (const op of operations.value) {
    if (!editForms[op.id]) {
      editForms[op.id] = createEditForm(op)
    }
  }
}

// Create edit form from operation
function createEditForm(op: Operation): EditForm {
  return {
    name: op.name,
    work_center_id: op.work_center_id,
    setup_time_min: op.setup_time_min,
    operation_time_min: op.operation_time_min,
    setup_time_locked: op.setup_time_locked,
    operation_time_locked: op.operation_time_locked,
    cutting_mode: op.cutting_mode,
    is_coop: op.is_coop,
    coop_price: op.coop_price,
    coop_min_price: op.coop_min_price,
    coop_days: op.coop_days
  }
}

// Watch operations changes to update edit forms
watch(operations, () => {
  initEditForms()
}, { deep: true })

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
  initEditForms()
}

// Toggle expanded state
function toggleExpanded(opId: number) {
  const ctx = operationsStore.getContext(props.linkingGroup)
  ctx.expandedOps[opId] = !ctx.expandedOps[opId]
}

// Add new operation
async function handleAddOperation() {
  if (!props.partId) return

  const newOp = await operationsStore.addOperation(props.partId, props.linkingGroup)
  if (newOp) {
    editForms[newOp.id] = createEditForm(newOp)
  }
}

// Save operation
async function saveOperation(op: Operation) {
  const formData = editForms[op.id]
  if (!formData) return

  await operationsStore.updateOperation(op.id, {
    name: formData.name,
    work_center_id: formData.work_center_id,
    setup_time_min: formData.setup_time_min,
    operation_time_min: formData.operation_time_min,
    setup_time_locked: formData.setup_time_locked,
    operation_time_locked: formData.operation_time_locked,
    cutting_mode: formData.cutting_mode,
    is_coop: formData.is_coop,
    coop_price: formData.coop_price,
    coop_min_price: formData.coop_min_price,
    coop_days: formData.coop_days
  }, props.linkingGroup)
}

// Handle work center change (update type/icon)
function onWorkCenterChange(opId: number) {
  const formData = editForms[opId]
  if (!formData) return

  const wcId = formData.work_center_id
  if (!wcId) {
    // No work center - keep current name
    return
  }

  const wc = activeWorkCenters.value.find(w => w.id === wcId)
  if (wc) {
    const wcType = wc.work_center_type.toLowerCase().replace('cnc_', '').replace('_', '')
    const mapping = OPERATION_TYPE_MAP[wcType] ?? OPERATION_TYPE_MAP.generic
    const op = operations.value.find(o => o.id === opId)
    if (op && mapping) {
      formData.name = `OP${op.seq} - ${mapping.label}`
    }
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
  delete editForms[opId]

  showDeleteConfirm.value = false
  operationToDelete.value = null
}

// Format time helper
function formatTime(minutes: number): string {
  if (minutes === 0) return '0 min'
  if (minutes < 1) return `${(minutes * 60).toFixed(0)} s`
  return `${minutes.toFixed(1)} min`
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
        class="btn-primary"
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
      <div class="empty-icon">🔧</div>
      <p>Žádné operace</p>
      <p class="hint">Přidejte první operaci kliknutím na tlačítko výše</p>
    </div>

    <!-- Operations List -->
    <div v-else class="operations-list">
      <div
        v-for="op in sortedOperations"
        :key="op.id"
        class="operation-card"
        :class="{ 'is-coop': op.is_coop, 'is-expanded': expandedOps[op.id] }"
      >
        <!-- Collapsed header -->
        <div class="op-header" @click="toggleExpanded(op.id)">
          <div class="op-info">
            <span class="op-seq">{{ op.seq }}</span>
            <span class="op-icon">{{ op.icon }}</span>
            <span class="op-name">{{ op.name }}</span>
            <span v-if="op.is_coop" class="coop-badge">Kooperace</span>
          </div>
          <div class="op-times">
            <span class="time-badge" title="Přípravný čas">tp: {{ formatTime(op.setup_time_min) }}</span>
            <span class="time-badge" title="Kusový čas">tj: {{ formatTime(op.operation_time_min) }}</span>
          </div>
          <button class="expand-btn" type="button">
            {{ expandedOps[op.id] ? '▲' : '▼' }}
          </button>
        </div>

        <!-- Expanded edit form -->
        <div v-if="expandedOps[op.id] && editForms[op.id]" class="op-details">
          <form @submit.prevent="saveOperation(op)">
            <!-- Name + Work Center -->
            <div class="form-row">
              <div class="form-field">
                <label>Název</label>
                <input
                  v-model="form(op.id).name"
                  type="text"
                  maxlength="100"
                  required
                />
              </div>
              <div class="form-field">
                <label>Pracoviště</label>
                <select
                  v-model="form(op.id).work_center_id"
                  @change="onWorkCenterChange(op.id)"
                >
                  <option :value="null">-- Bez pracoviště --</option>
                  <option v-for="wc in activeWorkCenters" :key="wc.id" :value="wc.id">
                    {{ wc.work_center_number }} - {{ wc.name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Times with lock buttons -->
            <div class="form-row">
              <div class="form-field">
                <label>
                  Přípravný čas (tp) [min]
                  <button
                    type="button"
                    class="lock-btn"
                    :class="{ 'is-locked': form(op.id).setup_time_locked }"
                    @click="form(op.id).setup_time_locked = !form(op.id).setup_time_locked"
                    title="Zamknout hodnotu"
                  >
                    {{ form(op.id).setup_time_locked ? '🔒' : '🔓' }}
                  </button>
                </label>
                <input
                  v-model.number="form(op.id).setup_time_min"
                  type="number"
                  step="0.1"
                  min="0"
                  :disabled="form(op.id).setup_time_locked"
                />
              </div>
              <div class="form-field">
                <label>
                  Kusový čas (tj) [min]
                  <button
                    type="button"
                    class="lock-btn"
                    :class="{ 'is-locked': form(op.id).operation_time_locked }"
                    @click="form(op.id).operation_time_locked = !form(op.id).operation_time_locked"
                    title="Zamknout hodnotu"
                  >
                    {{ form(op.id).operation_time_locked ? '🔒' : '🔓' }}
                  </button>
                </label>
                <input
                  v-model.number="form(op.id).operation_time_min"
                  type="number"
                  step="0.01"
                  min="0"
                  :disabled="form(op.id).operation_time_locked"
                />
              </div>
              <div class="form-field">
                <label>Režim</label>
                <select v-model="form(op.id).cutting_mode">
                  <option value="low">Dokončovací</option>
                  <option value="mid">Střední</option>
                  <option value="high">Hrubovací</option>
                </select>
              </div>
            </div>

            <!-- Coop checkbox -->
            <div class="form-row">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form(op.id).is_coop" />
                Kooperace (externí dodavatel)
              </label>
            </div>

            <!-- Coop fields (conditional) -->
            <div v-if="form(op.id).is_coop" class="form-row coop-fields">
              <div class="form-field">
                <label>Cena kooperace [Kč]</label>
                <input
                  v-model.number="form(op.id).coop_price"
                  type="number"
                  min="0"
                  step="1"
                />
              </div>
              <div class="form-field">
                <label>Min. cena [Kč]</label>
                <input
                  v-model.number="form(op.id).coop_min_price"
                  type="number"
                  min="0"
                  step="1"
                />
              </div>
              <div class="form-field">
                <label>Dodací dny</label>
                <input
                  v-model.number="form(op.id).coop_days"
                  type="number"
                  min="0"
                />
              </div>
            </div>

            <!-- Actions -->
            <div class="form-actions">
              <button
                type="button"
                class="btn-danger"
                @click="confirmDelete(op)"
              >
                🗑️ Smazat
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="saving"
              >
                {{ saving ? 'Ukládám...' : '💾 Uložit' }}
              </button>
            </div>
          </form>
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
  gap: var(--space-4);
  height: 100%;
  padding: var(--space-4);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

/* === LOADING === */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
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
  padding: var(--space-8);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-icon {
  font-size: 2rem;
}

.empty p {
  margin: 0;
  font-size: var(--text-base);
}

.empty .hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* === OPERATIONS LIST === */
.operations-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
  flex: 1;
}

.operation-card {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  transition: var(--transition-fast);
}

.operation-card.is-coop {
  border-left: 3px solid var(--color-warning);
}

.operation-card.is-expanded {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.op-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  cursor: pointer;
  transition: var(--transition-fast);
}

.op-header:hover {
  background: var(--state-hover);
}

.op-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.op-seq {
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  min-width: 30px;
}

.op-icon {
  font-size: var(--text-base);
}

.op-name {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.coop-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.op-times {
  display: flex;
  gap: var(--space-2);
}

.time-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-muted);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.expand-btn {
  padding: var(--space-1) var(--space-2);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: var(--transition-fast);
}

.expand-btn:hover {
  color: var(--text-primary);
}

/* === EXPANDED FORM === */
.op-details {
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  background: var(--bg-muted);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-base);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.lock-btn {
  padding: var(--space-1);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-xs);
  transition: var(--transition-fast);
}

.lock-btn:hover {
  background: var(--state-hover);
}

.lock-btn.is-locked {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.form-field input,
.form-field select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-base);
  transition: var(--transition-fast);
}

.form-field input:focus,
.form-field select:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.form-field input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-muted);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-base);
  cursor: pointer;
}

.coop-fields {
  background: var(--bg-warning-subtle, #fef3c7);
  padding: var(--space-3);
  border-radius: var(--radius-md);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}

/* === BUTTONS === */
.btn-primary,
.btn-secondary,
.btn-danger {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: var(--color-danger-subtle, #fee2e2);
  color: var(--color-danger, #dc2626);
}

.btn-danger:hover {
  background: var(--color-danger-subtle-hover, #fecaca);
}

</style>
