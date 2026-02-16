<script setup lang="ts">
/**
 * Operations Detail Panel Component (Refactored)
 * COORDINATOR ONLY - delegates rendering to OperationRow.vue
 * BUILDING BLOCKS (L-039): <150 LOC coordinator
 * DRAG & DROP: VueDraggable (professional solution)
 */

import { ref, computed, watch, reactive } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useMaterialsStore } from '@/stores/materials'
import { useWindowsStore } from '@/stores/windows'
import { operationsApi } from '@/api/operations'
import { fetchEstimationById } from '@/api/time-vision'
import type { Operation, CuttingMode } from '@/types/operation'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import OperationRow from './OperationRow.vue'
import { confirm } from '@/composables/useDialog'
import { Settings, Plus, Sparkles, AlertTriangle } from 'lucide-vue-next'
import draggable from 'vuedraggable'
import { ICON_SIZE } from '@/config/design'

interface Props {
  partId: number | null
  part: Part | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  part: null,
  linkingGroup: null
})

const emit = defineEmits<{
  'select-operation': [operation: Operation | null]
  'toggle-ai-panel': []
}>()

const operationsStore = useOperationsStore()
const materialsStore = useMaterialsStore()
const windowsStore = useWindowsStore()

// Local state
const expandedOps = reactive<Record<number, boolean>>({})
const selectedOperationId = ref<number | null>(null)
const aiTimeModified = ref(false)

// Debounce timers per operation
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()

// Computed from store
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// AI estimation indicator
const hasAIEstimation = computed(() => operations.value.some(op => op.ai_estimation_id != null))

// Material inputs for linking
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)

// VueDraggable local array (v-model)
const localOperations = ref<Operation[]>([])

// Sync with store
watch(sortedOperations, (newOps) => {
  localOperations.value = [...newOps]
}, { immediate: true })

// Watch partId change
watch(() => props.partId, async (newPartId) => {
  aiTimeModified.value = false
  if (newPartId) {
    await loadData(newPartId)
  }
}, { immediate: true })

// Load data
async function loadData(partId: number) {
  await Promise.all([
    operationsStore.loadWorkCenters(),
    operationsStore.loadOperations(partId, props.linkingGroup),
    materialsStore.loadMaterialInputs(partId, props.linkingGroup)
  ])
}

// Toggle expanded state
function toggleExpanded(opId: number) {
  expandedOps[opId] = !expandedOps[opId]
}

// Debounced update operation
function debouncedUpdateOperation(op: Operation, field: keyof Operation, value: any) {
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1) {
    ;(operations.value[opIndex] as any)[field] = value
  }

  const existingTimer = debounceTimers.get(op.id)
  if (existingTimer) clearTimeout(existingTimer)

  // Mark AI time as modified (warning turns red)
  if (field === 'operation_time_min' && op.ai_estimation_id) {
    aiTimeModified.value = true
  }

  const timer = setTimeout(async () => {
    debounceTimers.delete(op.id)
    await operationsStore.updateOperation(op.id, { [field]: value }, props.linkingGroup)
  }, 500)

  debounceTimers.set(op.id, timer)
}

// Restore AI-estimated time from TimeVision
async function restoreAITime(op: Operation) {
  if (!op.ai_estimation_id) return
  try {
    const est = await fetchEstimationById(op.ai_estimation_id)
    if (est?.estimated_time_min != null) {
      await operationsStore.updateOperation(
        op.id,
        { operation_time_min: est.estimated_time_min },
        props.linkingGroup,
      )
      aiTimeModified.value = false
    }
  } catch {
    // Silent fail
  }
}

// Handle work center change
async function onWorkCenterChange(op: Operation, newWorkCenterId: number | null) {
  const updates: Partial<Operation> = { work_center_id: newWorkCenterId }

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

  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1 && operations.value[opIndex]) {
    Object.assign(operations.value[opIndex]!, updates)
  }

  await operationsStore.updateOperation(op.id, updates, props.linkingGroup)
}

// Change cutting mode
async function changeMode(op: Operation, mode: CuttingMode) {
  await operationsStore.changeMode(op.id, mode, props.linkingGroup)
}

// Toggle coop mode
async function toggleCoop(op: Operation) {
  const newValue = !op.is_coop
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1 && operations.value[opIndex]) {
    operations.value[opIndex]!.is_coop = newValue
  }
  await operationsStore.updateOperation(op.id, { is_coop: newValue }, props.linkingGroup)
}

// Add new operation
async function handleAddOperation() {
  if (!props.partId) return
  const newOp = await operationsStore.addOperation(props.partId, props.linkingGroup)
  // NEW: collapsed by default (fix #2)
  if (newOp) {
    expandedOps[newOp.id] = false
  }
}

