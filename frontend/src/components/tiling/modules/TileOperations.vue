<script setup lang="ts">
/**
 * TileOperations — operations table coordinator for tiling workspace
 * VueDraggable, debounced updates, add/delete, batch recalculation
 * Business logic ported from OperationsDetailPanel.vue — UI is v2 tiling style
 */

import { ref, computed, watch, reactive, onBeforeUnmount } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useMaterialsStore } from '@/stores/materials'
import { operationsApi } from '@/api/operations'
import { fetchEstimationById } from '@/api/time-vision'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import type { Operation, CuttingMode } from '@/types/operation'
import type { LinkingGroup } from '@/types/workspace'
import { OPERATION_TYPE_MAP } from '@/types/operation'
import { confirm } from '@/composables/useDialog'
import { Settings } from 'lucide-vue-next'
import draggable from 'vuedraggable'
import { ICON_SIZE } from '@/config/design'
import TileOperationRow from './TileOperationRow.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})

const emit = defineEmits<{
  'select-operation': [operation: Operation | null]
}>()

const operationsStore = useOperationsStore()
const materialsStore = useMaterialsStore()

// Keyboard shortcuts
const { registerShortcut } = useKeyboardShortcuts()

// Local state
const expandedOps = reactive<Record<number, boolean>>({})
const selectedOperationId = ref<number | null>(null)
const aiTimeModified = ref(false)

// Debounce timers per operation
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()

// Register Ctrl+N shortcut for new operation
registerShortcut({
  key: 'n',
  ctrl: true,
  handler: () => {
    if (props.partId && !loading.value) {
      handleAddOperation()
    }
  },
})

// Computed from store
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const sortedOperations = computed(() => operationsStore.getSortedOperations(props.linkingGroup))
const loading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const initialLoading = computed(() => operationsStore.getContext(props.linkingGroup).initialLoading)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const saving = computed(() => operationsStore.saving)

// AI estimation indicator
const hasAIEstimation = computed(() => operations.value.some(op => op.ai_estimation_id != null))

// Material inputs for linking
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)

// VueDraggable local array (v-model)
const localOperations = ref<Operation[]>([])
const isDragging = ref(false)

// Sync with store (SKIP when dragging to prevent race condition)
watch(sortedOperations, (newOps) => {
  if (!isDragging.value) {
    localOperations.value = [...newOps]
  }
}, { immediate: true })

// Watch partId change
watch(() => props.partId, async (newPartId) => {
  aiTimeModified.value = false
  if (newPartId) {
    await loadData(newPartId)
  }
}, { immediate: true })

async function loadData(partId: number) {
  await Promise.all([
    operationsStore.loadWorkCenters(),
    operationsStore.loadOperations(partId, props.linkingGroup),
  ])
}

// Toggle expanded state
function toggleExpanded(opId: number) {
  expandedOps[opId] = !expandedOps[opId]
}

// Debounced update operation
function debouncedUpdateOperation(op: Operation, field: keyof Operation, value: unknown) {
  const opIndex = operations.value.findIndex(o => o.id === op.id)
  if (opIndex !== -1) {
    ;(operations.value[opIndex] as never)[field] = value as never
  }

  const existingTimer = debounceTimers.get(op.id)
  if (existingTimer) clearTimeout(existingTimer)

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
    cancelText: 'Zrušit',
  })

  if (!confirmed) return

  await operationsStore.deleteOperation(op.id, props.linkingGroup)
  delete expandedOps[op.id]
}

// VueDraggable handlers
function handleDragStart() {
  isDragging.value = true
}

async function handleDragEnd() {
  isDragging.value = false

  localOperations.value.forEach((op, index) => {
    op.seq = (index + 1) * 10
  })

  await Promise.all(
    localOperations.value.map(op =>
      operationsStore.updateOperation(op.id, { seq: op.seq }, props.linkingGroup),
    ),
  )
}

// Link material to operation
async function handleLinkMaterial(operationId: number, materialId: number) {
  try {
    await operationsApi.linkMaterial(operationId, materialId)
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
    selectedOperationId.value = null
    emit('select-operation', null)
  } else {
    selectedOperationId.value = op.id
    emit('select-operation', op)
  }
}

// Flush pending debounce timers on unmount
onBeforeUnmount(() => {
  debounceTimers.forEach((timer) => clearTimeout(timer))
  debounceTimers.clear()
})

// Expose for parent (TilePanel)
defineExpose({
  operationsCount: computed(() => operations.value.length),
  hasAIEstimation: computed(() => hasAIEstimation.value),
  aiTimeModified: computed(() => aiTimeModified.value),
  resetAIWarning() { aiTimeModified.value = false },
  addOperation() { handleAddOperation() },
})
</script>

<template>
  <div class="tile-operations">
    <!-- Loading (only on first load) -->
    <div v-if="initialLoading" class="ops-loading">
      <div class="spinner" />
      <span>Načítám operace...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="operations.length === 0 && !loading" class="ops-empty">
      <Settings :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Žádné operace</p>
      <p class="ops-hint">Ctrl+N nebo tlačítko "Operace" v ribbonu</p>
    </div>

    <!-- Operations table (v2 styling) -->
    <div v-else class="ops-table-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th class="th-drag" />
            <th>Seq</th>
            <th>Pracoviště</th>
            <th>Operace</th>
            <th class="r">Seříz.</th>
            <th class="r">Čas/ks</th>
            <th class="r" />
          </tr>
        </thead>
        <draggable
          v-model="localOperations"
          item-key="id"
          handle=".drag-handle"
          :animation="200"
          tag="tbody"
          ghost-class="ghost"
          chosen-class="chosen"
          drag-class="drag"
          @start="handleDragStart"
          @end="handleDragEnd"
        >
          <template #item="{ element: op }">
            <TileOperationRow
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
/* ═══ CONTAINER ═══ */
.tile-operations {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ═══ LOADING ═══ */
.ops-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px;
  color: var(--t3);
  font-size: var(--fs);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--b2);
  border-top-color: var(--ok);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ═══ EMPTY ═══ */
.ops-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 24px;
  color: var(--t3);
  text-align: center;
}

.empty-icon {
  color: var(--t4);
}

.ops-empty p {
  margin: 0;
  font-size: var(--fs);
}

.ops-hint {
  color: var(--t4);
}

/* ═══ TABLE WRAPPER ═══ */
.ops-table-wrap {
  overflow-y: auto;
  flex: 1;
}

/* ═══ OPERATIONS TABLE (v2 style) ═══ */
.ot {
  width: 100%;
  border-collapse: collapse;
}

.ot thead {
  background: rgba(255, 255, 255, 0.025);
  position: sticky;
  top: 0;
  z-index: 2;
}

.ot th {
  padding: 4px var(--pad);
  font-size: var(--fsl);
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
  user-select: none;
}

.ot th.r {
  text-align: right;
}

.th-drag {
  width: 24px;
}

/* ═══ VUEDRAGGABLE STATES ═══ */
.ghost {
  opacity: 0.4;
}

.chosen {
  cursor: grabbing;
}

.drag {
  opacity: 1;
  cursor: grabbing;
}
</style>
