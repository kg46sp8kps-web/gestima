<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import type { LeafNode, DropZone, ModuleId } from '@/types/workspace'
import TilePanelHeader from './TilePanelHeader.vue'
import TileDropZones from './TileDropZones.vue'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  node: LeafNode
  instant?: boolean
}

const props = defineProps<Props>()
const ws = useWorkspaceStore()
const maximized = ref(false)
const showModulePicker = ref(false)

const isFocused = computed(() => ws.focusedLeafId === props.node.id)
const isDragging = computed(() => ws.dragState?.leafId === props.node.id)
// Drop zones are active on all target panels immediately when any drag is in progress
const dropZonesActive = computed(() =>
  !!ws.dragState && ws.dragState.leafId !== props.node.id,
)

// Map module IDs to async components
const MODULE_COMPONENTS: Partial<Record<ModuleId, ReturnType<typeof defineAsyncComponent>>> = {
  'parts-list': defineAsyncComponent(() => import('@/components/tiling/modules/TilePartsList.vue')),
  'work-detail': defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkDetail.vue')),
  'work-ops': defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkOps.vue')),
}

const ModuleComponent = computed(() => MODULE_COMPONENTS[props.node.module] ?? null)

function onDrop(zone: DropZone) {
  if (!ws.dragState) return
  const { leafId, moduleId } = ws.dragState
  ws.endDrag()
  if (leafId === null) {
    // Tab spawn — create new panel from dragged tab
    ws.splitLeaf(props.node.id, moduleId, zone, props.node.ctx)
  } else if (leafId !== props.node.id) {
    ws.moveLeaf(leafId, props.node.id, zone)
  }
}

function onClose() {
  ws.closeLeaf(props.node.id)
}

function onFocus() {
  ws.focusLeaf(props.node.id)
}
</script>

<template>
  <div
    :class="[
      'pnl',
      node.ctx,
      { instant, focused: isFocused, dragging: isDragging, max: maximized }
    ]"
    @mousedown="onFocus"
  >
    <TilePanelHeader
      :node="node"
      :maximized="maximized"
      @maximize="maximized = !maximized"
      @close="onClose"
      @open-module-picker="showModulePicker = true"
    />

    <!-- Module content -->
    <div class="pb">
      <Suspense v-if="ModuleComponent">
        <component :is="ModuleComponent" :leaf-id="node.id" :ctx="node.ctx" />
        <template #fallback>
          <div class="panel-loading">
            <Spinner size="sm" />
          </div>
        </template>
      </Suspense>

      <!-- Placeholder for unimplemented modules -->
      <div v-else class="mod-placeholder">
        <div
          class="mi-dot-lg"
          :style="{ background: 'var(--t4)' }"
        />
        <div class="mod-label">{{ node.module }}</div>
        <div class="mod-hint">Modul se připravuje</div>
      </div>
    </div>

    <!-- Drop zones overlay — active on all non-source panels when drag is in progress -->
    <TileDropZones
      :active="dropZonesActive"
      :leaf-id="node.id"
      @drop="onDrop"
    />
  </div>
</template>

<style scoped>
.pnl {
  background: var(--surface);
  backdrop-filter: blur(12px) saturate(1.3);
  -webkit-backdrop-filter: blur(12px) saturate(1.3);
  border: 1px solid var(--b1);
  border-radius: var(--r);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  /* Fill .tree-leaf (flex column) */
  flex: 1;
  min-height: 0;
  min-width: 0;
  opacity: 0;
  transform: scale(0.98);
  animation: pnlIn 0.35s var(--ease) forwards;
  transition: border-color 0.15s, box-shadow 0.2s;
}

.pnl.instant {
  opacity: 1;
  transform: none;
  animation: none;
}

.pnl.focused {
  border-color: var(--b2);
  box-shadow: 0 0 0 1px var(--b1), 0 8px 32px rgba(0,0,0,0.4);
}

.pnl.dragging {
  opacity: 0.4;
  pointer-events: none;
}

.pnl.max {
  position: fixed !important;
  inset: 38px 3px 24px 3px;
  z-index: 50;
}

/* Context stripe — top edge color */
.pnl::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  z-index: 5;
  opacity: 0;
}
.pnl.ca::before {
  background: linear-gradient(90deg, transparent, var(--la) 30%, var(--la) 70%, transparent);
  opacity: 0.4;
}
.pnl.cb::before {
  background: linear-gradient(90deg, transparent, var(--lb) 30%, var(--lb) 70%, transparent);
  opacity: 0.3;
}

.pb {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
  user-select: none;
  padding: 24px;
  height: 100%;
}
.mi-dot-lg {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.mod-label {
  font-size: var(--fsl);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t4);
}
.mod-hint {
  font-size: 10px;
  color: var(--t4);
  opacity: 0.6;
}

@keyframes pnlIn {
  to { opacity: 1; transform: scale(1); }
}
</style>
