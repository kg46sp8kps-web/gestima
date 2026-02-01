<template>
  <div class="data-table-wrapper">
    <!-- Loading overlay -->
    <div v-if="loading" class="data-table-loading">
      <Spinner size="lg" />
    </div>

    <!-- Empty state -->
    <div v-else-if="!data || data.length === 0" class="data-table-empty">
      <slot name="empty">
        <div class="empty-icon">
          <Inbox :size="48" :stroke-width="1.5" />
        </div>
        <p class="empty-text">{{ emptyText }}</p>
      </slot>
    </div>

    <!-- Table -->
    <div v-else class="data-table-container">
      <table class="data-table">
        <thead>
          <tr>
            <!-- Selection column -->
            <th v-if="selectable" class="col-select">
              <input
                v-if="multiSelect"
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected && !allSelected"
                @change="toggleAll"
              />
            </th>

            <!-- Data columns -->
            <th
              v-for="(col, colIndex) in visibleColumns"
              :key="col.key"
              :class="[
                `col-${col.key}`,
                {
                  sortable: col.sortable,
                  sorted: sortKey === col.key
                }
              ]"
              :style="col.width ? { width: col.width } : {}"
              @click="col.sortable && handleSort(col.key)"
            >
              <div class="th-content">
                <span class="th-label">{{ col.label }}</span>
                <span v-if="col.sortable" class="sort-icon">
                  <ArrowUp v-if="sortKey === col.key && sortDirection === 'asc'" :size="14" :stroke-width="2" />
                  <ArrowDown v-else-if="sortKey === col.key && sortDirection === 'desc'" :size="14" :stroke-width="2" />
                  <ArrowUpDown v-else :size="14" :stroke-width="2" />
                </span>
              </div>
            </th>

            <!-- Actions column -->
            <th v-if="$slots.actions" class="col-actions">
              {{ actionsLabel }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="(row, index) in data"
            :key="getRowKey(row, index)"
            :class="[
              { selected: isSelected(row), clickable: rowClickable }
            ]"
            @click="handleRowClick(row, index)"
          >
            <!-- Selection column -->
            <td v-if="selectable" class="col-select" @click.stop>
              <input
                type="checkbox"
                :checked="isSelected(row)"
                @change="toggleRow(row)"
              />
            </td>

            <!-- Data columns -->
            <td
              v-for="col in visibleColumns"
              :key="col.key"
              :class="`col-${col.key}`"
            >
              <!-- Custom slot for column -->
              <slot :name="`cell-${col.key}`" :row="row" :value="getCellValue(row, col)" :index="index">
                <!-- Format based on column type -->
                <template v-if="col.format === 'currency'">
                  {{ formatCurrency(getCellValue(row, col)) }}
                </template>
                <template v-else-if="col.format === 'number'">
                  {{ formatNumber(getCellValue(row, col)) }}
                </template>
                <template v-else-if="col.format === 'date'">
                  {{ formatDate(getCellValue(row, col)) }}
                </template>
                <template v-else-if="col.format === 'boolean'">
                  <Check v-if="getCellValue(row, col)" :size="16" :stroke-width="2" class="bool-icon bool-true" />
                  <X v-else :size="16" :stroke-width="2" class="bool-icon bool-false" />
                </template>
                <template v-else>
                  {{ getCellValue(row, col) ?? '—' }}
                </template>
              </slot>
            </td>

            <!-- Actions column -->
            <td v-if="$slots.actions" class="col-actions" @click.stop>
              <slot name="actions" :row="row" :index="index"></slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="pagination && data.length > 0" class="data-table-pagination">
      <div class="pagination-info">
        Zobrazeno {{ paginationStart }}-{{ paginationEnd }} z {{ pagination.total }}
      </div>

      <div class="pagination-controls">
        <button
          class="pagination-btn"
          :disabled="!hasPreviousPage"
          @click="goToPage(currentPage - 1)"
        >
          ‹ Předchozí
        </button>

        <span class="pagination-current">
          Strana {{ currentPage }} z {{ totalPages }}
        </span>

        <button
          class="pagination-btn"
          :disabled="!hasNextPage"
          @click="goToPage(currentPage + 1)"
        >
          Další ›
        </button>
      </div>

      <div class="pagination-per-page">
        <label>
          Na stránku:
          <select :value="pagination.perPage" @change="handlePerPageChange">
            <option v-for="option in perPageOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Spinner from './Spinner.vue';
