<script setup lang="ts">
/**
 * Material Items List Module - Split-pane layout (Design System Pattern 7.2)
 *
 * LEFT: Material items list (DataTable)
 * RIGHT: Material item detail (Info Ribbon)
 *
 * Refactored: uses useResizeHandle composable
 */

import { ref, computed } from 'vue'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import { useResizeHandle } from '@/composables/useResizeHandle'
import MaterialItemsListPanel from './MaterialItemsListPanel.vue'
import MaterialItemDetailPanel from './MaterialItemDetailPanel.vue'
import type { MaterialItem } from '@/types/material'

interface Props {
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inline: false
})

// Layout + resize
const { layoutMode } = usePartLayoutSettings('material-items')
const { size: panelSize, isDragging, startResize } = useResizeHandle({
  storageKey: 'materialItemsPanelSize',
  defaultSize: 320,
  minSize: 250,
  maxSize: 1000,
  vertical: true,
})

// Selected item
const selectedItem = ref<MaterialItem | null>(null)
const listPanelRef = ref<InstanceType<typeof MaterialItemsListPanel> | null>(null)

function handleSelectItem(item: MaterialItem) {
  selectedItem.value = item
}

function handleItemCreated(item: MaterialItem) {
  selectedItem.value = item
}

function handleItemUpdated() {
  // Refresh handled by panel
}

function handleItemDeleted() {
  selectedItem.value = null
  listPanelRef.value?.setSelection(null)
}

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
    <div v-else class="empty-state">
      <p>Select a material item from the list to view details</p>
    </div>
  </div>
</template>

<style scoped>
.split-layout { display: flex; gap: 0; height: 100%; overflow: hidden; }
.layout-horizontal { flex-direction: column; }
.layout-vertical { flex-direction: row; }
.first-panel, .second-panel { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.first-panel { flex-shrink: 0; }
.second-panel { flex: 1; padding: var(--space-5); overflow-y: auto; }
.resize-handle { flex-shrink: 0; background: var(--border-default); transition: background var(--duration-fast); position: relative; z-index: 10; }
.layout-vertical .resize-handle { width: 4px; }
.layout-horizontal .resize-handle { height: 4px; }
.resize-handle:hover, .resize-handle.dragging { background: var(--color-primary); }
</style>
