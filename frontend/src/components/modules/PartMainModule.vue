<script setup lang="ts">
/**
 * Part Main Module - Split-pane layout coordinator
 *
 * LEFT: PartListPanel (always visible, sorted, filterable)
 * RIGHT: Empty / PartDetailPanel / PartCreateForm
 */

import { ref, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { useResizablePanel } from '@/composables/useResizablePanel'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'

import PartListPanel from './parts/PartListPanel.vue'
import PartDetailPanel from './parts/PartDetailPanel.vue'
import PartCreateForm from './parts/PartCreateForm.vue'

interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  partNumber: undefined,
  linkingGroup: null
})

const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()

const partsStore = usePartsStore()
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// State
const selectedPart = ref<Part | null>(null)
const isCreating = ref(false)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Resizable panel (PartMainModule always shows left panel - no linking)
const { panelWidth, isDragging, startResize } = useResizablePanel({
  storageKey: 'partMainPanelWidth',
  defaultWidth: 320,
  minWidth: 250,
  maxWidth: 1000
})

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part
  isCreating.value = false

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }

  emit('select-part', part.part_number)
}

function handleCreateNew() {
  isCreating.value = true
  selectedPart.value = null
  listPanelRef.value?.setSelection(null)
}

function handleCreated(part: Part) {
  isCreating.value = false
  selectedPart.value = part
  listPanelRef.value?.setSelection(part.id)

  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }

  emit('select-part', part.part_number)
}

function handleCancelCreate() {
  isCreating.value = false
}

// Window actions
function openMaterialWindow() {
  if (!selectedPart.value) return

  const title = `Material - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-material', title, props.linkingGroup || null)
}

function openOperationsWindow() {
  if (!selectedPart.value) return

  const title = `Operations - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-operations', title, props.linkingGroup || null)
}

function openPricingWindow() {
  if (!selectedPart.value) return

  const title = `Pricing - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-pricing', title, props.linkingGroup || null)
}

function openDrawingWindow(drawingId?: number) {
  if (!selectedPart.value) return

  // For specific drawing ID, open without linking group (standalone window)
  // For primary drawing, use linking group (context-aware)
  const title = drawingId
    ? `Drawing #${drawingId} - ${selectedPart.value.part_number}`
    : `Drawing - ${selectedPart.value.part_number}`

  // NOTE: drawingId is parsed from title in PartDrawingWindow
  // Pattern: "Drawing #123 - ..." where 123 is drawing_id
  windowsStore.openWindow('part-drawing', title, drawingId ? null : (props.linkingGroup || null))
}

async function refreshPart() {
  if (!selectedPart.value) return

  // Reload part data from API
  await partsStore.fetchParts()
  const updatedPart = partsStore.parts.find(p => p.id === selectedPart.value?.id)
  if (updatedPart) {
    selectedPart.value = updatedPart
  }
}

// Load parts on mount and auto-select if partNumber provided
onMounted(async () => {
  await partsStore.fetchParts()

  // If partNumber prop provided, select it
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})

// Watch prop changes (for external part selection)
watch(() => props.partNumber, (newPartNumber) => {
  if (newPartNumber) {
    const part = partsStore.parts.find(p => p.part_number === newPartNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})
</script>

<template>
  <div class="split-layout">
    <!-- LEFT PANEL: Parts List -->
    <div class="left-panel" :style="{ width: `${panelWidth}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Detail / Create / Empty -->
    <div class="right-panel">
      <!-- Mode 1: EMPTY -->
      <div v-if="!selectedPart && !isCreating" class="empty">
        <p>Vyberte díl ze seznamu vlevo</p>
      </div>

      <!-- Mode 2: DETAIL -->
      <PartDetailPanel
        v-else-if="selectedPart && !isCreating"
        :part="selectedPart"
        :linkingGroup="linkingGroup"
        @open-material="openMaterialWindow"
        @open-operations="openOperationsWindow"
        @open-pricing="openPricingWindow"
        @open-drawing="openDrawingWindow"
        @refresh="refreshPart"
      />

      <!-- Mode 3: CREATE -->
      <PartCreateForm
        v-else-if="isCreating"
        @created="handleCreated"
        @cancel="handleCancelCreate"
      />
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

/* === RIGHT PANEL === */
.right-panel {
  flex: 1;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* Empty State */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
  text-align: center;
  height: 100%;
}

.empty .empty-icon {
  font-size: var(--text-2xl);
  margin-bottom: var(--space-2);
}

.empty p {
  font-size: var(--text-base);
}
</style>
