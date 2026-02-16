<script setup lang="ts">
/**
 * Pricing Header Component
 * Displays part info and batch sets count
 */
import { computed } from 'vue'
import type { Part } from '@/types/part'
import type { BatchSet } from '@/types/batch'

interface Props {
  part: Part | null
  batchSets: BatchSet[]
}

const props = defineProps<Props>()

const frozenSetsCount = computed(() => {
  return props.batchSets.filter(s => s.status === 'frozen').length
})
</script>

<template>
  <div class="pricing-header">
    <!-- Part Info -->
    <div v-if="part" class="part-info">
      <h2>{{ part.name }}</h2>
      <span class="part-badge">{{ part.article_number || part.part_number }}</span>
    </div>
    <div v-else class="part-info">
      <h2 class="placeholder">Vyberte díl</h2>
    </div>
  </div>
</template>

<style scoped>
.pricing-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
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
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}
</style>
