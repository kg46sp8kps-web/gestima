<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'
import { useSplitLayoutStore } from '@/stores/splitLayout'
import { useSplitResize } from '@/composables/useSplitResize'
import type { ContextGroup } from '@/types/workspace'
import TileItemList from './TileItemList.vue'
import TileItemDetail from './TileItemDetail.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const catalog = useCatalogStore()
const splitLayout = useSplitLayoutStore()

const layoutMode = computed(() => splitLayout.getMode(props.leafId, 'parts-list'))
const focusedItem = computed(() => catalog.getFocusedItem(props.ctx))

onUnmounted(() => splitLayout.cleanup(props.leafId))

// ── Resize ──
const containerRef = ref<HTMLElement | null>(null)
const { splitPct, isDragging, startResize } = useSplitResize(layoutMode, containerRef)
</script>

<template>
  <div ref="containerRef" class="wcat-root" :class="layoutMode">
    <!-- List panel -->
    <div
      class="wcat-list-wrap"
      :style="focusedItem
        ? layoutMode === 'vertical'
          ? { width: `${splitPct}%` }
          : { height: `${splitPct}%` }
        : {}"
    >
      <TileItemList :leaf-id="leafId" :ctx="ctx" />
    </div>

    <!-- Resize handle (only when detail is open) -->
    <div
      v-if="focusedItem"
      :class="['resize-handle', layoutMode, { dragging: isDragging }]"
      @mousedown.prevent="startResize"
    />

    <!-- Detail panel -->
    <div v-if="focusedItem" class="wcat-detail-wrap">
      <TileItemDetail :leaf-id="leafId" :ctx="ctx" />
    </div>
  </div>
</template>

<style scoped>
.wcat-root {
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.wcat-root.vertical   { flex-direction: row; }
.wcat-root.horizontal { flex-direction: column; }

.wcat-list-wrap {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  flex: 1;
}
.wcat-list-wrap[style] { flex: none; }

.wcat-detail-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.wcat-root.vertical   .wcat-detail-wrap { border-left: 1px solid var(--b1); }
.wcat-root.horizontal .wcat-detail-wrap { border-top: 1px solid var(--b1); }

.resize-handle {
  flex-shrink: 0;
  background: transparent;
  transition: background 120ms var(--ease);
}
.resize-handle.vertical   { width: 5px; cursor: col-resize; }
.resize-handle.horizontal { height: 5px; cursor: row-resize; }
.resize-handle:hover,
.resize-handle.dragging { background: var(--b2); }
</style>
