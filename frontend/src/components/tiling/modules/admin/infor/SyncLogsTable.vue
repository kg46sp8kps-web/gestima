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

function logStatusDotClass(status: string): string {
  if (status === 'success') return 'badge-dot badge-dot-ok'
  if (status === 'error') return 'badge-dot badge-dot-error'
  return 'badge-dot badge-dot-neutral'
}
</script>

<template>
  <div class="ot-wrap">
    <table class="ot">
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
          <td class="col-mono">{{ new Date(log.created_at).toLocaleTimeString() }}</td>
          <td>{{ log.step_name }}</td>
          <td>
            <span class="badge">
              <span :class="logStatusDotClass(log.status)"></span>
              {{ log.status }}
            </span>
          </td>
          <td class="col-mono col-num">{{ log.duration_ms ?? '-' }}</td>
          <td class="col-mono">{{ log.created_count }}/{{ log.updated_count }}/{{ log.error_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.ot-wrap { overflow-y: auto; max-height: 320px; border: 1px solid var(--b2); border-radius: var(--r); }
.col-mono { font-size: var(--fsm); color: var(--t3); }
</style>
