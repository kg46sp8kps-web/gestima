<script setup lang="ts">
/**
 * Material Items List Module - Split-pane layout (UI-BIBLE Pattern 1)
 *
 * LEFT: Material items list (DataTable)
 * RIGHT: Material item detail (Info Ribbon)
 */

import { ref, computed, onMounted } from 'vue'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import MaterialItemsListPanel from './MaterialItemsListPanel.vue'
import MaterialItemDetailPanel from './MaterialItemDetailPanel.vue'
import type { MaterialItem } from '@/types/material'

interface Props {
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inline: false
})

// Layout settings
const { layoutMode } = usePartLayoutSettings('material-items')

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

// Selected item
const selectedItem = ref<MaterialItem | null>(null)
const listPanelRef = ref<InstanceType<typeof MaterialItemsListPanel> | null>(null)

// Load saved panel size
onMounted(() => {
  const stored = localStorage.getItem('materialItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }
})

// Handle item selection
function handleSelectItem(item: MaterialItem) {
  selectedItem.value = item
}

function handleItemCreated(item: MaterialItem) {
  selectedItem.value = item
}

function handleItemUpdated() {
  // Refresh list (handled by panel)
  if (selectedItem.value) {
    // Optionally reload detail
  }
}

function handleItemDeleted() {
  selectedItem.value = null
  listPanelRef.value?.setSelection(null)
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
    localStorage.setItem('materialItemsPanelSize', panelSize.value.toString())
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
    <!-- FIRST PANEL: Material Items List -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
      <MaterialItemsListPanel
        ref="listPanelRef"
        :selected-item="selectedItem"
        @select-item="handleSelectItem"
        @item-created="handleItemCreated"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Material Item Detail -->
    <div v-if="selectedItem" class="second-panel">
      <MaterialItemDetailPanel
        :item="selectedItem"
        @updated="handleItemUpdated"
        @deleted="handleItemDeleted"
      />
    </div>

    <!-- EMPTY STATE -->
    <div v-else class="empty">
      <p>Select a material item from the list to view details</p>
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
  background: var(--border-color);
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
  font-size: var(--text-base);
}
</style>
