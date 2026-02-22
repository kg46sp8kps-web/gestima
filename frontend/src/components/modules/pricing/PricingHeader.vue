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
  gap: var(--pad);
  padding: 12px;
  border-bottom: 1px solid var(--b2);
  background: var(--surface);
}

.part-info {
  display: flex;
  align-items: center;
  gap: var(--pad);
}

.part-info h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.part-info h2.placeholder {
  color: var(--t3);
}

.part-badge {
  padding: 4px var(--pad);
  background: transparent;
  color: var(--t1);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}
</style>
