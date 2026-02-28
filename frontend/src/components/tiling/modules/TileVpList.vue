<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'
import { useSplitLayoutStore } from '@/stores/splitLayout'
import { useSplitResize } from '@/composables/useSplitResize'
import type { ContextGroup } from '@/types/workspace'
import VpListPanel from './vp/VpListPanel.vue'
import VpDetailPanel from './vp/VpDetailPanel.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const catalog = useCatalogStore()
const splitLayout = useSplitLayoutStore()

const layoutMode = computed(() => splitLayout.getMode(props.leafId, 'vp-list'))
const focusedVp = computed(() => {
  const item = catalog.getFocusedItem(props.ctx)
  return item?.type === 'vp' ? item : null
})

onUnmounted(() => splitLayout.cleanup(props.leafId))

// Resize
const containerRef = ref<HTMLElement | null>(null)
const { splitPct, isDragging, startResize } = useSplitResize(layoutMode, containerRef)
</script>

<template>
  <div ref="containerRef" class="vp-root" :class="layoutMode">
    <!-- List panel -->
    <div
      class="vp-list-wrap"
      :style="focusedVp
        ? layoutMode === 'vertical'
          ? { width: `${splitPct}%` }
          : { height: `${splitPct}%` }
        : {}"
    >
      <VpListPanel :leaf-id="leafId" :ctx="ctx" />
    </div>

    <!-- Resize handle -->
    <div
      v-if="focusedVp"
      :class="['resize-handle', layoutMode, { dragging: isDragging }]"
      @mousedown.prevent="startResize"
    />

    <!-- Detail panel -->
    <div v-if="focusedVp" class="vp-detail-wrap">
      <VpDetailPanel :leaf-id="leafId" :ctx="ctx" />
    </div>
  </div>
</template>

<style scoped>
.vp-root {
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.vp-root.vertical   { flex-direction: row; }
.vp-root.horizontal { flex-direction: column; }

.vp-list-wrap {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  flex: 1;
}
.vp-list-wrap[style] { flex: none; }

.vp-detail-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.vp-root.vertical   .vp-detail-wrap { border-left: 1px solid var(--b1); }
.vp-root.horizontal .vp-detail-wrap { border-top: 1px solid var(--b1); }

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
