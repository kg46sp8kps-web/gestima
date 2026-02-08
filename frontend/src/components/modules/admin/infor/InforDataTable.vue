<script setup lang="ts">
interface Props {
  data: Record<string, unknown>[]
}

defineProps<Props>()
</script>

<template>
  <div v-if="data && data.length > 0" class="data-table-wrapper">
    <div class="table-info">
      Loaded <strong>{{ data.length }}</strong> records
    </div>
    <div class="table-scroll">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="key in Object.keys(data[0])" :key="key">{{ key }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in data" :key="idx">
            <td v-for="key in Object.keys(row)" :key="key">{{ row[key] }}</td>
          </tr>
        </tbody>
      </table>
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
  border: 1px solid var(--border-color);
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
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}
</style>
