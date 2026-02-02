<script setup lang="ts">
/**
 * GridLayoutArea.vue - Wrapper for vue-grid-layout-v3
 *
 * Provides a clean API for grid layout with container queries.
 * Lazy-loads vue-grid-layout-v3 library.
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 */

import { defineAsyncComponent, computed } from 'vue'
import type { WidgetLayout } from '@/types/widget'

interface Props {
  /**
   * Widget layouts (position, size)
   */
  layouts: WidgetLayout[]

  /**
   * Number of grid columns
   */
  cols?: number

  /**
   * Row height in pixels
   */
  rowHeight?: number

  /**
   * Is draggable? (edit mode)
   */
  isDraggable?: boolean

  /**
   * Is resizable? (edit mode)
   */
  isResizable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  cols: 12,
  rowHeight: 60,
  isDraggable: true,
  isResizable: true
})

const emit = defineEmits<{
  'update:layouts': [layouts: WidgetLayout[]]
}>()

// Lazy-load vue-grid-layout-v3 (saves ~18KB until customization enabled)
const GridLayout = defineAsyncComponent(() =>
  import('vue-grid-layout-v3').then((m) => m.GridLayout)
)

const GridItem = defineAsyncComponent(() =>
  import('vue-grid-layout-v3').then((m) => m.GridItem)
)

function handleLayoutUpdated(newLayouts: WidgetLayout[]) {
  emit('update:layouts', newLayouts)
}
</script>

<template>
  <div class="grid-layout-area">
    <GridLayout
      :layout="layouts"
      :col-num="cols"
      :row-height="rowHeight"
      :is-draggable="isDraggable"
      :is-resizable="isResizable"
      :is-mirrored="false"
      :vertical-compact="true"
      :use-css-transforms="true"
      :responsive="false"
      :margin="[8, 8]"
      @layout-updated="handleLayoutUpdated"
    >
      <GridItem
        v-for="item in layouts"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
        :static="item.static"
      >
        <slot name="widget" :widget="item" />
      </GridItem>
    </GridLayout>
  </div>
</template>

<style scoped>
.grid-layout-area {
  /* Enable container queries for responsive columns */
  container-type: inline-size;
  container-name: grid-area;
  height: 100%;
  overflow: auto;
  padding: var(--space-3);
}

/* Container query breakpoints defined in _grid-layout.css */
</style>
