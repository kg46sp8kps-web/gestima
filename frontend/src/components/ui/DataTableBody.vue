<script setup lang="ts">
import { Check, X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { Column } from './DataTable.vue'
import { formatCurrency, formatNumber, formatDate } from '@/utils/formatters'

interface Props {
  data: Record<string, unknown>[]
  columns: Column[]
  rowKey?: string
  rowClickable?: boolean
  selectable?: boolean
  selected?: unknown[]
  highlightedIndex?: number | null
  hasActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  rowKey: 'id',
  rowClickable: false,
  selectable: false,
  selected: () => [],
  highlightedIndex: null,
  hasActions: false
})

const emit = defineEmits<{
  'row-click': [row: Record<string, unknown>, index: number]
  'toggle-row': [row: Record<string, unknown>]
  'row-hover': [row: Record<string, unknown>, index: number]
  'row-leave': []
}>()

function getRowKey(row: Record<string, unknown>, index: number): string | number {
  return (row[props.rowKey] as string | number) ?? index
}

function getCellValue(row: Record<string, unknown>, col: Column): unknown {
  const keys = col.key.split('.')
  let value: unknown = row
  for (const key of keys) {
    if (value === null || value === undefined) return undefined
    value = (value as Record<string, unknown>)[key]
  }
  return value
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
</script>

<template>
  <tbody>
    <tr
      v-for="(row, index) in data"
      :key="getRowKey(row, index)"
      :class="[
        { selected: isSelected(row), clickable: rowClickable, highlighted: index === highlightedIndex }
      ]"
      @click="emit('row-click', row, index)"
      @mouseenter="emit('row-hover', row, index)"
      @mouseleave="emit('row-leave')"
    >
      <!-- Selection column -->
      <td v-if="selectable" class="col-select" @click.stop>
        <input
          type="checkbox"
          :checked="isSelected(row)"
          @change="emit('toggle-row', row)"
        />
      </td>

      <!-- Data columns -->
      <td
        v-for="col in columns"
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
            <Check v-if="getCellValue(row, col)" :size="ICON_SIZE.SMALL" :stroke-width="2" class="bool-icon bool-true" />
            <X v-else :size="ICON_SIZE.SMALL" :stroke-width="2" class="bool-icon bool-false" />
          </template>
          <template v-else>
            {{ getCellValue(row, col) ?? '—' }}
          </template>
        </slot>
      </td>

      <!-- Actions column -->
      <td v-if="hasActions" class="col-actions" @click.stop>
        <slot name="actions" :row="row" :index="index"></slot>
      </td>
    </tr>
  </tbody>
</template>

<style scoped>
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
  background: var(--selected);
}

.data-table tbody tr.selected:hover {
  background: var(--active);
}

.data-table tbody tr.highlighted {
  background: var(--state-hover);
  outline: 1px solid var(--border-focus);
}

.data-table td {
  padding: var(--density-cell-py, var(--space-3)) var(--density-cell-px, var(--space-4));
  border-bottom: 1px solid var(--border-default);
  color: var(--text-primary);
  vertical-align: middle;
}

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
</style>
