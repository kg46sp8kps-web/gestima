<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'

type EdgeZone = 'left' | 'right' | 'top' | 'bottom'

const ws = useWorkspaceStore()

// Active for both leaf panel drags (leafId set) and tab spawns (leafId = null)
const active = computed(() => !!ws.dragState)
const hoveredZone = ref<EdgeZone | null>(null)

watch(active, (a) => { if (!a) hoveredZone.value = null })

function onDragOver(e: DragEvent, zone: EdgeZone) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  hoveredZone.value = zone
}

function onDragLeave(e: DragEvent) {
  const el = e.currentTarget as HTMLElement
  if (!el.contains(e.relatedTarget as Node)) {
    hoveredZone.value = null
  }
}

function onDrop(e: DragEvent, zone: EdgeZone) {
  e.preventDefault()
  e.stopPropagation()
  if (!ws.dragState) return
  const { leafId, moduleId } = ws.dragState
  ws.endDrag()
  if (leafId !== null) {
    // Moving an existing panel to a workspace edge
    ws.dockLeafToEdge(leafId, zone)
  } else {
    // Tab spawn — create a new panel at the workspace edge
    const ctx = ws.leaves[ws.leaves.length - 1]?.ctx ?? 'ca'
    ws.spawnToEdge(moduleId, zone, ctx)
  }
  hoveredZone.value = null
}

const ICONS: Record<EdgeZone, string> = { left: '←', right: '→', top: '↑', bottom: '↓' }
const ZONES: EdgeZone[] = ['left', 'right', 'top', 'bottom']
</script>

<template>
  <div :class="['gdz', { active }]">
    <div
      v-for="zone in ZONES"
      :key="zone"
      :class="['gdz-strip', zone, { hovered: hoveredZone === zone }]"
      @dragover="onDragOver($event, zone)"
      @dragleave="onDragLeave"
      @drop="onDrop($event, zone)"
    >
      <span class="gdz-icon">{{ ICONS[zone] }}</span>
    </div>
  </div>
</template>

<style scoped>
.gdz {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 35;
}

.gdz-strip {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s, background 0.1s, border-color 0.1s;
  background: rgba(229,57,53,0.04);
  border: 1px solid rgba(229,57,53,0.12);
}

.gdz.active .gdz-strip {
  opacity: 1;
  pointer-events: auto;
}

.gdz-strip.hovered {
  background: rgba(229,57,53,0.14);
  border-color: rgba(229,57,53,0.4);
}

/* Size + position of each strip */
.gdz-strip.left   { top: 0; left: 0; bottom: 0; width: 52px; border-radius: 0 var(--r) var(--r) 0; border-left: none; }
.gdz-strip.right  { top: 0; right: 0; bottom: 0; width: 52px; border-radius: var(--r) 0 0 var(--r); border-right: none; }
.gdz-strip.top    { left: 0; top: 0; right: 0; height: 52px; border-radius: 0 0 var(--r) var(--r); border-top: none; }
.gdz-strip.bottom { left: 0; bottom: 0; right: 0; height: 52px; border-radius: var(--r) var(--r) 0 0; border-bottom: none; }

/* Accent line on the inner edge (where the split would appear) */
.gdz-strip::after {
  content: '';
  position: absolute;
  background: var(--red);
  border-radius: 99px;
  opacity: 0;
  transition: opacity 0.1s;
}
.gdz-strip.hovered::after { opacity: 0.7; }

.gdz-strip.left::after   { right: 0; top: 10%; bottom: 10%; width: 2px; }
.gdz-strip.right::after  { left: 0;  top: 10%; bottom: 10%; width: 2px; }
.gdz-strip.top::after    { bottom: 0; left: 10%; right: 10%; height: 2px; }
.gdz-strip.bottom::after { top: 0;   left: 10%; right: 10%; height: 2px; }

.gdz-icon {
  font-size: 15px;
  color: var(--t3);
  transition: color 0.1s;
  pointer-events: none;
  user-select: none;
}
.gdz-strip.hovered .gdz-icon { color: var(--red); }
</style>
