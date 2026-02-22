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
      <span class="part-badge">{{ part.article_number || part.part_number }}</span>
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

.part-badge {
  padding: 4px var(--pad);
  background: var(--red);
  color: white;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}

.material-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.materials-count-badge {
  padding: 4px var(--pad);
  background: var(--t3);
  color: white;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}

.material-type-badge {
  padding: 4px var(--pad);
  background: var(--t3);
  color: white;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}

.empty-summary {
  display: flex;
  align-items: center;
}

.empty-text {
  font-size: var(--fs);
  color: var(--t3);
}
</style>
