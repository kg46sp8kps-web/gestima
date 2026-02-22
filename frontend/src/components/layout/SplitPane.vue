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

import { ref, computed, type Ref } from 'vue'
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

  /**
   * Layout orientation (vertical = left/right, horizontal = top/bottom)
   */
  orientation?: 'vertical' | 'horizontal'
}

const props = withDefaults(defineProps<Props>(), {
  leftCollapsed: false,
  defaultSize: 320,
  minSize: 250,
  maxSize: 1000,
  orientation: 'vertical'
})

// Layout mode (vertical = side-by-side, horizontal = stacked)
// Use prop if provided, otherwise fallback to stored settings
const { layoutMode: storedLayoutMode } = usePartLayoutSettings(props.storageKey)
const layoutMode = computed(() => props.orientation || storedLayoutMode.value)

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
  transition: width all 100ms var(--ease), height all 100ms var(--ease);
  display: flex;
  flex-direction: column;

  /* 🎯 CONTAINER QUERIES - levý panel reaguje na vlastní šířku */
  container-type: inline-size;
  container-name: first-panel;
}

.layout-vertical .first-panel {
  height: 100%;
}

.layout-horizontal .first-panel {
  width: 100%;
}

/* === RESIZE HANDLE === */
.resize-handle {
  background: var(--b2);
  flex-shrink: 0;
  transition: background all 100ms var(--ease);
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
  background: var(--red);
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

  /* 🎯 CONTAINER QUERIES - pravý panel reaguje na vlastní šířku */
  container-type: inline-size;
  container-name: second-panel;
}

.layout-vertical .second-panel {
  height: 100%;
}

.layout-horizontal .second-panel {
  width: 100%;
}
</style>
