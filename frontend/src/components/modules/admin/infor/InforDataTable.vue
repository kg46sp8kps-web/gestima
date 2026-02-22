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

const columns = computed(() => props.data.length > 0 && props.data[0] ? Object.keys(props.data[0]).filter(k => !k.startsWith('_')) : [])
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
  margin-top: 12px;
}

.table-info {
  font-size: var(--fs);
  color: var(--t3);
  margin-bottom: 6px;
  padding: 6px;
  background: var(--surface);
  border-radius: var(--rs);
}

.table-info strong {
  color: var(--red);
}

.table-scroll {
  overflow-x: auto;
  max-height: 500px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs);
}

.data-table th {
  background: var(--surface);
  padding: 6px var(--pad);
  text-align: left;
  font-weight: 600;
  color: var(--t1);
  border-bottom: 1px solid var(--b2);
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table td {
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b2);
  color: var(--t1);
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-table tbody tr:hover {
  background: var(--b1);
}

.load-more {
  display: flex;
  gap: 6px;
  padding: var(--pad);
  justify-content: center;
}

</style>
