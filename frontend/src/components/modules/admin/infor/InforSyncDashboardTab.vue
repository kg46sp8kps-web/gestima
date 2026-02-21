<script setup lang="ts">
/**
 * Infor Sync Dashboard Tab
 *
 * Real-time dashboard for automatic Infor sync pipeline.
 * Shows sync daemon status, step states, and recent logs.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { getSyncStatus, getSyncLogs, triggerSyncStep, updateSyncStep, startSync, stopSync } from '@/api/infor-sync'
import { useUiStore } from '@/stores/ui'
import { Play, Square, RefreshCw } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { SyncState, SyncLog } from '@/types/infor-sync'
import SyncStepsTable from './SyncStepsTable.vue'
import SyncLogsTable from './SyncLogsTable.vue'

const uiStore = useUiStore()

const running = ref(false)
const steps = ref<SyncState[]>([])
const logs = ref<SyncLog[]>([])
const loading = ref(false)
const triggeringStep = ref<string | null>(null)
const refreshInterval = ref<number | null>(null)

async function loadStatus() {
  try {
    const status = await getSyncStatus()
    running.value = status.running
    steps.value = status.steps
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba načtení stavu: ' + (err.message || 'Neznámá chyba'))
  }
}

async function loadLogs() {
  try {
    logs.value = await getSyncLogs(50)
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba načtení logů: ' + (err.message || 'Neznámá chyba'))
  }
}

async function refresh() {
  loading.value = true
  await Promise.all([loadStatus(), loadLogs()])
  loading.value = false
}

async function handleStart() {
  try {
    await startSync()
    uiStore.showSuccess('Sync daemon spuštěn')
    await refresh()
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba při spuštění: ' + (err.message || 'Neznámá chyba'))
  }
}

async function handleStop() {
  try {
    await stopSync()
    uiStore.showSuccess('Sync daemon zastaven')
    await refresh()
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba při zastavení: ' + (err.message || 'Neznámá chyba'))
  }
}

async function handleTrigger(stepName: string) {
  triggeringStep.value = stepName
  try {
    const result = await triggerSyncStep(stepName)
    uiStore.showSuccess(`${stepName}: ${result.created}C / ${result.updated}U / ${result.errors}E`)
    await refresh()
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba triggeru: ' + (err.message || 'Neznámá chyba'))
  } finally {
    triggeringStep.value = null
  }
}

async function handleToggleEnabled(step: SyncState) {
  try {
    await updateSyncStep(step.step_name, { enabled: !step.enabled })
    uiStore.showSuccess(`${step.step_name} ${!step.enabled ? 'zapnuto' : 'vypnuto'}`)
    await loadStatus()
  } catch (error: unknown) {
    const err = error as { message?: string }
    uiStore.showError('Chyba při změně: ' + (err.message || 'Neznámá chyba'))
  }
}

onMounted(() => {
  refresh()
  refreshInterval.value = window.setInterval(refresh, 2000)
})

onUnmounted(() => {
  if (refreshInterval.value !== null) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<template>
  <div class="sync-dashboard">
    <div class="status-header">
      <div class="status-indicator">
        <span v-if="running" class="badge badge-running">
          <span class="badge-dot badge-dot-ok"></span>
          Running
        </span>
        <span v-else class="badge badge-stopped">
          <span class="badge-dot badge-dot-neutral"></span>
          Stopped
        </span>
      </div>
      <div class="header-actions">
        <button @click="refresh" :disabled="loading" class="icon-btn">
          <RefreshCw :size="ICON_SIZE.STANDARD" :class="{ spin: loading }" />
        </button>
        <button v-if="!running" @click="handleStart" class="btn-primary btn-sm">
          <Play :size="ICON_SIZE.SMALL" /> Start
        </button>
        <button v-else @click="handleStop" class="btn-secondary btn-sm">
          <Square :size="ICON_SIZE.SMALL" /> Stop
        </button>
      </div>
    </div>

    <div class="section">
      <h4>Pipeline Steps</h4>
      <SyncStepsTable
        :steps="steps"
        :triggering-step="triggeringStep"
        @trigger="handleTrigger"
        @toggle-enabled="handleToggleEnabled"
      />
    </div>

    <div class="section">
      <h4>Recent Logs (last 50)</h4>
      <SyncLogsTable :logs="logs" />
    </div>
  </div>
</template>

<style scoped>
.sync-dashboard {
  padding: var(--space-4);
  overflow-y: auto;
  height: 100%;
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.badge-running {
  color: var(--color-success);
}

.badge-stopped {
  color: var(--text-tertiary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section {
  margin-bottom: var(--space-6);
}

h4 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
