<script setup lang="ts">
/**
 * Manufacturing Items Module - Split-pane layout
 *
 * LEFT: Parts list
 * RIGHT: Part detail
 */

import { ref, computed, onMounted, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import PartListPanel from '@/components/modules/parts/PartListPanel.vue'
import PartDetailPanel from '@/components/modules/parts/PartDetailPanel.vue'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { useLinkedWindowOpener } from '@/composables/useLinkedWindowOpener'

interface Props {
  windowId?: string
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()

// Stores
const partsStore = usePartsStore()
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// Layout settings
const { layoutMode } = usePartLayoutSettings('manufacturing-items')

// Linked window opener — ensures child windows always share a linking group
const { openLinked } = useLinkedWindowOpener({
  get windowId() { return props.windowId },
  get linkingGroup() { return props.linkingGroup ?? null },
  onGroupAssigned(group) {
    // Re-publish current part context so the newly opened child syncs immediately
    if (selectedPart.value?.id && selectedPart.value.id > 0) {
      contextStore.setContext(group, selectedPart.value.id, selectedPart.value.part_number, selectedPart.value.article_number)
    }
  }
})

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

// Selected part
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Je právě otevřený nový (virtual) díl?
const isCreating = computed(() => selectedPart.value?.id === -1)

// Load panel size on mount (PartListPanel handles fetchParts itself)
onMounted(() => {
  const stored = localStorage.getItem('manufacturingItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }
})

// Auto-select part when parts are loaded (reacts to PartListPanel's fetch)
watch(() => partsStore.parts.length, (len) => {
  if (len > 0 && props.partNumber && !selectedPart.value) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      selectedPart.value = part
      listPanelRef.value?.setSelection(part.id)
    }
  }
}, { immediate: true })

// Handle part selection
function handleSelectPart(part: Part) {
  // Ignore clicks while creating — prevent accidental part switch
  if (isCreating.value) return

  selectedPart.value = part

  // Update window context for linking
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }

  emit('select-part', part.part_number)
}

function handleCreateNew() {
  // Virtual part (id=-1) — PartDetailPanel detects isNew() a otevře edit mód
  const virtualPart: Part = {
    id: -1,
    part_number: 'NOVÝ',
    article_number: '',
    name: '',
    drawing_path: null,
    drawing_number: null,
    customer_revision: null,
    revision: 'A',
    status: 'draft',
    source: 'manual',
    file_id: null,
    length: 0,
    notes: '',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    version: 0,
    created_by_name: null
  }
  selectedPart.value = virtualPart
  listPanelRef.value?.setSelection(-1)
}

// Window actions - open linked modules
function openPricingWindow() {
  if (!selectedPart.value) return
  openLinked('part-pricing', `Ceny - ${selectedPart.value.part_number}`)
}

function openTechnologyWindow() {
  if (!selectedPart.value) return
  openLinked('part-technology', `Technologie - ${selectedPart.value.part_number}`)
}

function openDrawingWindow(drawingId?: number) {
  if (!selectedPart.value) return
  const title = drawingId
    ? `Drawing #${drawingId} - ${selectedPart.value.part_number}`
    : `Drawing - ${selectedPart.value.part_number}`
  if (drawingId) {
    windowsStore.openWindow('part-drawing', title, null)
  } else {
    openLinked('part-drawing', title)
  }
}

// PartDetailPanel callbacks
async function handlePartCreated(createdPart: Part) {
  selectedPart.value = createdPart
  listPanelRef.value?.prependAndSelect(createdPart)
}

function handleCancelCreate() {
  selectedPart.value = null
  listPanelRef.value?.setSelection(null)
}

async function handlePartRefresh() {
  await partsStore.fetchParts()
  const updatedPart = partsStore.parts.find(p => p.id === selectedPart.value?.id)
  if (updatedPart) selectedPart.value = updatedPart
}

// Resize handler
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  const onMove = (e: MouseEvent) => {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(1000, startSize + delta))
    panelSize.value = newSize
  }

  const onUp = () => {
    isDragging.value = false
    localStorage.setItem('manufacturingItemsPanelSize', panelSize.value.toString())
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// Computed styles
const layoutClasses = computed(() => ({
  [`layout-${layoutMode.value}`]: true
}))

const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)
</script>

<template>
  <div class="split-layout" :class="layoutClasses">
    <!-- FIRST PANEL: Parts List -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        :readonly="isCreating"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
        @open-pricing="openPricingWindow"
        @open-drawing="openDrawingWindow()"
        @open-technology="openTechnologyWindow"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Part Detail — sdílená komponenta PartDetailPanel -->
    <div v-if="selectedPart" class="second-panel">
      <PartDetailPanel
        :part="selectedPart"
        :showActions="false"
        @created="handlePartCreated"
        @cancel-create="handleCancelCreate"
        @refresh="handlePartRefresh"
        @open-technology="openTechnologyWindow"
        @open-pricing="openPricingWindow"
        @open-drawing="openDrawingWindow"
      />
    </div>

    <!-- EMPTY STATE -->
    <div v-else class="empty">
      <p>Vyberte díl ze seznamu</p>
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

.layout-horizontal {
  flex-direction: column;
}

.layout-vertical {
  flex-direction: row;
}

/* === PANELS === */
.first-panel,
.second-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.first-panel {
  flex-shrink: 0;
}

.second-panel {
  flex: 1;
  padding: var(--space-5);
  overflow-y: auto;
  container-type: inline-size;
  container-name: second-panel;
}

/* === RESIZE HANDLE === */
.resize-handle {
  flex-shrink: 0;
  background: var(--border-default);
  transition: background var(--duration-fast);
  position: relative;
  z-index: 10;
}

.layout-vertical .resize-handle {
  width: 4px;
}

.layout-horizontal .resize-handle {
  height: 4px;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
}

/* second-panel nemá padding — PartDetailPanel si spravuje vlastní */
.second-panel {
  padding: 0;
}

/* Bez rámečku — v Manufacturing detail panel nemá border */
.second-panel :deep(.info-ribbon) {
  border: none;
  border-radius: 0;
  box-shadow: none;
}

/* === EMPTY STATE === */
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
}

.empty p {
  font-size: var(--text-sm);
}
</style>
