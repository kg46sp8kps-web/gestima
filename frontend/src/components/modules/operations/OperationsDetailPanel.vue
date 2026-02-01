<script setup lang="ts">
/**
 * Operations Detail Panel Component (Refactored)
 * COORDINATOR ONLY - delegates rendering to OperationRow.vue
 * BUILDING BLOCKS (L-039): <150 LOC coordinator
 */

import { ref, computed, watch, reactive } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import type { Operation, CuttingMode } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import OperationRow from './OperationRow.vue'
import DeleteOperationModal from './DeleteOperationModal.vue'
import { Settings } from 'lucide-vue-next'

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
const draggedOpId = ref<number | null>(null)
const dragOverOpId = ref<number | null>(null)

// Debounce timers per operation
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()

// Computed from store
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// Watch partId change
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
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1) {
    ;(operations.value[opIndex] as any)[field] = value
  }

  const existingTimer = debounceTimers.get(op.id)
  if (existingTimer) clearTimeout(existingTimer)

  const timer = setTimeout(async () => {
    debounceTimers.delete(op.id)
    await operationsStore.updateOperation(op.id, { [field]: value }, props.linkingGroup)
  }, 500)

  debounceTimers.set(op.id, timer)
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

// Drag & Drop handlers (HTML5 API)
function handleDragStart(event: DragEvent, op: Operation) {
  draggedOpId.value = op.id

  // Clone the entire operation card for realistic drag preview
  const wrapper = event.currentTarget as HTMLElement
  const opCard = wrapper.querySelector('.operation-card') as HTMLElement

  if (opCard) {
    const ghostElement = opCard.cloneNode(true) as HTMLElement
    ghostElement.style.cssText = `
      position: absolute;
      top: -9999px;
      left: -9999px;
      width: ${opCard.offsetWidth}px;
      opacity: 0.95;
      transform: rotate(2deg);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      pointer-events: none;
      z-index: 9999;
    `

    document.body.appendChild(ghostElement)

    // Calculate offset from mouse to element (keep grab position)
    const rect = opCard.getBoundingClientRect()
    const offsetX = event.clientX - rect.left
    const offsetY = event.clientY - rect.top

    // Set custom drag image at EXACT grab position
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setDragImage(ghostElement, offsetX, offsetY)
    }

    // Cleanup after browser copies the image
    setTimeout(() => {
      if (document.body.contains(ghostElement)) {
        document.body.removeChild(ghostElement)
      }
    }, 0)
  }
}

function handleDragEnd() {
  draggedOpId.value = null
  dragOverOpId.value = null
}

function handleDragOver(event: DragEvent, op: Operation) {
  event.preventDefault()

  if (!draggedOpId.value || draggedOpId.value === op.id) {
    dragOverOpId.value = null
    return
  }

  // Detect mouse position relative to element
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const mouseY = event.clientY
  const elementMiddle = rect.top + rect.height / 2

  // If mouse in TOP half → gap ABOVE this element
  // If mouse in BOTTOM half → gap ABOVE next element
  if (mouseY < elementMiddle) {
    dragOverOpId.value = op.id
  } else {
    const currentIndex = sortedOperations.value.findIndex(o => o.id === op.id)
    const nextOp = sortedOperations.value[currentIndex + 1]
    dragOverOpId.value = nextOp ? nextOp.id : null
  }
}

