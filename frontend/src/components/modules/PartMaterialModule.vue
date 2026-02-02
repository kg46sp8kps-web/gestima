<script setup lang="ts">
/**
 * Part Material Module - Split-pane coordinator
 *
 * LEFT: PartListPanel (when standalone) OR Linked badge (when linked)
 * RIGHT: MaterialInputForm (top) + MaterialInputList (bottom) - Horizontal split
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import { useMaterialsStore } from '@/stores/materials'
import { useOperationsStore } from '@/stores/operations'
import { useResizablePanel } from '@/composables/useResizablePanel'
import { operationsApi } from '@/api/operations'
import { linkMaterialToOperation, unlinkMaterialFromOperation } from '@/api/materialInputs'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'
import type { MaterialInput, MaterialInputWithOperations } from '@/types/material'

import PartListPanel from './parts/PartListPanel.vue'
import MaterialInputForm from './material/MaterialInputForm.vue'
import MaterialInputList from './material/MaterialInputList.vue'

interface Props {
  inline?: boolean
  partId?: number | null
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  inline: false,
  partId: null,
  partNumber: '',
  linkingGroup: null
})

const partsStore = usePartsStore()
const contextStore = useWindowContextStore()
const materialsStore = useMaterialsStore()
const operationsStore = useOperationsStore()

// State
const selectedPart = ref<Part | null>(null)
const editingMaterial = ref<MaterialInputWithOperations | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Debounce timers per material (like operations)
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()

// Computed: Get partId from window context (direct property access for fine-grained reactivity)
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

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
const isLinked = computed(() => props.linkingGroup !== null)
const currentPartId = computed(() => selectedPart.value?.id || effectivePartId.value)

// Resizable panel (only when NOT linked)
const { panelWidth, isDragging, startResize } = useResizablePanel({
  storageKey: 'partMaterialsPanelWidth',
  defaultWidth: 320,
  minWidth: 250,
  maxWidth: 1000
})

// Computed: Get materials and operations from stores
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const loading = computed(() => materialsStore.getContext(props.linkingGroup).loadingInputs)

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }
}

function handleEdit(material: MaterialInputWithOperations) {
  editingMaterial.value = material
}

function handleSave(material: MaterialInput) {
  editingMaterial.value = null
  // Reload materials to reflect changes
  if (currentPartId.value) {
    materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
  }
}

function handleCancel() {
  editingMaterial.value = null
}

function handleUpdate(materialId: number, updates: Partial<MaterialInput>) {
  // Find the material
  const material = materialInputs.value.find(m => m.id === materialId)
  if (!material) {
    console.error('Material not found for update:', materialId)
    return
  }

  // 1. IMMEDIATE optimistic update (synchronous) - prevents re-render during typing
  const matIndex = materialInputs.value.findIndex(m => m.id === materialId)
  if (matIndex !== -1) {
    // Directly mutate store array to update UI instantly
    Object.assign(materialInputs.value[matIndex]!, updates)
  }

  // 2. Clear existing timer
  const existingTimer = debounceTimers.get(materialId)
  if (existingTimer) clearTimeout(existingTimer)

  // 3. Debounced backend call (500ms after last keystroke)
  const timer = setTimeout(async () => {
    debounceTimers.delete(materialId)

    try {
      // Create update payload with version for optimistic locking
      const updateData = {
        ...updates,
        version: material.version
      }

      // Backend call returns MaterialInputWithOperations (with calculated fields)
      await materialsStore.updateMaterialInput(materialId, updateData, props.linkingGroup)

      // Store automatically merges response (including weight_kg, cost_per_piece)
      // No manual re-render needed - Vue reactivity handles it
    } catch (error) {
      console.error('Failed to update material:', error)
      // Optionally: revert optimistic update on error
      if (currentPartId.value) {
        await materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
      }
    }
  }, 500)

  debounceTimers.set(materialId, timer)
}

async function handleLinkOperation(materialId: number, operationId: number) {
  try {
    // Use material-side API endpoint (either works, but for consistency use material-side)
    await linkMaterialToOperation(materialId, operationId)

    // Reload materials to reflect the new link
    if (currentPartId.value) {
      await materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to link operation to material:', error)
  }
}

async function handleUnlinkOperation(materialId: number, operationId: number) {
  try {
    // Use material-side API endpoint
    await unlinkMaterialFromOperation(materialId, operationId)

    // Reload materials to reflect the unlink
    if (currentPartId.value) {
      await materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to unlink operation from material:', error)
  }
}

async function handleDelete(materialId: number) {
  try {
    await materialsStore.deleteMaterialInput(materialId, props.linkingGroup)
    // Reload materials after deletion
    if (currentPartId.value) {
      await materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
    }
  } catch (error) {
    console.error('Failed to delete material:', error)
  }
}

// Load data on mount
onMounted(async () => {
  // Only fetch if parts not loaded yet (prevents list refresh/scroll reset)
  if (partsStore.parts.length === 0) {
    await partsStore.fetchParts()
  }

  // If partNumber prop provided, select it
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }

  // If partId prop provided (without partNumber), select by ID
  if (props.partId && !props.partNumber) {
    const part = partsStore.parts.find(p => p.id === props.partId)
    if (part) {
      selectedPart.value = part
    }
  }

  // Load materials and operations for current part
  if (currentPartId.value) {
    await materialsStore.loadMaterialInputs(currentPartId.value, props.linkingGroup)
    await operationsStore.loadOperations(currentPartId.value, props.linkingGroup)
  }
})

// Watch linked context changes (watch contextPartId computed for reactivity)
watch(contextPartId, async (newPartId) => {
  if (isLinked.value && newPartId) {
    const part = partsStore.parts.find(p => p.id === newPartId)
    if (part) {
      selectedPart.value = part
      // Load materials and operations for new part
      await materialsStore.loadMaterialInputs(newPartId, props.linkingGroup)
      await operationsStore.loadOperations(newPartId, props.linkingGroup)
    }
  }
}, { immediate: true })

// Watch prop changes
watch(() => props.partNumber, (newPartNumber) => {
  if (newPartNumber) {
    const part = partsStore.parts.find(p => p.part_number === newPartNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})

// Watch currentPartId to load data
watch(currentPartId, async (newPartId) => {
  if (newPartId) {
    await materialsStore.loadMaterialInputs(newPartId, props.linkingGroup)
    await operationsStore.loadOperations(newPartId, props.linkingGroup)
  }
})
</script>

<template>
  <div class="split-layout">
    <!-- LEFT PANEL: Only visible when standalone (not linked) -->
    <div v-if="!linkingGroup" class="left-panel" :style="{ width: `${panelWidth}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
      />
    </div>

    <!-- RESIZE HANDLE: Only visible when left panel is shown -->
    <div
      v-if="!linkingGroup"
      class="resize-handle"
      :class="{ dragging: isDragging }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Horizontal split (full width when linked) -->
    <div class="right-panel" :class="{ 'full-width': linkingGroup }">
      <!-- CONTEXT INFO RIBBON (when linked) -->
      <div v-if="linkingGroup && selectedPart" class="context-ribbon">
        <span class="context-label">Materiál</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.part_number }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.article_number || '-' }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.name || '-' }}</span>
      </div>

      <!-- TOP SECTION: Material Input Form -->
      <div class="material-form-section">
        <div v-if="!currentPartId" class="no-part-selected">
          <p>Vyberte díl pro přidání materiálu</p>
        </div>
        <MaterialInputForm
          v-else
          :materialInput="editingMaterial"
          :partId="currentPartId"
          :operations="operations"
          @save="handleSave"
          @cancel="handleCancel"
        />
      </div>

      <!-- DIVIDER -->
      <div class="divider"></div>

      <!-- BOTTOM SECTION: Material Input List -->
      <div class="material-list-section">
        <MaterialInputList
          :materials="materialInputs"
          :operations="operations"
          :editing-material-id="editingMaterial?.id || null"
          :loading="loading"
          @edit="handleEdit"
          @update="handleUpdate"
          @delete="handleDelete"
          @link-operation="handleLinkOperation"
          @unlink-operation="handleUnlinkOperation"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

/* === LEFT PANEL === */
.left-panel {
  flex-shrink: 0;
  /* width set via :style binding */
  padding: var(--space-3);
  height: 100%;
  overflow: hidden;
}

/* === RESIZE HANDLE === */
.resize-handle {
  width: 4px;
  background: var(--border-default);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background var(--transition-fast);
  position: relative;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
}

/* Wider hit area for easier dragging */
.resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
  cursor: col-resize;
}

/* === RIGHT PANEL: Horizontal Split === */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  container-type: inline-size;
  container-name: right-panel;
}

.right-panel.full-width {
  width: 100%;
}

/* === CONTEXT INFO RIBBON === */
.context-ribbon {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.context-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-divider {
  color: var(--border-default);
  font-weight: 300;
}

.context-value {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

/* === MATERIAL FORM SECTION (TOP) === */
.material-form-section {
  flex-shrink: 0;
  overflow-y: auto;
  padding: var(--space-4);
  padding-bottom: 0;
}

.no-part-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--text-secondary);
  font-size: var(--text-base);
  text-align: center;
}

.no-part-selected p {
  margin: 0;
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
}

/* === DIVIDER === */
.divider {
  height: 1px;
  background: var(--border-default);
  flex-shrink: 0;
}

/* === MATERIAL LIST SECTION (BOTTOM) === */
.material-list-section {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}
</style>
