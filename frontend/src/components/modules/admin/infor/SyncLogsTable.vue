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
  border: 1px solid var(--b2);
  border-radius: var(--r);
  overflow: auto;
  max-height: 400px;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
}

.logs-table th {
  background: var(--surface);
  padding: 6px var(--pad);
  text-align: left;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  border-bottom: 1px solid var(--b2);
  position: sticky;
  top: 0;
  letter-spacing: 0.05em;
}

.logs-table td {
  padding: 6px var(--pad);
  font-size: var(--fs);
  border-bottom: 1px solid var(--b1);
}

.logs-table tbody tr:hover {
  background: var(--b1);
}

.status-badge {
  padding: 2px 6px;
  font-size: var(--fs);
  border-radius: var(--rs);
  font-weight: 500;
  text-transform: uppercase;
}

.badge-ok {
  background: rgba(52,211,153,0.1);
  color: var(--ok);
}

.badge-error {
  background: rgba(248,113,113,0.1);
  color: var(--err);
}

.badge-neutral {
  background: var(--raised);
  color: var(--t3);
}
</style>
