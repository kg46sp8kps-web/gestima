<script setup lang="ts">
/**
 * Material Items List Panel - DataTable layout (UI-BIBLE Pattern 1)
 *
 * Features:
 * - DataTable with sortable columns
 * - Column chooser
 * - Search filter
 * - Shape & supplier filters
 * - Create & Import buttons
 */

import { ref, computed, onMounted } from 'vue'
import { Plus, Upload, Package } from 'lucide-vue-next'
import type { MaterialItem, MaterialGroup, StockShape } from '@/types/material'
import type { Column } from '@/components/ui/DataTable.vue'
import { getMaterialItems, getMaterialGroups } from '@/api/materials'

import DataTable from '@/components/ui/DataTable.vue'
import ColumnChooser from '@/components/ui/ColumnChooser.vue'

interface Props {
  selectedItem?: MaterialItem | null
}

const props = withDefaults(defineProps<Props>(), {
  selectedItem: null
})

const emit = defineEmits<{
  'select-item': [item: MaterialItem]
  'item-created': [item: MaterialItem]
}>()

// State
const items = ref<MaterialItem[]>([])
const groups = ref<MaterialGroup[]>([])
const loading = ref(false)
const searchQuery = ref('')
const filterGroupId = ref<number | null>(null)
const filterShape = ref<StockShape | null>(null)
const filterSupplier = ref<string | null>(null)
const selectedItemNumber = ref<string | null>(null)
const sortKey = ref('code')
const sortDirection = ref<'asc' | 'desc'>('asc')

// Column definitions
const defaultColumns: Column[] = [
  { key: 'code', label: 'KÓD', sortable: true, visible: true, format: 'text' },
  { key: 'name', label: 'Název', sortable: true, visible: true, format: 'text' },
  { key: 'shape', label: 'Tvar', sortable: true, visible: true, format: 'text' },
  { key: 'diameter', label: 'Průměr', sortable: false, visible: true, format: 'number' },
  { key: 'width', label: 'Šířka', sortable: false, visible: false, format: 'number' },
  { key: 'thickness', label: 'Tloušťka', sortable: false, visible: false, format: 'number' },
  { key: 'supplier', label: 'Dodavatel', sortable: true, visible: true, format: 'text' },
  { key: 'supplier_code', label: 'Kód dodavatele', sortable: false, visible: false, format: 'text' },
  { key: 'stock_available', label: 'Sklad (kg)', sortable: false, visible: true, format: 'number' }
]
const columns = ref<Column[]>(defaultColumns)

// Computed
const filteredItems = computed(() => {
  let result = [...items.value]

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item =>
      item.code.toLowerCase().includes(query) ||
      item.name.toLowerCase().includes(query) ||
      (item.supplier_code?.toLowerCase() || '').includes(query) ||
      (item.supplier?.toLowerCase() || '').includes(query)
    )
  }

  // Material group filter
  if (filterGroupId.value) {
    result = result.filter(item => item.material_group_id === filterGroupId.value)
  }

  // Shape filter
  if (filterShape.value) {
    result = result.filter(item => item.shape === filterShape.value)
  }

  // Supplier filter
  if (filterSupplier.value) {
    result = result.filter(item =>
      item.supplier?.toLowerCase() === filterSupplier.value?.toLowerCase()
    )
  }

  // Sort
  result.sort((a, b) => {
    let aVal: any = a[sortKey.value as keyof MaterialItem]
    let bVal: any = b[sortKey.value as keyof MaterialItem]

    // Handle null/undefined
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1

    // String comparison
    const comparison = String(aVal).localeCompare(String(bVal))
    return sortDirection.value === 'asc' ? comparison : -comparison
  })

  return result
})

const uniqueSuppliers = computed(() => {
  const suppliers = new Set<string>()
  items.value.forEach(item => {
    if (item.supplier) suppliers.add(item.supplier)
  })
  return Array.from(suppliers).sort()
})

const selectedItems = computed(() => {
  return selectedItemNumber.value !== null
    ? items.value.filter(item => item.material_number === selectedItemNumber.value)
    : []
})

const isLoading = computed(() => loading.value)
const hasItems = computed(() => items.value.length > 0)

// Methods
async function loadItems() {
  loading.value = true
  try {
    items.value = await getMaterialItems()
  } catch (error) {
    console.error('Failed to load material items:', error)
  } finally {
    loading.value = false
  }
}

async function loadGroups() {
  try {
    groups.value = await getMaterialGroups()
  } catch (error) {
    console.error('Failed to load material groups:', error)
  }
}

function handleRowClick(row: Record<string, unknown>) {
  const item = row as unknown as MaterialItem
  selectedItemNumber.value = item.material_number
  emit('select-item', item)
}

function handleSort(sort: { key: string, direction: 'asc' | 'desc' }) {
  sortKey.value = sort.key
  sortDirection.value = sort.direction
}

function handleCreate() {
  // TODO: Open create modal
  console.log('Create material item')
}

function handleImport() {
  // TODO: Open import modal
  console.log('Import material items')
}

