<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Props {
  data: Record<string, unknown>[]
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  pageSize: 50
})

const visibleCount = ref(props.pageSize)

// Reset when data changes
watch(() => props.data, () => { visibleCount.value = props.pageSize })

const columns = computed(() => props.data.length > 0 ? Object.keys(props.data[0]).filter(k => !k.startsWith('_')) : [])
const visibleData = computed(() => props.data.slice(0, visibleCount.value))
const hasMore = computed(() => visibleCount.value < props.data.length)
const remaining = computed(() => props.data.length - visibleCount.value)

function showMore() {
  visibleCount.value = Math.min(visibleCount.value + props.pageSize, props.data.length)
}

function showAll() {
  visibleCount.value = props.data.length
}

function formatCell(value: unknown): string {
  if (value == null || value === '') return '-'
  const str = String(value)
  const num = Number(str)
  if (!isNaN(num) && str.includes('.')) {
    return num.toFixed(2)
  }
  return str
}
</script>

<template>
  <div v-if="data && data.length > 0" class="data-table-wrapper">
    <div class="table-info">
      Zobrazeno <strong>{{ visibleData.length }}</strong> z <strong>{{ data.length }}</strong> záznamů
    </div>
    <div class="table-scroll">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="key in columns" :key="key">{{ key }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in visibleData" :key="idx">
            <td v-for="key in columns" :key="key">{{ formatCell(row[key]) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="hasMore" class="load-more">
      <button @click="showMore" class="btn-ghost">
        Zobrazit dalších {{ Math.min(pageSize, remaining) }} (zbývá {{ remaining }})
      </button>
      <button v-if="remaining > pageSize" @click="showAll" class="btn-ghost btn-secondary">
        Zobrazit vše ({{ data.length }})
      </button>
    </div>
  </div>
</template>

<style scoped>
.data-table-wrapper {
  margin-top: var(--space-4);
}

.table-info {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
}

.table-info strong {
  color: var(--color-primary);
}

.table-scroll {
  overflow-x: auto;
  max-height: 500px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th {
  background: var(--bg-surface);
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-default);
  color: var(--text-primary);
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.load-more {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  justify-content: center;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-ghost:hover { background: var(--state-hover); border-color: var(--border-strong); }
.btn-ghost.btn-secondary { color: var(--text-secondary); }
</style>
