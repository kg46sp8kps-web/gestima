<template>
  <div class="data-table-wrapper">
    <div v-if="loading" class="data-table-loading">
      <Spinner size="lg" />
    </div>

    <div v-else-if="!data || data.length === 0" class="data-table-empty">
      <slot name="empty">
        <div class="empty-icon">
          <Inbox :size="ICON_SIZE.HERO" :stroke-width="1.5" />
        </div>
        <p class="empty-text">{{ emptyText }}</p>
      </slot>
    </div>

    <div v-else class="data-table-container">
      <table class="data-table">
        <DataTableHeader
          :columns="visibleColumns"
          :selectable="selectable"
          :multi-select="multiSelect"
          :all-selected="allSelected"
          :some-selected="someSelected"
          :sort-key="sortKey"
          :sort-direction="sortDirection"
          :actions-label="actionsLabel"
          :has-actions="!!$slots.actions"
          @toggle-all="toggleAll"
          @sort="handleSort"
        />

        <DataTableBody
          :data="data"
          :columns="visibleColumns"
          :row-key="rowKey"
          :row-clickable="rowClickable"
          :selectable="selectable"
          :selected="selected"
          :highlighted-index="highlightedIndex"
          :has-actions="!!$slots.actions"
          @row-click="handleRowClick"
          @toggle-row="toggleRow"
          @row-hover="(row, index) => $emit('row-hover', row, index)"
          @row-leave="$emit('row-leave')"
        >
          <template v-for="col in visibleColumns" #[`cell-${col.key}`]="slotProps">
            <slot :name="`cell-${col.key}`" v-bind="slotProps"></slot>
          </template>
          <template #actions="slotProps">
            <slot name="actions" v-bind="slotProps"></slot>
          </template>
        </DataTableBody>
      </table>
    </div>

    <DataTablePagination
      v-if="pagination && data.length > 0"
      :pagination="pagination"
      :data-length="data.length"
      :per-page-options="perPageOptions"
      @page-change="goToPage"
      @per-page-change="handlePerPageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Spinner from './Spinner.vue'
import { Inbox } from 'lucide-vue-next'
import DataTableHeader from './DataTableHeader.vue'
import DataTableBody from './DataTableBody.vue'
import DataTablePagination from './DataTablePagination.vue'
import { ICON_SIZE } from '@/config/design'

export interface Column {
  key: string
  label: string
  sortable?: boolean
  width?: string
  format?: 'text' | 'number' | 'currency' | 'date' | 'boolean'
  visible?: boolean
}

export interface Pagination {
  page: number
  perPage: number
  total: number
}

export interface SortState {
  key: string
  direction: 'asc' | 'desc'
}

interface Props {
  data: Record<string, unknown>[]
  columns: Column[]
  loading?: boolean
  emptyText?: string
  rowKey?: string
  rowClickable?: boolean
  selectable?: boolean
  multiSelect?: boolean
  selected?: unknown[]
  pagination?: Pagination
  sortKey?: string
  sortDirection?: 'asc' | 'desc'
  actionsLabel?: string
  perPageOptions?: number[]
  highlightedIndex?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  emptyText: 'Žádná data k zobrazení',
  rowKey: 'id',
  rowClickable: false,
  selectable: false,
  multiSelect: false,
  selected: () => [],
  actionsLabel: 'Akce',
  perPageOptions: () => [10, 25, 50, 100],
  highlightedIndex: null
})

const emit = defineEmits<{
  'row-click': [row: Record<string, unknown>, index: number]
  'sort': [sort: SortState]
  'page-change': [page: number]
  'per-page-change': [perPage: number]
  'selection-change': [selected: unknown[]]
  'update:columns': [columns: Column[]]
  'row-hover': [row: Record<string, unknown>, index: number]
  'row-leave': []
}>()

const visibleColumns = computed(() =>
  props.columns.filter(col => col.visible !== false)
)

const allSelected = computed(() => {
  if (!props.selectable || props.data.length === 0) return false
  return props.data.every(row => isSelected(row))
})

const someSelected = computed(() => {
  if (!props.selectable) return false
  return props.selected.length > 0
})

function getRowKey(row: Record<string, unknown>, index: number): string | number {
  return (row[props.rowKey] as string | number) ?? index
}

function isSelected(row: Record<string, unknown>): boolean {
  const key = getRowKey(row, -1)
  return props.selected.some((s: unknown) => {
    if (typeof s === 'object' && s !== null) {
      return (s as Record<string, unknown>)[props.rowKey] === key
    }
    return s === key
  })
}

function handleRowClick(row: Record<string, unknown>, index: number) {
  if (props.rowClickable) {
    emit('row-click', row, index)
  }
}

function handleSort(sort: SortState) {
  emit('sort', sort)
}

function goToPage(page: number) {
  emit('page-change', page)
}

function handlePerPageChange(perPage: number) {
  emit('per-page-change', perPage)
}

function toggleRow(row: Record<string, unknown>) {
  const newSelected = [...props.selected]
  const key = getRowKey(row, -1)
  const index = newSelected.findIndex((s: unknown) => {
    if (typeof s === 'object' && s !== null) {
      return (s as Record<string, unknown>)[props.rowKey] === key
    }
    return s === key
  })

  if (index === -1) {
    if (props.multiSelect) {
      newSelected.push(row)
    } else {
      emit('selection-change', [row])
      return
    }
  } else {
    newSelected.splice(index, 1)
  }
  emit('selection-change', newSelected)
}

function toggleAll() {
  if (allSelected.value) {
    emit('selection-change', [])
  } else {
    emit('selection-change', [...props.data])
  }
}
</script>

<style scoped>
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 200px;
  position: relative;
}

.data-table-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-overlay);
  border-radius: var(--radius-md);
  z-index: 10;
}

.data-table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  color: var(--text-secondary);
}

.empty-icon {
  margin-bottom: var(--space-4);
  opacity: 0.3;
  color: var(--text-tertiary);
}

.empty-text {
  font-size: var(--text-base);
  margin: 0;
}

.data-table-container {
  overflow-x: auto;
  flex: 1;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--density-font-base, var(--text-sm));
}
</style>
