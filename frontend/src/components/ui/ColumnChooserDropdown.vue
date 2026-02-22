<script setup lang="ts">
import { ref } from 'vue'
import { RotateCcw, GripVertical } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { Column } from './DataTable.vue'

interface Props {
  columns: Column[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'toggle-column': [key: string]
  'reset': []
  'reorder': [fromIndex: number, toIndex: number]
}>()

const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

function handleDragStart(event: DragEvent, index: number) {
  draggedIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleDragOver(event: DragEvent, index: number) {
  event.preventDefault()
  dragOverIndex.value = index
}

function handleDragLeave() {
  dragOverIndex.value = null
}

function handleDrop(event: DragEvent, dropIndex: number) {
  event.preventDefault()

  if (draggedIndex.value === null || draggedIndex.value === dropIndex) {
    draggedIndex.value = null
    dragOverIndex.value = null
    return
  }

  emit('reorder', draggedIndex.value, dropIndex)

  draggedIndex.value = null
  dragOverIndex.value = null
}

function handleDragEnd() {
  draggedIndex.value = null
  dragOverIndex.value = null
}
</script>

<template>
  <div class="dropdown-menu" @click.stop>
    <div class="dropdown-header">
      <span class="dropdown-title">Sloupce</span>
      <button
        class="btn-reset"
        @click="emit('reset')"
        title="Obnovit výchozí"
      >
        <RotateCcw :size="ICON_SIZE.SMALL" :stroke-width="2" />
      </button>
    </div>

    <div class="dropdown-content">
      <label
        v-for="(col, index) in columns"
        :key="col.key"
        class="column-option"
        :class="{
          'dragging': draggedIndex === index,
          'drag-over': dragOverIndex === index
        }"
        draggable="true"
        @dragstart="(e) => handleDragStart(e, index)"
        @dragover="(e) => handleDragOver(e, index)"
        @dragleave="handleDragLeave"
        @drop="(e) => handleDrop(e, index)"
        @dragend="handleDragEnd"
      >
        <GripVertical :size="ICON_SIZE.SMALL" :stroke-width="2" class="drag-handle" />
        <input
          type="checkbox"
          :checked="col.visible ?? true"
          @change="emit('toggle-column', col.key)"
          @click.stop
        />
        <span class="option-label">{{ col.label }}</span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 200px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  z-index: 1000;
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b2);
  background: var(--ground);
}

.dropdown-title {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.btn-reset {
  display: flex;
  align-items: center;
  padding: 4px;
  background: transparent;
  border: none;
  color: var(--t3);
  cursor: pointer;
  border-radius: var(--rs);
  transition: all 100ms var(--ease);
}

.btn-reset:hover {
  background: var(--b1);
  color: var(--red);
}

.dropdown-content {
  padding: 6px;
  max-height: 400px;
  overflow-y: auto;
}

.column-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  cursor: grab;
  border-radius: var(--rs);
  transition: all 100ms var(--ease);
  position: relative;
}

.column-option:hover {
  background: var(--b1);
}

.column-option.dragging {
  opacity: 0.5;
  cursor: grabbing;
}

.column-option.drag-over {
  background: var(--red-10);
  border-top: 2px solid var(--t3);
}

.column-option input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.option-label {
  font-size: var(--fs);
  color: var(--t2);
  user-select: none;
  flex: 1;
}

.drag-handle {
  color: var(--t3);
  cursor: grab;
  flex-shrink: 0;
}

.column-option.dragging .drag-handle {
  cursor: grabbing;
}
</style>
