<script setup lang="ts">
import { ref, watch } from 'vue'
import type { DropZone } from '@/types/workspace'

interface Props {
  active: boolean
  leafId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  drop: [zone: DropZone]
}>()

const currentZone = ref<DropZone | null>(null)

// Reset zone when overlay becomes inactive
watch(() => props.active, (active) => {
  if (!active) currentZone.value = null
})

// Edge threshold matches v3 reference (22%)
function computeZone(e: DragEvent, el: HTMLElement): DropZone {
  const rect = el.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width
  const y = (e.clientY - rect.top) / rect.height
  const T = 0.22
  if (y < T) return 'top'
  if (y > 1 - T) return 'bottom'
  if (x < T) return 'left'
  if (x > 1 - T) return 'right'
  return 'center'
}

// Zone styles match v3 reference (45% for edges, 15% inset for center)
function zoneStyle(zone: DropZone): Record<string, string> {
  switch (zone) {
    case 'top':    return { top: '0', left: '0', right: '0', bottom: 'auto', width: 'auto', height: '45%' }
    case 'bottom': return { bottom: '0', left: '0', right: '0', top: 'auto', width: 'auto', height: '45%' }
    case 'left':   return { top: '0', left: '0', bottom: '0', right: 'auto', height: 'auto', width: '45%' }
    case 'right':  return { top: '0', right: '0', bottom: '0', left: 'auto', height: 'auto', width: '45%' }
    case 'center': return { top: '15%', bottom: '15%', left: '15%', right: '15%', height: 'auto', width: 'auto' }
  }
}

// Icons match v3 reference
const ICONS: Record<DropZone, string> = { top: '↑', bottom: '↓', left: '←', right: '→', center: '⊡' }

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  currentZone.value = computeZone(e, e.currentTarget as HTMLElement)
}

function onDragLeave(e: DragEvent) {
  const el = e.currentTarget as HTMLElement
  if (!el.contains(e.relatedTarget as Node)) {
    currentZone.value = null
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  // Use currentZone if set, fall back to computing from drop position
  const zone = currentZone.value ?? computeZone(e, e.currentTarget as HTMLElement)
  emit('drop', zone)
  currentZone.value = null
}
</script>

<template>
  <div
    :class="['drop-zones', { active }]"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- Permanent highlight element — shown/hidden via .visible class, repositioned via style.
         Matches v3 pattern: always in DOM, opacity 0→1 transition, no v-if mount/unmount. -->
    <div
      :class="['drop-highlight', currentZone ? 'visible' : '', currentZone ?? '']"
      :style="currentZone ? zoneStyle(currentZone) : undefined"
    >
      <span class="dz-icon">{{ currentZone ? ICONS[currentZone] : '' }}</span>
    </div>
  </div>
</template>

<style scoped>
.drop-zones {
  position: absolute;
  inset: 0;
  z-index: 40;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.1s;
}
.drop-zones.active {
  opacity: 1;
  pointer-events: auto;
}

/* Permanent highlight — invisible by default, shown with .visible */
.drop-highlight {
  position: absolute;
  border-radius: 4px;
  background: rgba(229,57,53,0.08);
  border: 1px solid rgba(229,57,53,0.25);
  transition: all 0.1s var(--ease);
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
}
.drop-highlight.visible { opacity: 1; }
.drop-highlight.center { border-style: dashed; }
.drop-highlight.center .dz-icon { font-size: 20px; }

/* Edge line indicators — matches v3 reference */
.drop-highlight.top::after,
.drop-highlight.bottom::after {
  content: '';
  position: absolute;
  left: 10%; right: 10%;
  height: 2px;
  background: var(--red);
  border-radius: 99px;
}
.drop-highlight.top::after { bottom: 0; }
.drop-highlight.bottom::after { top: 0; }

.drop-highlight.left::after,
.drop-highlight.right::after {
  content: '';
  position: absolute;
  top: 10%; bottom: 10%;
  width: 2px;
  background: var(--red);
  border-radius: 99px;
}
.drop-highlight.left::after { right: 0; }
.drop-highlight.right::after { left: 0; }

.dz-icon {
  font-size: 16px;
  color: var(--t2);
  opacity: 0.7;
  text-shadow: 0 1px 3px rgba(0,0,0,0.5);
  pointer-events: none;
}
</style>
