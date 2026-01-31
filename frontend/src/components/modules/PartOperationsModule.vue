<template>
  <div class="operations-module">
    <!-- Header -->
    <div class="module-header">
      <h3 v-if="!inline">⚙️ Operace</h3>
      <div class="header-actions">
        <span v-if="operations.length > 0" class="operations-count">
          {{ operations.length }} operací
        </span>
        <button
          class="btn btn-primary btn-sm"
          @click="handleAddOperation"
          :disabled="!partId || saving"
        >
          + Přidat operaci
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <span class="spinner"></span>
      Načítám operace...
    </div>

    <!-- Empty state -->
    <div v-else-if="operations.length === 0" class="empty-state">
      <div class="empty-icon">🔧</div>
      <p>Žádné operace</p>
      <p class="hint">Přidejte první operaci kliknutím na tlačítko výše</p>
    </div>

    <!-- Operations list -->
    <div v-else class="operations-list">
      <div
        v-for="op in sortedOperations"
        :key="op.id"
        class="operation-card"
        :class="{ 'is-coop': op.is_coop, 'is-expanded': expandedOps[op.id] }"
      >
        <!-- Operation header (always visible) -->
        <div class="op-header" @click="toggleExpanded(op.id)">
          <div class="op-info">
            <span class="op-seq">{{ op.seq }}</span>
            <span class="op-icon">{{ op.icon }}</span>
            <span class="op-name">{{ op.name }}</span>
            <span v-if="op.is_coop" class="coop-badge">Kooperace</span>
          </div>
          <div class="op-times">
            <span class="time-badge" title="Přípravný čas (tp)">
              tp: {{ formatTime(op.setup_time_min) }}
            </span>
            <span class="time-badge" title="Kusový čas (tj)">
              tj: {{ formatTime(op.operation_time_min) }}
            </span>
          </div>
          <button class="expand-btn" :title="expandedOps[op.id] ? 'Sbalit' : 'Rozbalit'">
            {{ expandedOps[op.id] ? '▲' : '▼' }}
          </button>
        </div>

        <!-- Operation details (expanded) -->
        <div v-if="expandedOps[op.id] && editForms[op.id]" class="op-details">
          <form @submit.prevent="saveOperation(op)" class="op-form">
            <!-- Row 1: Name + Work Center -->
            <div class="form-row">
              <div class="form-group">
                <label>Název</label>
                <input
                  v-model="form(op.id).name"
                  type="text"
                  class="form-input"
                  maxlength="100"
                />
              </div>
              <div class="form-group">
                <label>Pracoviště</label>
                <select
                  v-model="form(op.id).work_center_id"
                  class="form-select"
                  @change="onWorkCenterChange(op.id)"
                >
                  <option :value="null">-- Bez pracoviště --</option>
                  <option
                    v-for="wc in activeWorkCenters"
                    :key="wc.id"
                    :value="wc.id"
                  >
                    {{ wc.work_center_number }} - {{ wc.name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Row 2: Times -->
            <div class="form-row">
              <div class="form-group">
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
                  class="form-input"
                  min="0"
                  step="0.1"
                  :disabled="form(op.id).setup_time_locked"
                />
              </div>
              <div class="form-group">
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
                  class="form-input"
                  min="0"
                  step="0.01"
                  :disabled="form(op.id).operation_time_locked"
                />
              </div>
              <div class="form-group">
                <label>Režim</label>
                <select
                  v-model="form(op.id).cutting_mode"
                  class="form-select"
                >
                  <option value="low">Dokončovací</option>
                  <option value="mid">Střední</option>
                  <option value="high">Hrubovací</option>
                </select>
              </div>
            </div>

            <!-- Row 3: Coop checkbox -->
            <div class="form-row">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="form(op.id).is_coop"
                />
                Kooperace (externí dodavatel)
              </label>
            </div>

            <!-- Row 4: Coop details (conditional) -->
            <div v-if="form(op.id).is_coop" class="form-row coop-fields">
              <div class="form-group">
                <label>Cena kooperace [Kč]</label>
                <input
                  v-model.number="form(op.id).coop_price"
                  type="number"
                  class="form-input"
                  min="0"
                  step="1"
                />
              </div>
              <div class="form-group">
                <label>Min. cena [Kč]</label>
                <input
                  v-model.number="form(op.id).coop_min_price"
                  type="number"
                  class="form-input"
                  min="0"
                  step="1"
                />
              </div>
              <div class="form-group">
                <label>Dodací dny</label>
                <input
                  v-model.number="form(op.id).coop_days"
                  type="number"
                  class="form-input"
                  min="0"
                />
              </div>
            </div>

            <!-- Actions -->
            <div class="form-actions">
              <button
                type="button"
                class="btn btn-danger btn-sm"
                @click="confirmDelete(op)"
              >
                🗑️ Smazat
              </button>
              <button
                type="submit"
                class="btn btn-primary btn-sm"
                :disabled="saving"
              >
                {{ saving ? 'Ukládám...' : '💾 Uložit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="operations.length > 0" class="operations-summary">
      <div class="summary-item">
        <span class="summary-label">Celkem tp:</span>
        <span class="summary-value">{{ formatTime(totalSetupTime) }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Celkem tj:</span>
        <span class="summary-value">{{ formatTime(totalOperationTime) }}</span>
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-content">
          <h3>Smazat operaci?</h3>
          <p>Opravdu chcete smazat operaci <strong>{{ operationToDelete?.name }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showDeleteConfirm = false">Zrušit</button>
            <button class="btn btn-danger" @click="executeDelete">Smazat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, reactive } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useUiStore } from '@/stores/ui'
import { useWindowContextStore } from '@/stores/windowContext'
import type { Operation, CuttingMode } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import { OPERATION_TYPE_MAP } from '@/types/operation'

// Props
const props = withDefaults(defineProps<{
  inline?: boolean
  partId: number | null
  partNumber: string
  linkingGroup?: LinkingGroup
}>(), {
  linkingGroup: null
})

// Stores
const operationsStore = useOperationsStore()
const ui = useUiStore()
const contextStore = useWindowContextStore()

// Local state
const editForms = reactive<Record<number, EditForm>>({})
const showDeleteConfirm = ref(false)
const operationToDelete = ref<Operation | null>(null)

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

// Computed from store
// Computed from store (per-context)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const expandedOps = computed(() => operationsStore.getContext(props.linkingGroup).expandedOps)
const totalSetupTime = computed(() => operationsStore.getTotalSetupTime(props.linkingGroup))
const totalOperationTime = computed(() => operationsStore.getTotalOperationTime(props.linkingGroup))

// Computed from store (global)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// Helper to safely get form (used in template after v-if guard)
function form(opId: number): EditForm {
  return editForms[opId]!
}

// Computed: Get partId from window context (direct property access for fine-grained reactivity)
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  // Direct access to specific color's ref (NOT via function call)
  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

// Effective partId (context or props)
const effectivePartId = computed(() => contextPartId.value ?? props.partId)

// Watch for partId changes
watch(effectivePartId, async (newPartId) => {
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
  // Initialize edit forms
  initEditForms()
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

// Toggle expanded state
function toggleExpanded(opId: number) {
  operationsStore.expandedOps[opId] = !operationsStore.expandedOps[opId]
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
  const form = editForms[op.id]
  if (!form) return

  await operationsStore.updateOperation(op.id, {
    name: form.name,
    work_center_id: form.work_center_id,
    setup_time_min: form.setup_time_min,
    operation_time_min: form.operation_time_min,
    setup_time_locked: form.setup_time_locked,
    operation_time_locked: form.operation_time_locked,
    cutting_mode: form.cutting_mode,
    is_coop: form.is_coop,
    coop_price: form.coop_price,
    coop_min_price: form.coop_min_price,
    coop_days: form.coop_days
  }, props.linkingGroup)
}

// Handle work center change (update type/icon)
function onWorkCenterChange(opId: number) {
  const form = editForms[opId]
  if (!form) return

  const wcId = form.work_center_id
  if (!wcId) {
    // No work center - set to generic
    form.name = form.name.replace(/^OP\d+ - \w+/, `OP${operations.value.find(o => o.id === opId)?.seq || 10}`)
    return
  }

  const wc = activeWorkCenters.value.find(w => w.id === wcId)
  if (wc) {
    const mapping = OPERATION_TYPE_MAP[wc.type] ?? OPERATION_TYPE_MAP.generic
    const op = operations.value.find(o => o.id === opId)
    if (op && mapping) {
      form.name = `OP${op.seq} - ${mapping.label}`
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
</script>

<style scoped>
.operations-module {
  padding: var(--density-module-padding, 1rem);
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--density-section-gap, 0.75rem);
}

.module-header h3 {
  margin: 0;
  font-size: var(--density-font-md, 1rem);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.operations-count {
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.8rem);
}

/* Loading & Empty states */
.loading-state,
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

/* Operations list */
.operations-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.operation-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-surface);
  overflow: hidden;
}

.operation-card.is-coop {
  border-left: 3px solid #f59e0b;
}

.operation-card.is-expanded {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Operation header */
.op-header {
  display: flex;
  align-items: center;
  padding: var(--density-cell-py, 0.5rem) var(--density-cell-px, 0.75rem);
  cursor: pointer;
  transition: background 0.15s;
}

.op-header:hover {
  background: var(--bg-primary);
}

.op-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.op-seq {
  font-weight: 600;
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.8rem);
  min-width: 25px;
}

.op-icon {
  font-size: var(--density-font-md, 1rem);
}

.op-name {
  font-weight: 500;
}

.coop-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 4px;
  font-weight: 600;
}

.op-times {
  display: flex;
  gap: 0.5rem;
  margin-right: 1rem;
}

.time-badge {
  font-size: var(--density-font-sm, 0.7rem);
  padding: 2px 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  color: var(--text-secondary);
}

.expand-btn {
  background: none;
  border: none;
  font-size: 0.75rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
}

/* Operation details */
.op-details {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.op-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.form-group {
  flex: 1;
  min-width: 150px;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.form-input,
.form-select {
  width: 100%;
  padding: var(--density-input-py, 0.375rem) var(--density-input-px, 0.5rem);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: var(--density-font-base, 0.8rem);
  background: var(--bg-surface);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-red);
}

.form-input:disabled {
  background: var(--bg-primary);
  color: var(--text-muted);
}

.lock-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0;
}

.lock-btn.is-locked {
  opacity: 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  cursor: pointer;
}

.coop-fields {
  padding: 0.75rem;
  background: #fef3c7;
  border-radius: 6px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
}

/* Summary */
.operations-summary {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  margin-top: 1rem;
  background: var(--bg-primary);
  border-radius: 8px;
}

.summary-item {
  display: flex;
  gap: 0.5rem;
}

.summary-label {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.summary-value {
  font-weight: 600;
}

/* Buttons */
.btn {
  padding: var(--density-btn-py, 0.375rem) var(--density-btn-px, 0.75rem);
  border: none;
  border-radius: 4px;
  font-size: var(--density-font-base, 0.8rem);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-sm {
  padding: var(--density-btn-py, 0.25rem) var(--density-btn-px, 0.5rem);
  font-size: var(--density-font-sm, 0.75rem);
}

.btn-primary {
  background: var(--accent-red);
  color: white;
}

.btn-primary:hover {
  background: #b91c1c;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-danger {
  background: #fee2e2;
  color: #dc2626;
}

.btn-danger:hover {
  background: #fecaca;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  margin: 0 0 1rem 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.5rem;
}
</style>
