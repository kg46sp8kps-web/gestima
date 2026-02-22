<script setup lang="ts">
import type { DropZone } from '@/types/workspace'

interface Props {
  active: boolean
  leafId: string
}

defineProps<Props>()

const emit = defineEmits<{
  drop: [zone: DropZone]
}>()

const zones: { id: DropZone; style: Record<string, string>; icon: string }[] = [
  { id: 'top',    style: { top: '0', left: '20%', right: '20%', height: '30%' }, icon: '▲' },
  { id: 'bottom', style: { bottom: '0', left: '20%', right: '20%', height: '30%' }, icon: '▼' },
  { id: 'left',   style: { left: '0', top: '20%', bottom: '20%', width: '25%' }, icon: '◄' },
  { id: 'right',  style: { right: '0', top: '20%', bottom: '20%', width: '25%' }, icon: '►' },
  { id: 'center', style: { top: '30%', bottom: '30%', left: '25%', right: '25%' }, icon: '●' },
]

function onDragOver(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

function onDrop(e: DragEvent, zone: DropZone) {
  e.preventDefault()
  e.stopPropagation()
  emit('drop', zone)
}
</script>

<template>
  <div :class="['drop-zones', { active }]">
    <div
      v-for="z in zones"
      :key="z.id"
      :class="['drop-highlight', z.id]"
      :style="{ ...z.style, position: 'absolute', borderRadius: '4px' }"
      @dragover.prevent="onDragOver($event)"
      @drop="onDrop($event, z.id)"
    >
      <span class="dz-icon">{{ z.icon }}</span>
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
.drop-highlight {
  background: rgba(229,57,53,0.08);
  border: 1px solid rgba(229,57,53,0.25);
  transition: all 0.1s var(--ease);
  display: flex;
  align-items: center;
  justify-content: center;
}
.drop-highlight:hover {
  background: rgba(229,57,53,0.15);
  border-color: rgba(229,57,53,0.5);
}
.drop-highlight.center {
  border-style: dashed;
}
.dz-icon {
  font-size: 14px;
  color: var(--t3);
  opacity: 0.7;
  pointer-events: none;
}
</style>
