<script setup lang="ts">
/**
 * Vision Status Bar - Displays refinement progress
 * LOC: ~70 (L-036 compliant)
 */

import { computed } from 'vue'
import { CheckCircle, AlertCircle } from 'lucide-vue-next'

const props = defineProps<{
  iteration: number
  error: number
  converged: boolean
  analyzing: boolean
  featureCount: number
}>()

const errorClass = computed(() => {
  if (props.error < 1) return 'success'
  if (props.error < 5) return 'warning'
  return 'danger'
})

const statusText = computed(() => {
  if (props.converged) return 'Converged'
  if (props.analyzing) return `Iterating... (${props.iteration})`
  return 'Ready'
})
</script>

<template>
  <div class="vision-status-bar">
    <div class="status-item">
      <span class="label">Status:</span>
      <span :class="['value', { 'text-success': converged, 'text-warning': analyzing }]">
        {{ statusText }}
      </span>
    </div>

    <div class="status-item">
      <span class="label">Iteration:</span>
      <span class="value mono">{{ iteration }}</span>
    </div>

    <div class="status-item">
      <span class="label">Error:</span>
      <span :class="['value', 'mono', `text-${errorClass}`]">
        {{ typeof error === 'number' ? error.toFixed(2) : error }}%
      </span>
      <CheckCircle v-if="typeof error === 'number' && error < 1" :size="16" class="icon-success" />
      <AlertCircle v-else-if="typeof error === 'number' && error > 10" :size="16" class="icon-danger" />
    </div>

    <div class="status-item">
      <span class="label">Features:</span>
      <span class="value mono">{{ featureCount }}</span>
    </div>
  </div>
</template>

<style scoped>
.vision-status-bar {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-item .label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.status-item .value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.status-item .value.mono {
  font-family: var(--font-mono);
}

.text-success {
  color: var(--color-success);
}

.text-warning {
  color: var(--color-warning);
}

.text-danger {
  color: var(--color-danger);
}

.icon-success {
  color: var(--color-success);
}

.icon-danger {
  color: var(--color-danger);
}

.mono {
  font-family: var(--font-mono);
}
</style>
