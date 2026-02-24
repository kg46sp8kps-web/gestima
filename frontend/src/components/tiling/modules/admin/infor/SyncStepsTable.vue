<script setup lang="ts">
/**
 * Sync Steps Table
 *
 * Displays pipeline steps with status and actions.
 */

import { Play, Power, CheckCircle, XCircle, Clock } from 'lucide-vue-next'
import { ICON_SIZE_SM } from '@/config/design'
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
  <div class="ot-wrap">
    <table class="ot">
      <thead>
        <tr>
          <th>Krok</th>
          <th>IDO</th>
          <th>Stav</th>
          <th>Poslední sync</th>
          <th>V/A/Ch</th>
          <th>Akce</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="step in steps" :key="step.id">
          <td>{{ step.step_name }}</td>
          <td class="cell-mono">{{ step.ido_name }}</td>
          <td>
            <CheckCircle v-if="stepStatus(step) === 'ok'" :size="ICON_SIZE_SM" class="icon-ok" />
            <XCircle v-else-if="stepStatus(step) === 'error'" :size="ICON_SIZE_SM" class="icon-error" />
            <Clock v-else :size="ICON_SIZE_SM" class="icon-idle" />
          </td>
          <td class="cell-time">{{ formatRelativeTime(step.last_sync_at) }}</td>
          <td class="cell-mono">{{ step.created_count }}/{{ step.updated_count }}/{{ step.error_count }}</td>
          <td>
            <div class="action-buttons">
              <button
                @click="emit('trigger', step.step_name)"
                :disabled="triggeringStep === step.step_name"
                class="icon-btn icon-btn-sm"
                title="Spustit"
              >
                <Play :size="ICON_SIZE_SM" />
              </button>
              <button
                @click="emit('toggle-enabled', step)"
                :class="['icon-btn', 'icon-btn-sm', { active: step.enabled }]"
                title="Povolit/zakázat"
              >
                <Power :size="ICON_SIZE_SM" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.ot-wrap { overflow-y: auto; max-height: 320px; border: 1px solid var(--b2); border-radius: var(--r); }

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

.cell-mono {
  font-size: var(--fsm);
  color: var(--t2);
}

.cell-time {
  font-size: var(--fsm);
  color: var(--t3);
}
</style>
