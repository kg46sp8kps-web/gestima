<script setup lang="ts">
/**
 * Sync Logs Table
 *
 * Displays recent sync execution logs.
 */

import type { SyncLog } from '@/types/infor-sync'

defineProps<{
  logs: SyncLog[]
}>()

function logStatusBadgeClass(status: string): string {
  if (status === 'success') return 'badge-ok'
  if (status === 'error') return 'badge-error'
  return 'badge-neutral'
}
</script>

<template>
  <div class="table-container">
    <table class="logs-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Step</th>
          <th>Status</th>
          <th>ms</th>
          <th>C/U/E</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.id">
          <td class="font-mono text-xs">{{ new Date(log.created_at).toLocaleTimeString() }}</td>
          <td>{{ log.step_name }}</td>
          <td>
            <span :class="['status-badge', logStatusBadgeClass(log.status)]">
              {{ log.status }}
            </span>
          </td>
          <td class="font-mono text-xs col-num">{{ log.duration_ms ?? '-' }}</td>
          <td class="font-mono text-xs">{{ log.created_count }}/{{ log.updated_count }}/{{ log.error_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-container {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: auto;
  max-height: 400px;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
}

.logs-table th {
  background: var(--bg-surface);
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-tertiary);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  letter-spacing: 0.05em;
}

.logs-table td {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--border-subtle);
}

.logs-table tbody tr:hover {
  background: var(--hover);
}

.status-badge {
  padding: 2px 6px;
  font-size: var(--text-sm);
  border-radius: var(--radius-sm);
  font-weight: var(--font-medium);
  text-transform: uppercase;
}

.badge-ok {
  background: var(--status-ok-bg);
  color: var(--color-success);
}

.badge-error {
  background: var(--status-error-bg);
  color: var(--color-danger);
}

.badge-neutral {
  background: var(--bg-raised);
  color: var(--text-tertiary);
}
</style>
