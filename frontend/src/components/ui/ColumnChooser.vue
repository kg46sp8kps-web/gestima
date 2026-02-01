<script setup lang="ts">
/**
 * ColumnChooser - Dropdown for toggling table column visibility
 * Features: Checkboxes, Reset button, localStorage persistence, Drag & Drop reordering
 */

import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { Settings, RotateCcw, GripVertical } from 'lucide-vue-next'
import type { Column } from './DataTable.vue'

interface Props {
  columns: Column[]
  storageKey: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:columns': [columns: Column[]]
}>()

const showDropdown = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// Toggle dropdown
function toggleDropdown() {
  showDropdown.value = !showDropdown.value
}

// Toggle column visibility
function toggleColumn(key: string) {
  const updated: Column[] = props.columns.map(col =>
    col.key === key ? { ...col, visible: !(col.visible ?? true) } : col
  )
  emit('update:columns', updated)
  saveToLocalStorage(updated)
}

// Reset to defaults (all visible)
function resetToDefaults() {
  const updated: Column[] = props.columns.map(col => ({ ...col, visible: true }))
  emit('update:columns', updated)
  saveToLocalStorage(updated)
}

// localStorage persistence
function saveToLocalStorage(columns: Column[]) {
  const visibility = columns.reduce((acc, col) => {
    acc[col.key] = col.visible ?? true
    return acc
  }, {} as Record<string, boolean>)

  const order = columns.map(col => col.key)

  localStorage.setItem(props.storageKey, JSON.stringify(visibility))
  localStorage.setItem(`${props.storageKey}_order`, JSON.stringify(order))
}

function loadFromLocalStorage() {
  const storedVisibility = localStorage.getItem(props.storageKey)
  const storedOrder = localStorage.getItem(`${props.storageKey}_order`)

  let columns = [...props.columns]

  // Apply saved order
  if (storedOrder) {
    try {
      const order = JSON.parse(storedOrder) as string[]
      columns = order
        .map(key => columns.find(col => col.key === key))
        .filter((col): col is Column => col !== undefined)

      // Add any new columns that weren't in saved order
      const existingKeys = new Set(order)
      const newColumns = props.columns.filter(col => !existingKeys.has(col.key))
      columns = [...columns, ...newColumns]
    } catch (error) {
      console.error('Failed to load column order:', error)
    }
  }

  // Apply visibility
  if (storedVisibility) {
    try {
      const visibility = JSON.parse(storedVisibility) as Record<string, boolean>
      columns = columns.map(col => ({
        ...col,
        visible: visibility[col.key] !== undefined ? visibility[col.key] : (col.visible ?? true)
      }))
    } catch (error) {
      console.error('Failed to load column visibility:', error)
    }
  }

  if (storedVisibility || storedOrder) {
    emit('update:columns', columns)
  }
}

// Drag and drop handlers
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

  const updated = [...props.columns]
  const [draggedColumn] = updated.splice(draggedIndex.value, 1)
  updated.splice(dropIndex, 0, draggedColumn)

  emit('update:columns', updated)
  saveToLocalStorage(updated)

  draggedIndex.value = null
  dragOverIndex.value = null
}

function handleDragEnd() {
  draggedIndex.value = null
  dragOverIndex.value = null
}

// Close dropdown when clicking outside
function handleClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    showDropdown.value = false
  }
}

onMounted(() => {
  loadFromLocalStorage()
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<template>
  <div class="column-chooser" ref="dropdownRef">
    <button
      class="btn-chooser"
      @click="toggleDropdown"
      title="Vybrat sloupce"
    >
      <Settings :size="16" :stroke-width="2" />
    </button>

    <Transition name="dropdown-fade">
      <div v-if="showDropdown" class="dropdown-menu" @click.stop>
        <div class="dropdown-header">
          <span class="dropdown-title">Sloupce</span>
          <button
            class="btn-reset"
            @click="resetToDefaults"
            title="Obnovit výchozí"
          >
            <RotateCcw :size="14" :stroke-width="2" />
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
            <GripVertical :size="14" :stroke-width="2" class="drag-handle" />
            <input
              type="checkbox"
              :checked="col.visible ?? true"
              @change="toggleColumn(col.key)"
              @click.stop
            />
            <span class="option-label">{{ col.label }}</span>
          </label>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.column-chooser {
  position: relative;
}

.btn-chooser {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-1);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-chooser:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

/* Dropdown Menu */
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
  background: var(--accent-subtle);
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

/* Dropdown Transition */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
