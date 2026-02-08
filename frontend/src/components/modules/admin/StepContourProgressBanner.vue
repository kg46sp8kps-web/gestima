<script setup lang="ts">
/**
 * Step Contour Progress Banner
 *
 * Progress indicator for batch STEP file processing
 */

import { computed } from 'vue'

interface Props {
  processedCount: number
  totalCount: number
}

const props = defineProps<Props>()

const progressPercent = computed(() => {
  if (props.totalCount === 0) return 0
  return Math.round((props.processedCount / props.totalCount) * 100)
})
</script>

<template>
  <div class="progress-banner">
    <div class="progress-content">
      <div class="spinner"></div>
      <span class="progress-text">
        Zpracování {{ processedCount }} / {{ totalCount }} souborů ({{ progressPercent }}%)
      </span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
    </div>
  </div>
</template>

<style scoped>
.progress-banner {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-color);
}

.progress-content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.progress-text {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.progress-bar {
  height: 4px;
  background: var(--bg-surface);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent-primary);
  transition: width 0.3s ease;
}
</style>
