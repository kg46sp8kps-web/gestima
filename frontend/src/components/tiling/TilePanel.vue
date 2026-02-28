<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { MODULE_REGISTRY } from '@/types/workspace'
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

// Evaluated once at setup — never reacts to prop changes.
// Seen panels (remounts after tree restructure) start at full opacity, no animation.
const isInstant = props.instant || ws.isLeafSeen(props.node.id)
onMounted(() => ws.markLeafSeen(props.node.id))
// Drop zones are active on all target panels immediately when any drag is in progress
const dropZonesActive = computed(() =>
  !!ws.dragState && ws.dragState.leafId !== props.node.id,
)

// Map module IDs to async components
const MODULE_COMPONENTS: Partial<Record<ModuleId, ReturnType<typeof defineAsyncComponent>>> = {
  'parts-list':     defineAsyncComponent(() => import('@/components/tiling/modules/TileCatalog.vue')),
  'work-ops':       defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkOps.vue')),
  'work-pricing':   defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkPricing.vue')),
  'work-drawing':   defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkDrawing.vue')),
  'work-docs':      defineAsyncComponent(() => import('@/components/tiling/modules/TileWorkDocs.vue')),
  'partners':       defineAsyncComponent(() => import('@/components/tiling/modules/TilePartners.vue')),
  'quotes':         defineAsyncComponent(() => import('@/components/tiling/modules/TileQuotes.vue')),
  'orders-overview': defineAsyncComponent(() => import('@/components/tiling/modules/TileOrdersOverview.vue')),
  'time-vision':    defineAsyncComponent(() => import('@/components/tiling/modules/TileTimeVision.vue')),
  'batch-sets':     defineAsyncComponent(() => import('@/components/tiling/modules/TileBatchSets.vue')),
  'production':     defineAsyncComponent(() => import('@/components/tiling/modules/TileProduction.vue')),
  'files':          defineAsyncComponent(() => import('@/components/tiling/modules/TileFiles.vue')),
  'admin':          defineAsyncComponent(() => import('@/components/tiling/modules/TileAdmin.vue')),
  'materials':      defineAsyncComponent(() => import('@/components/tiling/modules/TileMaterials.vue')),
  'machine-plan-dnd': defineAsyncComponent(() => import('@/components/tiling/modules/TileMachinePlanDnD.vue')),
  'production-planner': defineAsyncComponent(() => import('@/components/tiling/modules/TileProductionPlanner.vue')),
  'vp-list': defineAsyncComponent(() => import('@/components/tiling/modules/TileVpList.vue')),
  'vp-work-ops': defineAsyncComponent(() => import('@/components/tiling/modules/TileVpWorkOps.vue')),
}

const ModuleComponent = computed(() => MODULE_COMPONENTS[props.node.module] ?? null)

function onDrop(zone: DropZone) {
  if (!ws.dragState) return
  const { leafId, moduleId, sourceCtx } = ws.dragState
  ws.endDrag()
  if (leafId === null) {
    // Tab spawn — new panel inherits ctx of source panel, not target
    ws.splitLeaf(props.node.id, moduleId, zone, sourceCtx ?? props.node.ctx)
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
      MODULE_REGISTRY[node.module]?.usesCtx ? node.ctx : null,
      { instant: isInstant, focused: isFocused, dragging: isDragging, max: maximized }
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
        <div class="mi-dot-lg" />
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
  /* New panels animate in via scale — no opacity change so remount flash is invisible */
  animation: pnlIn 0.22s var(--ease) both;
  transition: border-color 0.15s, box-shadow 0.2s;
}

/* Seen panels (remounts): skip animation entirely */
.pnl.instant {
  animation: none;
}

@keyframes pnlIn {
  from { transform: scale(0.96); opacity: 0.6; }
  to   { transform: scale(1);    opacity: 1; }
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
  position: fixed;
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
.pnl.cc::before {
  background: linear-gradient(90deg, transparent, var(--link-group-blue) 30%, var(--link-group-blue) 70%, transparent);
  opacity: 0.35;
}
.pnl.cd::before {
  background: linear-gradient(90deg, transparent, var(--link-group-yellow) 30%, var(--link-group-yellow) 70%, transparent);
  opacity: 0.35;
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
  background: var(--t4);
}
.mod-label {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t4);
}
.mod-hint {
  font-size: var(--fsm);
  color: var(--t4);
  opacity: 0.6;
}

</style>
