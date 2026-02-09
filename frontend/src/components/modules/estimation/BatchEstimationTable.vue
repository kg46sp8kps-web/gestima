<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MachiningTimeEstimation } from '@/types/estimation'
import { ArrowUp, ArrowDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  results: MachiningTimeEstimation[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'select': [result: MachiningTimeEstimation]
}>()

const selectedFilename = ref<string | null>(null)
const sortKey = ref<keyof MachiningTimeEstimation | 'removal'>('filename')
const sortDirection = ref<'asc' | 'desc'>('asc')

const sortedResults = computed(() => {
  const list = [...props.results]

  list.sort((a, b) => {
    let aVal: string | number
    let bVal: string | number

    if (sortKey.value === 'removal') {
      aVal = a.breakdown?.material_to_remove_mm3 ?? 0
      bVal = b.breakdown?.material_to_remove_mm3 ?? 0
    } else {
      const key = sortKey.value as keyof MachiningTimeEstimation
      const rawA = a[key]
      const rawB = b[key]

      if (typeof rawA === 'object' || typeof rawB === 'object' || rawA === undefined || rawB === undefined || typeof rawA === 'boolean' || typeof rawB === 'boolean') {
        return 0
      }

      aVal = rawA as string | number
      bVal = rawB as string | number
    }

    if (typeof aVal === 'string') {
      return sortDirection.value === 'asc'
        ? aVal.localeCompare(bVal as string)
        : (bVal as string).localeCompare(aVal)
    }

    return sortDirection.value === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
  })

  return list
})

function selectResult(result: MachiningTimeEstimation) {
  selectedFilename.value = result.filename
  emit('select', result)
}

function toggleSort(key: keyof MachiningTimeEstimation | 'removal') {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDirection.value = 'asc'
  }
}

function volumeInCm3(volumeMm3: number): string {
  return (volumeMm3 / 1000).toFixed(1)
}

function getSortIcon(key: keyof MachiningTimeEstimation | 'removal') {
  if (sortKey.value !== key) return null
  return sortDirection.value === 'asc' ? ArrowUp : ArrowDown
}
</script>

<template>
  <div class="batch-estimation-table">
    <div class="table-header">
      <h3>Batch Estimation Results</h3>
      <span class="results-count">{{ results.length }} files</span>
    </div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th class="sortable" @click="toggleSort('filename')">
              <span>Filename</span>
              <component v-if="getSortIcon('filename')" :is="getSortIcon('filename')" :size="ICON_SIZE.SMALL" />
            </th>
            <th>Material</th>
            <th class="sortable numeric" @click="toggleSort('removal')">
              <span>Removal (cm³)</span>
              <component v-if="getSortIcon('removal')" :is="getSortIcon('removal')" :size="ICON_SIZE.SMALL" />
            </th>
            <th class="sortable numeric" @click="toggleSort('roughing_time_min')">
              <span>Rough (min)</span>
              <component v-if="getSortIcon('roughing_time_min')" :is="getSortIcon('roughing_time_min')" :size="ICON_SIZE.SMALL" />
            </th>
            <th class="sortable numeric" @click="toggleSort('finishing_time_min')">
              <span>Finish (min)</span>
              <component v-if="getSortIcon('finishing_time_min')" :is="getSortIcon('finishing_time_min')" :size="ICON_SIZE.SMALL" />
            </th>
            <th class="sortable numeric" @click="toggleSort('total_time_min')">
              <span>Total (min)</span>
              <component v-if="getSortIcon('total_time_min')" :is="getSortIcon('total_time_min')" :size="ICON_SIZE.SMALL" />
            </th>
            <th class="numeric">Constraints</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in sortedResults" :key="result.filename" :class="{ selected: selectedFilename === result.filename }" @click="selectResult(result)">
            <td class="filename">{{ result.filename }}</td>
            <td class="material-cell">{{ result.breakdown?.material ?? 'N/A' }}</td>
            <td class="numeric">{{ volumeInCm3(result.breakdown?.material_to_remove_mm3 ?? 0) }}</td>
            <td class="numeric">{{ (result.roughing_time_min ?? 0).toFixed(2) }}</td>
            <td class="numeric">{{ (result.finishing_time_min ?? 0).toFixed(2) }}</td>
            <td class="numeric total-time">{{ (result.total_time_min ?? 0).toFixed(2) }}</td>
            <td class="numeric">
              <span v-if="(result.breakdown?.constraint_multiplier ?? 1) > 1" class="constraint-badge" :class="{ critical: (result.breakdown?.constraint_multiplier ?? 1) >= 2.0, warning: (result.breakdown?.constraint_multiplier ?? 1) >= 1.5 && (result.breakdown?.constraint_multiplier ?? 1) < 2.0 }">
                {{ (result.breakdown?.constraint_multiplier ?? 1).toFixed(2) }}x
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.batch-estimation-table {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-default);
}

.table-header h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.results-count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.table-container {
  flex: 1;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

thead {
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  z-index: 1;
}

th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
  text-transform: uppercase;
  font-size: var(--text-xs);
}

th.sortable {
  cursor: pointer;
  user-select: none;
}

th.sortable:hover {
  color: var(--text-primary);
  background: var(--state-hover);
}

th.sortable span {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

th.numeric {
  text-align: right;
}

tbody tr {
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

tbody tr:hover {
  background: var(--state-hover);
}

tbody tr.selected {
  background: var(--state-selected);
}

td {
  padding: var(--space-3) var(--space-4);
  color: var(--text-body);
  border-bottom: 1px solid var(--border-subtle);
}

td.filename {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

td.material-cell {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

td.numeric {
  text-align: right;
  font-family: var(--font-mono);
}

td.total-time {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.type-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.type-badge.rot {
  background: var(--color-info);
  color: white;
}

.type-badge.pri {
  background: var(--color-success);
  color: white;
}

.constraint-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  background: var(--color-info);
  color: white;
}

.constraint-badge.warning {
  background: var(--color-warning);
  color: white;
}

.constraint-badge.critical {
  background: var(--color-danger);
  color: white;
}
</style>