function handleColumnsUpdate(updatedColumns: Column[]) {
  columns.value = updatedColumns

  // Save to localStorage
  const visibility = updatedColumns.reduce((acc, col) => {
    acc[col.key] = col.visible ?? true
    return acc
  }, {} as Record<string, boolean>)

  const order = updatedColumns.map(col => col.key)

  localStorage.setItem('materialItemListColumns', JSON.stringify(visibility))
  localStorage.setItem('materialItemListColumns_order', JSON.stringify(order))
}

// Lifecycle
onMounted(() => {
  loadItems()
  loadGroups()

  // Load saved column settings
  const savedVisibility = localStorage.getItem('materialItemListColumns')
  const savedOrder = localStorage.getItem('materialItemListColumns_order')

  if (savedVisibility && savedOrder) {
    try {
      const visibility = JSON.parse(savedVisibility) as Record<string, boolean>
      const order = JSON.parse(savedOrder) as string[]

      const updatedColumns = order
        .map(key => defaultColumns.find(col => col.key === key))
        .filter(col => col !== undefined)
        .map(col => ({
          ...col!,
          visible: visibility[col!.key] ?? true
        }))

      // Add any new columns that weren't in saved order
      const newColumns = defaultColumns.filter(col => !order.includes(col.key))
      columns.value = [...updatedColumns, ...newColumns]
    } catch (error) {
      console.error('Failed to load column settings:', error)
    }
  }
})

// Expose method for parent to set selection
defineExpose({
  setSelection(materialNumber: string | null) {
    selectedItemNumber.value = materialNumber
  }
})
</script>

<template>
  <div class="material-items-list-panel">
    <!-- HEADER -->
    <div class="panel-header">
      <h3 class="panel-title">Materiálové položky</h3>
      <div class="header-actions">
        <button class="btn btn-icon-sm" @click="handleImport" title="Import">
          <Upload :size="16" />
        </button>
        <button class="btn btn-primary btn-sm" @click="handleCreate">
          <Plus :size="16" />
          Nová položka
        </button>
      </div>
    </div>

    <!-- TOOLBAR -->
    <div class="toolbar">
      <!-- Search -->
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Hledat..."
        class="search-input"
      />

      <!-- Filters -->
      <div class="filters">
        <select v-model="filterGroupId" class="filter-select">
          <option :value="null">Všechny skupiny</option>
          <option v-for="group in groups" :key="group.id" :value="group.id">
            {{ group.name }}
          </option>
        </select>

        <select v-model="filterShape" class="filter-select">
          <option :value="null">Všechny tvary</option>
          <option value="round_bar">Kruhová tyč</option>
          <option value="square_bar">Čtvercová tyč</option>
          <option value="flat_bar">Plochá tyč</option>
          <option value="hexagonal_bar">Šestihranná tyč</option>
          <option value="plate">Deska/Plech</option>
          <option value="tube">Trubka</option>
        </select>

        <select v-model="filterSupplier" class="filter-select">
          <option :value="null">Všichni dodavatelé</option>
          <option v-for="supplier in uniqueSuppliers" :key="supplier" :value="supplier">
            {{ supplier }}
          </option>
        </select>
      </div>

      <!-- Column chooser -->
      <ColumnChooser :columns="columns" @update:columns="handleColumnsUpdate" />
    </div>

    <!-- TABLE -->
    <div class="table-container">
      <DataTable
        :data="filteredItems"
        :columns="columns"
        :loading="isLoading"
        :rowClickable="true"
        :selected="selectedItems"
        @row-click="handleRowClick"
        @sort="handleSort"
      >
        <!-- Custom cell templates -->
        <template #cell-shape="{ value }">
          <span class="shape-badge">{{ value || '-' }}</span>
        </template>

        <template #cell-diameter="{ value }">
          <span>{{ value ? `${value} mm` : '-' }}</span>
        </template>

        <template #cell-width="{ value }">
          <span>{{ value ? `${value} mm` : '-' }}</span>
        </template>

        <template #cell-thickness="{ value }">
          <span>{{ value ? `${value} mm` : '-' }}</span>
        </template>

        <template #cell-stock_available="{ value }">
          <span>{{ value != null ? `${value.toFixed(1)} kg` : '-' }}</span>
        </template>
      </DataTable>
    </div>

    <!-- Empty state (when no items at all) -->
    <div v-if="!loading && !hasItems" class="empty-state">
      <Package :size="48" class="empty-icon" />
      <p class="empty-title">Žádné materiálové položky</p>
      <p class="empty-hint">Začněte importem katalogu nebo vytvořte položku ručně</p>
    </div>
  </div>
</template>

<style scoped>
/* === PANEL === */
.material-items-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  padding: var(--space-4);
  background: var(--bg-base);
}

/* === HEADER === */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.panel-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: var(--space-2);
}

/* === TOOLBAR === */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

.filters {
  display: flex;
  gap: var(--space-2);
}

.filter-select {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.filter-select:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* === TABLE === */
.table-container {
  flex: 1;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

/* === CUSTOM CELLS === */
.shape-badge {
  font-size: var(--text-xs);
  padding: 2px var(--space-2);
  background: var(--bg-raised);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
}

/* === EMPTY STATE === */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--text-secondary);
}

.empty-icon {
  color: var(--text-tertiary);
}

.empty-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.empty-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  text-align: center;
}

/* === BUTTONS === */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.btn-sm {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
}

.btn-icon-sm {
  padding: var(--space-1);
  min-width: 28px;
}
</style>
