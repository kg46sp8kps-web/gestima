<script setup lang="ts">
/**
 * Material Header Component
 * Displays part info and material summary
 */
import { computed } from 'vue'
import type { Part } from '@/types/part'
import type { MaterialInputWithOperations } from '@/types/material'
import { getStockShapeLabel } from '@/types/material'

interface Props {
  part: Part | null
  materialInputs: MaterialInputWithOperations[]
}

const props = defineProps<Props>()

const materialsCount = computed(() => props.materialInputs.length)
const primaryMaterial = computed(() => props.materialInputs[0] || null)
</script>

<template>
  <div class="material-header">
    <!-- Part Info -->
    <div v-if="part" class="part-info">
      <h2>{{ part.name }}</h2>
      <span class="part-badge">{{ part.part_number }}</span>
    </div>

    <!-- Material Summary -->
    <div v-if="materialsCount > 0" class="material-summary">
      <div class="summary-left">
        <span class="materials-count-badge">{{ materialsCount }} {{ materialsCount === 1 ? 'materiál' : 'materiálů' }}</span>
        <span v-if="primaryMaterial" class="material-type-badge">
          {{ getStockShapeLabel(primaryMaterial.stock_shape) }}
        </span>
      </div>
    </div>
    <div v-else class="empty-summary">
      <span class="empty-text">Žádné materiály</span>
    </div>
  </div>
</template>

<style scoped>
.material-header {
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

.part-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--palette-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.material-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.materials-count-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--palette-info);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.material-type-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--palette-secondary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.empty-summary {
  display: flex;
  align-items: center;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>