import { ArrowUp, ArrowDown, ArrowUpDown, Check, X, Inbox } from 'lucide-vue-next';

// === TYPES ===

export interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  format?: 'text' | 'number' | 'currency' | 'date' | 'boolean';
  visible?: boolean;
}

export interface Pagination {
  page: number;
  perPage: number;
  total: number;
}

export interface SortState {
  key: string;
  direction: 'asc' | 'desc';
}

// === PROPS ===

interface Props {
  data: Record<string, unknown>[];
  columns: Column[];
  loading?: boolean;
  emptyText?: string;
  rowKey?: string;
  rowClickable?: boolean;
  selectable?: boolean;
  multiSelect?: boolean;
  selected?: unknown[];
  pagination?: Pagination;
  sortKey?: string;
  sortDirection?: 'asc' | 'desc';
  actionsLabel?: string;
  perPageOptions?: number[];
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
  perPageOptions: () => [10, 25, 50, 100]
});

// === EMITS ===

const emit = defineEmits<{
  'row-click': [row: Record<string, unknown>, index: number];
  'sort': [sort: SortState];
  'page-change': [page: number];
  'per-page-change': [perPage: number];
  'selection-change': [selected: unknown[]];
  'update:columns': [columns: Column[]];
}>();

// === COMPUTED ===

const visibleColumns = computed(() =>
  props.columns.filter(col => col.visible !== false)
);

// Pagination
const currentPage = computed(() => props.pagination?.page ?? 1);
const totalPages = computed(() => {
  if (!props.pagination) return 1;
  return Math.ceil(props.pagination.total / props.pagination.perPage);
});
const hasPreviousPage = computed(() => currentPage.value > 1);
const hasNextPage = computed(() => currentPage.value < totalPages.value);
const paginationStart = computed(() => {
  if (!props.pagination) return 1;
  return (props.pagination.page - 1) * props.pagination.perPage + 1;
});
const paginationEnd = computed(() => {
  if (!props.pagination) return props.data.length;
  return Math.min(
    props.pagination.page * props.pagination.perPage,
    props.pagination.total
  );
});

// Selection
const allSelected = computed(() => {
  if (!props.selectable || props.data.length === 0) return false;
  return props.data.every(row => isSelected(row));
});
const someSelected = computed(() => {
  if (!props.selectable) return false;
  return props.selected.length > 0;
});

// === METHODS ===

const getRowKey = (row: Record<string, unknown>, index: number): string | number => {
  return (row[props.rowKey] as string | number) ?? index;
};

const getCellValue = (row: Record<string, unknown>, col: Column): unknown => {
  // Support nested keys like 'user.name'
  const keys = col.key.split('.');
  let value: unknown = row;
  for (const key of keys) {
    if (value === null || value === undefined) return undefined;
    value = (value as Record<string, unknown>)[key];
  }
  return value;
};

// Formatting
const formatCurrency = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  const num = typeof value === 'number' ? value : parseFloat(String(value));
  if (isNaN(num)) return '—';
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK',
    minimumFractionDigits: 2
  }).format(num);
};

const formatNumber = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  const num = typeof value === 'number' ? value : parseFloat(String(value));
  if (isNaN(num)) return '—';
  return new Intl.NumberFormat('cs-CZ').format(num);
};

const formatDate = (value: unknown): string => {
  if (!value) return '—';
  const date = new Date(String(value));
  if (isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('cs-CZ', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date);
};

// Event handlers
const handleRowClick = (row: Record<string, unknown>, index: number) => {
  if (props.rowClickable) {
    emit('row-click', row, index);
  }
};

const handleSort = (key: string) => {
  let direction: 'asc' | 'desc' = 'asc';
  if (props.sortKey === key && props.sortDirection === 'asc') {
    direction = 'desc';
  }
  emit('sort', { key, direction });
};

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    emit('page-change', page);
  }
};

