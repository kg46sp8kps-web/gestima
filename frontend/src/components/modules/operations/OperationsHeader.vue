<script setup lang="ts">
/**
 * Operations Header Component
 * Displays part info and operations count
 */

import type { Part } from '@/types/part'

interface Props {
  part: Part | null
  operationsCount: number
}

defineProps<Props>()
</script>

<template>
  <div class="operations-header">
    <div v-if="part" class="part-info">
      <h2>{{ part.name }}</h2>
      <span class="part-badge">{{ part.part_number }}</span>
    </div>
    <div v-else class="part-info">
      <h2 class="placeholder">Vyberte díl</h2>
    </div>
    <div class="header-meta">
      <span class="count-badge">{{ operationsCount }} operací</span>
    </div>
  </div>
</template>

<style scoped>
.operations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.part-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.part-info h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.part-info h2.placeholder {
  color: var(--text-tertiary);
}

.part-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.count-badge {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}
</style>
