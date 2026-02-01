<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import type { Column } from '@/components/ui/DataTable.vue'
import { Plus, Package } from 'lucide-vue-next'

import DataTable from '@/components/ui/DataTable.vue'
import ColumnChooser from '@/components/ui/ColumnChooser.vue'

interface Props {
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'select-part': [part: Part]
  'create-new': []
}>()

const partsStore = usePartsStore()
const searchQuery = ref('')
const selectedPartId = ref<number | null>(null)
const sortKey = ref('article_number')
const sortDirection = ref<'asc' | 'desc'>('asc')

// Column definitions - explicitly typed to satisfy TypeScript
const defaultColumns: Column[] = [
  { key: 'article_number', label: 'ARTIKL', sortable: true, visible: true, format: 'text' },
  { key: 'name', label: 'Název', sortable: true, visible: true, format: 'text' },
  { key: 'revision', label: 'Revize', sortable: false, visible: true, format: 'text' },
  { key: 'customer_revision', label: 'Zák. revize', sortable: false, visible: true, format: 'text' },
  { key: 'drawing_number', label: 'Číslo výkresu', sortable: false, visible: false, format: 'text' },
  { key: 'status', label: 'Status', sortable: false, visible: true, format: 'text' },
  { key: 'length', label: 'Délka', sortable: false, visible: true, format: 'number' },
  { key: 'notes', label: 'Poznámky', sortable: false, visible: true, format: 'text' },
  { key: 'created_at', label: 'Vytvořeno', sortable: true, visible: true, format: 'date' }
]
const columns = ref<Column[]>(defaultColumns)

// Filter and sort parts
const filteredParts = computed(() => {
  let list = [...partsStore.parts]

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      (p.article_number && p.article_number.toLowerCase().includes(query)) ||
      p.name.toLowerCase().includes(query) ||
      (p.notes && p.notes.toLowerCase().includes(query))
    )
  }

  // Sort
  list.sort((a, b) => {
    let aVal: any = a[sortKey.value as keyof Part]
    let bVal: any = b[sortKey.value as keyof Part]

    // Handle null/undefined
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1

    // Numeric sort for article_number if numeric
    if (sortKey.value === 'article_number') {
      const aNum = parseInt(String(aVal))
      const bNum = parseInt(String(bVal))
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return sortDirection.value === 'asc' ? aNum - bNum : bNum - aNum
      }
    }

    // String comparison
    const comparison = String(aVal).localeCompare(String(bVal))
    return sortDirection.value === 'asc' ? comparison : -comparison
  })

  return list
})

const isLoading = computed(() => partsStore.loading)
const hasParts = computed(() => partsStore.parts.length > 0)
const selectedParts = computed(() => {
  return selectedPartId.value !== null
    ? partsStore.parts.filter(p => p.id === selectedPartId.value)
    : []
})

function handleRowClick(row: Record<string, unknown>) {
  const part = row as unknown as Part
  selectedPartId.value = part.id
  emit('select-part', part)
}

function handleSort(sort: { key: string, direction: 'asc' | 'desc' }) {
  sortKey.value = sort.key
  sortDirection.value = sort.direction
}

function handleCreate() {
  emit('create-new')
}

function handleColumnsUpdate(updatedColumns: Column[]) {
  columns.value = updatedColumns

  // Save to localStorage (visibility + order)
  const visibility = updatedColumns.reduce((acc, col) => {
    acc[col.key] = col.visible ?? true
    return acc
  }, {} as Record<string, boolean>)

  const order = updatedColumns.map(col => col.key)

  localStorage.setItem('partListColumns', JSON.stringify(visibility))
  localStorage.setItem('partListColumns_order', JSON.stringify(order))
}

onMounted(async () => {
  await partsStore.fetchParts()
})

// Expose method for parent to set selection
defineExpose({
  setSelection(partId: number | null) {
    selectedPartId.value = partId
  }
})
</script>

<template>
  <div class="part-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Díly</h3>
      <div class="header-actions">
        <ColumnChooser
          :columns="columns"
          storageKey="partListColumns"
          @update:columns="handleColumnsUpdate"
        />
        <button @click="handleCreate" class="btn-create">
          <Plus :size="14" :stroke-width="2" />
          Nový
        </button>
      </div>
    </div>

    <!-- Search Bar -->
    <input
      v-model="searchQuery"
      v-select-on-focus
      type="text"
      placeholder="Filtrovat díly..."
      class="search-input"
    />

    <!-- DataTable -->
    <div class="table-container">
      <DataTable
        :data="filteredParts"
        :columns="columns"
        :loading="isLoading"
        :rowClickable="true"
        :selected="selectedParts"
        :sortKey="sortKey"
        :sortDirection="sortDirection"
        emptyText="Žádné díly"
        @row-click="handleRowClick"
        @sort="handleSort"
        @update:columns="handleColumnsUpdate"
      >
        <!-- Custom cell for article_number (bold + colored) -->
        <template #cell-article_number="{ value }">
          <span class="article-number">{{ value || '—' }}</span>
        </template>

        <!-- Custom cell for notes (truncate) -->
        <template #cell-notes="{ value }">
          <span class="notes-truncate" :title="String(value || '')">
            {{ value || '—' }}
          </span>
        </template>

        <!-- Custom cell for status (badge) -->
        <template #cell-status="{ value }">
          <span v-if="value" class="status-badge" :class="`status-${value}`">
            {{ value }}
          </span>
          <span v-else>—</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.part-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.list-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-create {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-create:hover {
  background: var(--color-primary-hover);
}

.search-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.search-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.table-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Custom cell styles */
.article-number {
  font-weight: var(--font-semibold);
  color: var(--color-primary);
}

.notes-truncate {
  display: block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
}

.status-active {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status-draft {
  background: var(--bg-subtle);
  color: var(--text-secondary);
}

.status-archived {
  background: var(--bg-subtle);
  color: var(--text-tertiary);
}
</style>
