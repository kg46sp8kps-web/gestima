<script setup lang="ts">
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { Column, SortState } from './DataTable.vue'

interface Props {
  columns: Column[]
  selectable?: boolean
  multiSelect?: boolean
  allSelected?: boolean
  someSelected?: boolean
  sortKey?: string
  sortDirection?: 'asc' | 'desc'
  actionsLabel?: string
  hasActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selectable: false,
  multiSelect: false,
  allSelected: false,
  someSelected: false,
  actionsLabel: 'Akce',
  hasActions: false
})

const emit = defineEmits<{
  'toggle-all': []
  'sort': [sort: SortState]
}>()

function handleSort(column: Column) {
  if (!column.sortable) return

  let direction: 'asc' | 'desc' = 'asc'
  if (props.sortKey === column.key && props.sortDirection === 'asc') {
    direction = 'desc'
  }
  emit('sort', { key: column.key, direction })
}
</script>

<template>
  <thead>
    <tr>
      <!-- Selection column -->
      <th v-if="selectable" class="col-select">
        <input
          v-if="multiSelect"
          type="checkbox"
          :checked="allSelected"
          :indeterminate="someSelected && !allSelected"
          @change="emit('toggle-all')"
        />
      </th>

      <!-- Data columns -->
      <th
        v-for="col in columns"
        :key="col.key"
        :class="[
          `col-${col.key}`,
          {
            sortable: col.sortable,
            sorted: sortKey === col.key
          }
        ]"
        :style="col.width ? { width: col.width } : {}"
        @click="handleSort(col)"
      >
        <div class="th-content">
          <span class="th-label">{{ col.label }}</span>
          <span v-if="col.sortable" class="sort-icon">
            <ArrowUp v-if="sortKey === col.key && sortDirection === 'asc'" :size="ICON_SIZE.SMALL" :stroke-width="2" />
            <ArrowDown v-else-if="sortKey === col.key && sortDirection === 'desc'" :size="ICON_SIZE.SMALL" :stroke-width="2" />
            <ArrowUpDown v-else :size="ICON_SIZE.SMALL" :stroke-width="2" />
          </span>
        </div>
      </th>

      <!-- Actions column -->
      <th v-if="hasActions" class="col-actions">
        {{ actionsLabel }}
      </th>
    </tr>
  </thead>
</template>

<style scoped>
.data-table thead {
  background: var(--ground);
  position: sticky;
  top: 0;
  z-index: 5;
}

.data-table th {
  padding: 3px 10px;
  text-align: left;
  font-weight: 600;
  font-size: var(--density-font-sm, var(--fs));
  color: var(--t3);
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  user-select: none;
  transition: all 100ms var(--ease);
}

.data-table th.sortable {
  cursor: pointer;
}

.data-table th:hover {
  background: var(--b1);
}

.data-table th.sortable:hover {
  color: var(--t1);
}

.data-table th.sorted {
  color: var(--red);
}

.th-content {
  display: flex;
  align-items: center;
  gap: 6px;
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
</style>
