<script setup lang="ts">
/**
 * Sync Steps Table
 *
 * Displays pipeline steps with status and actions.
 */

import { ref } from 'vue'
import { Play, Power, CheckCircle, XCircle, Clock } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { SyncState } from '@/types/infor-sync'

defineProps<{
  steps: SyncState[]
  triggeringStep: string | null
}>()

const emit = defineEmits<{
  (e: 'trigger', stepName: string): void
  (e: 'toggle-enabled', step: SyncState): void
}>()

function stepStatus(step: SyncState): 'ok' | 'error' | 'idle' {
  if (step.last_error) return 'error'
  if (step.last_sync_at) return 'ok'
  return 'idle'
}

function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return 'nikdy'
  const now = Date.now()
  const then = new Date(isoDate).getTime()
  const diffSec = Math.floor((now - then) / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}
</script>

<template>
  <div class="table-container">
    <table class="steps-table">
      <thead>
        <tr>
          <th>Step</th>
          <th>IDO</th>
          <th>Status</th>
          <th>Last Sync</th>
          <th>C/U/E</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="step in steps" :key="step.id">
          <td>{{ step.step_name }}</td>
          <td class="font-mono text-xs">{{ step.ido_name }}</td>
          <td>
            <CheckCircle v-if="stepStatus(step) === 'ok'" :size="ICON_SIZE.SMALL" class="icon-ok" />
            <XCircle v-else-if="stepStatus(step) === 'error'" :size="ICON_SIZE.SMALL" class="icon-error" />
            <Clock v-else :size="ICON_SIZE.SMALL" class="icon-idle" />
          </td>
          <td class="text-xs text-secondary">{{ formatRelativeTime(step.last_sync_at) }}</td>
          <td class="font-mono text-xs">{{ step.created_count }}/{{ step.updated_count }}/{{ step.error_count }}</td>
          <td>
            <div class="action-buttons">
              <button
                @click="emit('trigger', step.step_name)"
                :disabled="triggeringStep === step.step_name"
                class="icon-btn icon-btn-sm"
                title="Trigger now"
              >
                <Play :size="ICON_SIZE.SMALL" />
              </button>
              <button
                @click="emit('toggle-enabled', step)"
                :class="['icon-btn', 'icon-btn-sm', { active: step.enabled }]"
                title="Toggle enabled"
              >
                <Power :size="ICON_SIZE.SMALL" />
              </button>
            </div>
          </td>
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

.steps-table {
  width: 100%;
  border-collapse: collapse;
}

.steps-table th {
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

.steps-table td {
  padding: 6px var(--pad);
  font-size: var(--fs);
  border-bottom: 1px solid var(--b1);
}

.steps-table tbody tr:hover {
  background: var(--b1);
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.icon-ok {
  color: var(--ok);
}

.icon-error {
  color: var(--err);
}

.icon-idle {
  color: var(--t3);
}
</style>