const handlePerPageChange = (event: Event) => {
  const target = event.target as HTMLSelectElement;
  emit('per-page-change', parseInt(target.value, 10));
};

// Selection
const isSelected = (row: Record<string, unknown>): boolean => {
  const key = getRowKey(row, -1);
  return props.selected.some((s: unknown) => {
    if (typeof s === 'object' && s !== null) {
      return (s as Record<string, unknown>)[props.rowKey] === key;
    }
    return s === key;
  });
};

const toggleRow = (row: Record<string, unknown>) => {
  const newSelected = [...props.selected];
  const key = getRowKey(row, -1);
  const index = newSelected.findIndex((s: unknown) => {
    if (typeof s === 'object' && s !== null) {
      return (s as Record<string, unknown>)[props.rowKey] === key;
    }
    return s === key;
  });

  if (index === -1) {
    if (props.multiSelect) {
      newSelected.push(row);
    } else {
      emit('selection-change', [row]);
      return;
    }
  } else {
    newSelected.splice(index, 1);
  }
  emit('selection-change', newSelected);
};

const toggleAll = () => {
  if (allSelected.value) {
    emit('selection-change', []);
  } else {
    emit('selection-change', [...props.data]);
  }
};
</script>

<style scoped>
/* === WRAPPER === */
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 200px;
  position: relative;
}

/* === LOADING === */
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

/* === EMPTY STATE === */
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

/* === TABLE CONTAINER === */
.data-table-container {
  overflow-x: auto;
  flex: 1;
}

/* === TABLE === */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--density-font-base, var(--text-sm));
}

/* === HEADER === */
.data-table thead {
  background: var(--bg-subtle);
  position: sticky;
  top: 0;
  z-index: 5;
}

.data-table th {
  padding: var(--density-cell-py, var(--space-3)) var(--density-cell-px, var(--space-4));
  text-align: left;
  font-weight: var(--font-semibold);
  font-size: var(--density-font-sm, var(--text-xs));
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
  user-select: none;
  transition: var(--transition-fast);
}

.data-table th.sortable {
  cursor: pointer;
}

.data-table th:hover {
  background: var(--state-hover);
}

.data-table th.sortable:hover {
  color: var(--text-primary);
}

.data-table th.sorted {
  color: var(--accent-primary);
}

.th-content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.th-label {
  flex: 1;
}

.sort-icon {
  opacity: 0.5;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.data-table th.sorted .sort-icon {
  opacity: 1;
}

/* Boolean icons */
.bool-icon {
  display: inline-block;
  vertical-align: middle;
}

.bool-true {
  color: var(--color-success);
}

.bool-false {
  color: var(--text-tertiary);
}

/* === BODY === */
.data-table tbody tr {
  transition: var(--transition-fast);
}

.data-table tbody tr:hover {
  background: var(--state-hover);
}

.data-table tbody tr.clickable {
  cursor: pointer;
}

.data-table tbody tr.selected {
  background: var(--accent-subtle);
}

.data-table tbody tr.selected:hover {
  background: var(--accent-muted);
}

.data-table td {
  padding: var(--density-cell-py, var(--space-3)) var(--density-cell-px, var(--space-4));
  border-bottom: 1px solid var(--border-default);
  color: var(--text-primary);
  vertical-align: middle;
}

/* === SPECIAL COLUMNS === */
.col-select {
  width: 40px;
  text-align: center;
}

.col-select input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.col-actions {
  width: auto;
  text-align: right;
  white-space: nowrap;
}

/* === PAGINATION === */
.data-table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  background: var(--bg-subtle);
  flex-wrap: wrap;
}

.pagination-info {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.pagination-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  min-width: 100px;
  text-align: center;
}

.pagination-per-page {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.pagination-per-page select {
  margin-left: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-raised);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

/* === RESPONSIVE === */
@media (max-width: 768px) {
  .data-table-pagination {
    flex-direction: column;
    gap: var(--space-3);
  }

  .pagination-info,
  .pagination-per-page {
    width: 100%;
    text-align: center;
  }
}
</style>
