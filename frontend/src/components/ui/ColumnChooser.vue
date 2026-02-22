<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Settings } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import ColumnChooserDropdown from './ColumnChooserDropdown.vue'
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

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
}

function toggleColumn(key: string) {
  const updated: Column[] = props.columns.map(col =>
    col.key === key ? { ...col, visible: !(col.visible ?? true) } : col
  )
  emit('update:columns', updated)
  saveToLocalStorage(updated)
}

function resetToDefaults() {
  const updated: Column[] = props.columns.map(col => ({ ...col, visible: true }))
  emit('update:columns', updated)
  saveToLocalStorage(updated)
}

function handleReorder(fromIndex: number, toIndex: number) {
  const updated = [...props.columns]
  const [draggedColumn] = updated.splice(fromIndex, 1)
  if (!draggedColumn) return
  updated.splice(toIndex, 0, draggedColumn)

  emit('update:columns', updated)
  saveToLocalStorage(updated)
}

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

  if (storedOrder) {
    try {
      const order = JSON.parse(storedOrder) as string[]
      columns = order
        .map(key => columns.find(col => col.key === key))
        .filter((col): col is Column => col !== undefined)

      const existingKeys = new Set(order)
      const newColumns = props.columns.filter(col => !existingKeys.has(col.key))
      columns = [...columns, ...newColumns]
    } catch (error) {
      // Ignore parse errors
    }
  }

  if (storedVisibility) {
    try {
      const visibility = JSON.parse(storedVisibility) as Record<string, boolean>
      columns = columns.map(col => ({
        ...col,
        visible: visibility[col.key] !== undefined ? visibility[col.key] : (col.visible ?? true)
      }))
    } catch (error) {
      // Ignore parse errors
    }
  }

  if (storedVisibility || storedOrder) {
    emit('update:columns', columns)
  }
}

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
      <Settings :size="ICON_SIZE.SMALL" :stroke-width="2" />
    </button>

    <Transition name="dropdown-fade">
      <ColumnChooserDropdown
        v-if="showDropdown"
        :columns="columns"
        @toggle-column="toggleColumn"
        @reset="resetToDefaults"
        @reorder="handleReorder"
      />
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
  padding: 4px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.btn-chooser:hover {
  background: var(--b1);
  border-color: var(--b3);
  color: var(--t1);
}

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
