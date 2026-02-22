<script setup lang="ts" generic="T extends Record<string, unknown>">
import { ref, computed } from 'vue'
import { ChevronUp, ChevronDown } from 'lucide-vue-next'
import Spinner from './Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

export interface Column<Row = Record<string, unknown>> {
  key: string
  label: string
  sortable?: boolean
  align?: 'left' | 'center' | 'right'
  width?: string
  format?: (value: unknown, row: Row) => string
  class?: string
}

interface Props {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  selectable?: boolean
  selectedId?: string | number | null
  rowId?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectable: false,
  selectedId: null,
  rowId: 'id',
  emptyText: 'Žádná data',
})

const emit = defineEmits<{
  'row-click': [row: T]
  'sort': [key: string, dir: 'asc' | 'desc']
}>()

const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  const key = sortKey.value
  const dir = sortDir.value
  return [...props.data].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    const as = String(av).toLowerCase()
    const bs = String(bv).toLowerCase()
    return dir === 'asc' ? as.localeCompare(bs) : bs.localeCompare(as)
  })
})

function onSort(col: Column<T>) {
  if (!col.sortable) return
  if (sortKey.value === col.key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = col.key
    sortDir.value = 'asc'
  }
  emit('sort', sortKey.value!, sortDir.value)
}

function isSelected(row: T): boolean {
  if (!props.selectable || props.selectedId == null) return false
  return row[props.rowId as keyof T] === props.selectedId
}

function cellValue(row: T, col: Column<T>): string {
  const val = row[col.key]
  if (col.format) return col.format(val, row)
  if (val == null) return '—'
  return String(val)
}
</script>

<template>
  <div class="dt-wrap">
    <div v-if="loading" class="dt-loading">
      <Spinner size="sm" text="Načítám..." />
    </div>

    <div v-else-if="!data.length" class="dt-empty">
      {{ emptyText }}
    </div>

    <table v-else class="dt" data-testid="data-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :class="[
              'dt-th',
              col.align === 'right' ? 'dt-th-r' : col.align === 'center' ? 'dt-th-c' : '',
              col.sortable ? 'dt-th-sort' : '',
              col.class ?? '',
            ]"
            :style="col.width ? { width: col.width } : {}"
            @click="onSort(col)"
          >
            <span class="dt-th-inner">
              {{ col.label }}
              <span v-if="col.sortable" class="dt-sort-icon">
                <ChevronUp
                  v-if="sortKey === col.key && sortDir === 'asc'"
                  :size="ICON_SIZE_SM"
                  class="dt-sort-active"
                />
                <ChevronDown
                  v-else-if="sortKey === col.key && sortDir === 'desc'"
                  :size="ICON_SIZE_SM"
                  class="dt-sort-active"
                />
                <ChevronUp v-else :size="ICON_SIZE_SM" class="dt-sort-idle" />
              </span>
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in sortedData"
          :key="String(row[rowId as keyof T])"
          :class="['dt-row', { 'dt-row-selected': isSelected(row), 'dt-row-clickable': selectable }]"
          :data-testid="`table-row-${String(row[rowId as keyof T])}`"
          @click="selectable && emit('row-click', row)"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :class="[
              'dt-td',
              col.align === 'right' ? 'dt-td-r' : col.align === 'center' ? 'dt-td-c' : '',
              col.class ?? '',
            ]"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ cellValue(row, col) }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.dt-wrap {
  container-type: inline-size;
  width: 100%;
  overflow-x: auto;
  overflow-y: auto;
}

.dt-loading,
.dt-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: var(--t4);
  font-size: var(--fsl);
}

.dt {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs);
}

.dt-th {
  padding: 6px var(--pad);
  text-align: left;
  font-size: var(--fsl);
  font-weight: 500;
  color: var(--t3);
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--b1);
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}
.dt-th-r { text-align: right; }
.dt-th-c { text-align: center; }
.dt-th-sort { cursor: pointer; user-select: none; }
.dt-th-sort:hover { color: var(--t2); }

.dt-th-inner {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.dt-sort-icon {
  display: inline-flex;
  opacity: 0.5;
}
.dt-sort-active { opacity: 1; color: var(--t1); }
.dt-sort-idle { opacity: 0.3; }

.dt-row {
  transition: background 80ms;
  border-bottom: 1px solid var(--b1);
}
.dt-row:last-child { border-bottom: none; }
.dt-row-clickable { cursor: pointer; }
.dt-row-clickable:hover { background: rgba(255,255,255,0.03); }
.dt-row-selected { background: rgba(255,255,255,0.06); }
.dt-row-selected:hover { background: rgba(255,255,255,0.08); }

.dt-td {
  padding: 5px var(--pad);
  color: var(--t2);
  vertical-align: middle;
}
.dt-td-r { text-align: right; }
.dt-td-c { text-align: center; }
</style>
