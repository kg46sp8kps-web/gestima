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
  top: calc(100% + var(--space-1));
  right: 0;
  min-width: 200px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 1000;
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-subtle);
}

.dropdown-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-reset {
  display: flex;
  align-items: center;
  padding: var(--space-1);
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.btn-reset:hover {
  background: var(--state-hover);
  color: var(--color-primary);
}

.dropdown-content {
  padding: var(--space-2);
  max-height: 400px;
  overflow-y: auto;
}

.column-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  cursor: grab;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
  position: relative;
}

.column-option:hover {
  background: var(--state-hover);
}

.column-option.dragging {
  opacity: 0.5;
  cursor: grabbing;
}

.column-option.drag-over {
  background: var(--brand-subtle);
  border-top: 2px solid var(--palette-info);
}

.column-option input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.option-label {
  font-size: var(--text-sm);
  color: var(--text-body);
  user-select: none;
  flex: 1;
}

.drag-handle {
  color: var(--text-tertiary);
  cursor: grab;
  flex-shrink: 0;
}

.column-option.dragging .drag-handle {
  cursor: grabbing;
}
</style>
