<script setup lang="ts">
/**
 * SplitPane.vue - Reusable split-pane layout component
 *
 * Replaces duplicated split-pane logic across 7+ modules.
 * Supports vertical (side-by-side) and horizontal (stacked) layouts.
 *
 * Features:
 * - Drag-to-resize with mouse
 * - localStorage persistence
 * - Min/max size constraints
 * - Collapsible left/top panel
 * - Vertical/horizontal layout modes
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 * @example
 * ```vue
 * <SplitPane storage-key="my-split">
 *   <template #left>
 *     <MyListPanel />
 *   </template>
 *   <template #right>
 *     <MyDetailPanel />
 *   </template>
 * </SplitPane>
 * ```
 */

import { ref, computed } from 'vue'
import { useResizeHandle } from '@/composables/useResizeHandle'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'

interface Props {
  /**
   * Is left/top panel collapsed?
   */
  leftCollapsed?: boolean

  /**
   * localStorage key for panel size
   */
  storageKey: string

  /**
   * Default panel size in pixels
   */
  defaultSize?: number

  /**
   * Minimum panel size in pixels
   */
  minSize?: number

  /**
   * Maximum panel size in pixels
   */
  maxSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  leftCollapsed: false,
  defaultSize: 320,
  minSize: 250,
  maxSize: 1000
})

// Layout mode (vertical = side-by-side, horizontal = stacked)
const { layoutMode } = usePartLayoutSettings(props.storageKey)

// Resize handle
const { size: panelSize, isDragging, startResize } = useResizeHandle(
  computed(() => ({
    storageKey: `${props.storageKey}-size`,
    defaultSize: props.defaultSize,
    minSize: props.minSize,
    maxSize: props.maxSize,
    vertical: layoutMode.value === 'vertical'
  }))
)

const layoutClasses = computed(() => ({
  'layout-vertical': layoutMode.value === 'vertical',
  'layout-horizontal': layoutMode.value === 'horizontal',
  'left-collapsed': props.leftCollapsed
}))

const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)

const leftPanelStyle = computed(() => {
  if (props.leftCollapsed) {
    return { width: '0px', minWidth: '0px', display: 'none' }
  }

  return layoutMode.value === 'vertical'
    ? { width: `${panelSize.value}px` }
    : { height: `${panelSize.value}px` }
})
</script>

<template>
  <div class="split-pane" :class="layoutClasses">
    <!-- LEFT/TOP PANEL -->
    <div v-if="!leftCollapsed" class="first-panel" :style="leftPanelStyle">
      <slot name="left" />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      v-if="!leftCollapsed"
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    />

    <!-- RIGHT/BOTTOM PANEL -->
    <div class="second-panel">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-pane {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.split-pane.layout-horizontal {
  flex-direction: column;
}

.split-pane.layout-vertical {
  flex-direction: row;
}

/* === FIRST PANEL === */
.first-panel {
  flex-shrink: 0;
  overflow: hidden;
  transition: width var(--transition-fast), height var(--transition-fast);
  display: flex;
  flex-direction: column;
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

/* Wider hit area for easier dragging (24px gap) */
.layout-vertical .resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -10px;
  right: -10px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -10px;
  bottom: -10px;
  cursor: row-resize;
}

/* === SECOND PANEL === */
.second-panel {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.layout-vertical .second-panel {
  height: 100%;
}

.layout-horizontal .second-panel {
  width: 100%;
}
</style>
