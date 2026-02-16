<script setup lang="ts">
/**
 * Operations Header Component
 * Displays part info, operations count, and AI time warning
 */

import type { Part } from '@/types/part'
import { Sparkles } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  part: Part | null
  operationsCount: number
  hasAIEstimation?: boolean
}

defineProps<Props>()
</script>

<template>
  <div class="operations-header">
    <div v-if="part" class="part-info">
      <h2>{{ part.name }}</h2>
      <span class="part-badge">{{ part.article_number || part.part_number }}</span>
    </div>
    <div v-else class="part-info">
      <h2 class="placeholder">Vyberte díl</h2>
    </div>
    <div class="header-meta">
      <span v-if="hasAIEstimation" class="ai-time-badge" title="Existuje AI odhad času">
        <Sparkles :size="ICON_SIZE.SMALL" />
        AI odhad
      </span>
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

.ai-time-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: rgba(139, 92, 246, 0.1);
  color: var(--brand-text);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.count-badge {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}
</style>