// Delete confirmation
async function confirmDelete(op: Operation) {
  const confirmed = await confirm({
    title: 'Smazat operaci?',
    message: `Opravdu chcete smazat operaci "${op.name}"?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  await operationsStore.deleteOperation(op.id, props.linkingGroup)
  delete expandedOps[op.id]
}

// VueDraggable handler - called after drag ends
async function handleDragEnd() {
  // Renumber operations 10-20-30...
  localOperations.value.forEach((op, index) => {
    op.seq = (index + 1) * 10
  })

  // Bulk update to backend
  await Promise.all(
    localOperations.value.map(op =>
      operationsStore.updateOperation(op.id, { seq: op.seq }, props.linkingGroup)
    )
  )
}

// Link material to operation
async function handleLinkMaterial(operationId: number, materialId: number) {
  try {
    await operationsApi.linkMaterial(operationId, materialId)

    // Reload materials to reflect the new link
    if (props.partId) {
      await materialsStore.loadMaterialInputs(props.partId, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to link material to operation:', error)
  }
}

// Unlink material from operation
async function handleUnlinkMaterial(operationId: number, materialId: number) {
  try {
    await operationsApi.unlinkMaterial(operationId, materialId)

    // Reload materials to reflect the unlink
    if (props.partId) {
      await materialsStore.loadMaterialInputs(props.partId, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to unlink material from operation:', error)
  }
}

// Select operation (toggle on click)
function selectOperation(op: Operation) {
  if (selectedOperationId.value === op.id) {
    // Deselect on second click
    selectedOperationId.value = null
    emit('select-operation', null)
  } else {
    selectedOperationId.value = op.id
    emit('select-operation', op)
  }
}

// Expose for parent
defineExpose({
  operationsCount: computed(() => operations.value.length),
  resetAIWarning() { aiTimeModified.value = false },
})
</script>

<template>
  <div class="operations-detail-panel">
    <!-- Header with Add + AI buttons -->
    <div class="panel-header">
      <h3>Operace</h3>
      <span
        v-if="hasAIEstimation"
        class="ai-info"
        :class="{ 'is-modified': aiTimeModified }"
        :title="aiTimeModified ? 'AI čas byl upraven' : 'Operace obsahuje AI odhad'"
      >
        <AlertTriangle :size="ICON_SIZE.SMALL" />
        Existuje AI čas
      </span>
      <div class="header-actions">
        <button
          class="icon-btn"
          @click="emit('toggle-ai-panel')"
          :disabled="!partId"
          title="AI odhad času z výkresu"
        >
          <Sparkles :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          class="icon-btn"
          @click="handleAddOperation"
          :disabled="!partId || loading"
          title="Přidat operaci"
        >
          <Plus :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Načítám operace...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="operations.length === 0" class="empty">
      <Settings :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Žádné operace</p>
      <p class="hint">Klikni na "+ Přidat operaci" pro začátek</p>
    </div>

    <!-- Operations Table (VueDraggable) -->
    <div v-else class="operations-table-wrapper">
      <table class="operations-table">
        <thead>
          <tr>
            <th class="col-seq">Seq</th>
            <th class="col-workcenter">Pracoviště</th>
            <th class="col-time">tp</th>
            <th class="col-time">tj</th>
            <th class="col-coef">Ko</th>
            <th class="col-coef">Ke</th>
            <th class="col-sum">Tp</th>
            <th class="col-sum">Tj</th>
            <th class="col-sum">To</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <draggable
          v-model="localOperations"
          @end="handleDragEnd"
          item-key="id"
          :animation="300"
          tag="tbody"
          ghost-class="ghost"
          chosen-class="chosen"
          drag-class="drag"
        >
          <template #item="{ element: op }">
            <OperationRow
              :operation="op"
              :work-centers="activeWorkCenters"
              :available-materials="materialInputs"
              :expanded="expandedOps[op.id] || false"
              :saving="saving"
              :selected="selectedOperationId === op.id"
              @toggle-expanded="toggleExpanded(op.id)"
              @update-field="(field, value) => debouncedUpdateOperation(op, field, value)"
              @update-work-center="(wcId) => onWorkCenterChange(op, wcId)"
              @change-mode="(mode) => changeMode(op, mode)"
              @toggle-coop="toggleCoop(op)"
              @delete="confirmDelete(op)"
              @link-material="(matId) => handleLinkMaterial(op.id, matId)"
              @unlink-material="(matId) => handleUnlinkMaterial(op.id, matId)"
              @select="selectOperation(op)"
              @restore-ai-time="restoreAITime(op)"
            />
          </template>
        </draggable>
      </table>
    </div>

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

.header-actions {
  display: flex;
  gap: var(--space-2);
}

/* AI estimation info label */
.ai-info {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

.ai-info.is-modified {
  color: var(--color-danger);
  font-weight: var(--font-semibold);
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

/* === OPERATIONS TABLE === */
.operations-table-wrapper {
  overflow-y: auto;
  flex: 1;
}

.operations-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

/* Table Header */
.operations-table thead {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg-surface);
}

.operations-table th {
  padding: var(--space-2) var(--space-2);
  text-align: left;
  font-weight: var(--font-semibold);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
  user-select: none;
}

.col-seq { width: 50px; }
.col-workcenter { min-width: 180px; }
.col-time { width: 80px; }
.col-coef { width: 70px; }
.col-sum { width: 70px; font-family: var(--font-mono); }
.col-actions { width: 80px; text-align: right; }

/* Table Body - VueDraggable */
.operations-table tbody {
  cursor: grab;
}

.operations-table tbody:active {
  cursor: grabbing;
}

/* VueDraggable states */
.ghost {
  opacity: 0.4;
}

.chosen {
  cursor: grabbing !important;
}

.drag {
  opacity: 1 !important;
  cursor: grabbing !important;
}
</style>
