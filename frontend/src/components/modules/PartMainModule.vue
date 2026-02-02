<script setup lang="ts">
/**
 * Part Main Module - Split-pane layout coordinator
 *
 * LEFT: PartListPanel (always visible, sorted, filterable)
 * RIGHT: Empty / PartDetailPanel / PartCreateForm
 */

import { ref, watch, onMounted, computed } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { useResizablePanel } from '@/composables/useResizablePanel'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import { getPart } from '@/api/parts'
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

// Layout settings
const { layoutMode } = usePartLayoutSettings('part-main')

// Panel size state
const panelSize = ref(320) // Can be width (horizontal) or height (vertical)
const isDragging = ref(false)

// Load panel size from localStorage
onMounted(() => {
  const stored = localStorage.getItem('partMainPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }
})

// Custom resize handler that works for both horizontal and vertical
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  // Disable text selection during drag
  document.body.style.userSelect = 'none'
  document.body.style.cursor = isVertical ? 'col-resize' : 'row-resize'

  function onMouseMove(e: MouseEvent) {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(1000, startSize + delta))
    panelSize.value = newSize
  }

  function onMouseUp() {
    isDragging.value = false

    // Re-enable text selection
    document.body.style.userSelect = ''
    document.body.style.cursor = ''

    // Save to localStorage
    localStorage.setItem('partMainPanelSize', panelSize.value.toString())

    // Cleanup listeners
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Dynamic layout classes
const layoutClasses = computed(() => ({
  'layout-vertical': layoutMode.value === 'vertical',
  'layout-horizontal': layoutMode.value === 'horizontal'
}))

// Dynamic resize cursor
const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)

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

  const title = `Materiál položky - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-material', title, props.linkingGroup || null)
}

function openOperationsWindow() {
  if (!selectedPart.value) return

  const title = `Operace položky - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-operations', title, props.linkingGroup || null)
}

function openPricingWindow() {
  if (!selectedPart.value) return

  const title = `Ceny položky - ${selectedPart.value.part_number}`
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

  // Reload only the selected part from API
  // Don't update store to avoid triggering list re-render and scroll reset
  const updatedPart = await getPart(selectedPart.value.part_number)
  selectedPart.value = updatedPart
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
  <div class="split-layout" :class="layoutClasses">
    <!-- FIRST PANEL: Parts List -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
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
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Detail / Create / Empty -->
    <div class="second-panel">
      <!-- Mode 1: EMPTY -->
      <div v-if="!selectedPart && !isCreating" class="empty">
        <p>Vyberte díl ze seznamu vlevo</p>
      </div>

      <!-- Mode 2: DETAIL -->
      <PartDetailPanel
        v-else-if="selectedPart && !isCreating"
        :part="selectedPart"
        :linkingGroup="linkingGroup"
        :orientation="layoutMode"
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

/* Layout modes */
.split-layout.layout-horizontal {
  flex-direction: column; /* Horizontal split = stacked (nad sebou) */
}

.split-layout.layout-vertical {
  flex-direction: row; /* Vertical split = side by side (vedle sebe) */
}

/* === FIRST PANEL (with container queries) === */
.first-panel {
  flex-shrink: 0;
  /* width/height set via :style binding */
  padding: var(--space-3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  container-type: inline-size; /* Enable container queries for child components */
  container-name: part-list-panel;
}

.layout-vertical .first-panel {
  height: 100%;
}

.layout-horizontal .first-panel {
  width: 100%;
}

/* === RESIZE HANDLE === */
.resize-handle {
  background: var(--border-default);
  flex-shrink: 0;
  transition: background var(--transition-fast);
  position: relative;
}

.layout-vertical .resize-handle {
  width: 4px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle {
  height: 4px;
  cursor: row-resize;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
}

/* Wider hit area for easier dragging */
.layout-vertical .resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -4px;
  bottom: -4px;
  cursor: row-resize;
}

/* === SECOND PANEL === */
.second-panel {
  flex: 1;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.layout-vertical .second-panel {
  height: 100%;
}

.layout-horizontal .second-panel {
  width: 100%;
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