async function handleDrop(event: DragEvent) {
  event.preventDefault()

  console.log('🎯 DROP!', { draggedOpId: draggedOpId.value, dragOverOpId: dragOverOpId.value })

  if (!draggedOpId.value || !dragOverOpId.value) {
    console.log('❌ Missing IDs')
    draggedOpId.value = null
    dragOverOpId.value = null
    return
  }

  if (draggedOpId.value === dragOverOpId.value) {
    console.log('❌ Same operation')
    draggedOpId.value = null
    dragOverOpId.value = null
    return
  }

  const draggedOp = operations.value.find(op => op.id === draggedOpId.value)
  if (!draggedOp) {
    draggedOpId.value = null
    dragOverOpId.value = null
    return
  }

  // Get current sorted order
  const sorted = [...sortedOperations.value]
  const draggedIndex = sorted.findIndex(op => op.id === draggedOpId.value)
  const targetIndex = sorted.findIndex(op => op.id === dragOverOpId.value)

  if (draggedIndex === -1 || targetIndex === -1) {
    draggedOpId.value = null
    dragOverOpId.value = null
    return
  }

  // Calculate insert position BEFORE removing
  // Gap shows ABOVE dragOverOpId, so we insert BEFORE it
  let insertIndex = targetIndex

  // If dragged element is before target, adjust index
  // (after removal, everything shifts left)
  if (draggedIndex < targetIndex) {
    insertIndex--
  }

  // Remove from old position
  sorted.splice(draggedIndex, 1)

  // Insert at calculated position
  sorted.splice(insertIndex, 0, draggedOp)

  // Renumber all operations 10-20-30...
  sorted.forEach((op, index) => {
    op.seq = (index + 1) * 10
  })

  // Bulk update
  await Promise.all(
    sorted.map(op =>
      operationsStore.updateOperation(op.id, { seq: op.seq }, props.linkingGroup)
    )
  )

  draggedOpId.value = null
  dragOverOpId.value = null
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

    <!-- Operations List (drag & drop enabled) -->
    <div v-else class="operations-list">
      <template v-for="op in sortedOperations" :key="op.id">
        <!-- Drop placeholder GAP (shows BEFORE target operation) -->
        <div
          v-if="dragOverOpId === op.id && draggedOpId !== op.id"
          class="drop-placeholder"
        >
          <div class="placeholder-line"></div>
          <span class="placeholder-text">Sem vložit</span>
        </div>

        <!-- Operation wrapper -->
        <div
          draggable="true"
          @dragstart="handleDragStart($event, op)"
          @dragover="handleDragOver($event, op)"
          @dragend="handleDragEnd"
          @drop="handleDrop"
          :class="{
            'operation-wrapper': true,
            'is-dragging': draggedOpId === op.id
          }"
        >
          <OperationRow
            :operation="op"
            :work-centers="activeWorkCenters"
            :expanded="expandedOps[op.id] || false"
            :saving="saving"
            @toggle-expanded="toggleExpanded(op.id)"
            @update-field="(field, value) => debouncedUpdateOperation(op, field, value)"
            @update-work-center="(wcId) => onWorkCenterChange(op, wcId)"
            @change-mode="(mode) => changeMode(op, mode)"
            @toggle-coop="toggleCoop(op)"
            @delete="confirmDelete(op)"
          />
        </div>
      </template>
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
  gap: var(--space-3);  /* 12px - normální mezera */
  overflow-y: auto;
  flex: 1;
}

/* Drag & Drop styles */
.operation-wrapper {
  cursor: grab;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.operation-wrapper:active {
  cursor: grabbing;
}

.operation-wrapper.is-dragging {
  opacity: 0.3;
  transform: scale(0.95);
  cursor: grabbing;
}

/* Drop placeholder (gap visualization) */
.drop-placeholder {
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  margin: var(--space-3) 0;
  padding: var(--space-4) 0;
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    height: 0;
    margin: 0;
    padding: 0;
    opacity: 0;
    transform: scaleY(0);
  }
  to {
    height: 80px;
    margin: var(--space-3) 0;
    padding: var(--space-4) 0;
    opacity: 1;
    transform: scaleY(1);
  }
}

.placeholder-line {
  width: 100%;
  height: 3px;
  background: var(--color-primary);
  border-radius: var(--radius-sm);
  box-shadow: 0 0 8px var(--color-primary);
}

.placeholder-text {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-primary);
  background: var(--bg-surface);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-primary);
}
</style>
