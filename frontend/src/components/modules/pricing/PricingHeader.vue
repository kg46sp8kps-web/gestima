<script setup lang="ts">
/**
 * Pricing Header Component
 * Displays part info and batch pricing summary
 */
import { computed } from 'vue'
import type { Part } from '@/types/part'
import type { Batch } from '@/types/batch'

interface Props {
  part: Part | null
  batches: Batch[]
}

const props = defineProps<Props>()

const batchesCount = computed(() => props.batches.length)

const minUnitPrice = computed(() => {
  if (props.batches.length === 0) return null
  return Math.min(...props.batches.map(b => b.unit_price))
})

const maxUnitPrice = computed(() => {
  if (props.batches.length === 0) return null
  return Math.max(...props.batches.map(b => b.unit_price))
})

const defaultBatch = computed(() => {
  return props.batches.find(b => b.is_default) || null
})

function formatCurrency(amount: number | null): string {
  if (amount === null) return '-'
  return amount.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="pricing-header">
    <!-- Part Info -->
    <div v-if="part" class="part-info">
      <h2>{{ part.name }}</h2>
      <span class="part-badge">{{ part.part_number }}</span>
    </div>
    <div v-else class="part-info">
      <h2 class="placeholder">Vyberte díl</h2>
    </div>

    <!-- Batch Summary -->
    <div v-if="batchesCount > 0" class="batch-summary">
      <div class="summary-stat">
        <span class="stat-label">Počet dávek:</span>
        <span class="stat-value">{{ batchesCount }}</span>
      </div>
      <div v-if="minUnitPrice !== null" class="summary-stat">
        <span class="stat-label">Min. cena/ks:</span>
        <span class="stat-value">{{ formatCurrency(minUnitPrice) }} Kč</span>
      </div>
      <div v-if="maxUnitPrice !== null" class="summary-stat">
        <span class="stat-label">Max. cena/ks:</span>
        <span class="stat-value">{{ formatCurrency(maxUnitPrice) }} Kč</span>
      </div>
      <div v-if="defaultBatch" class="summary-stat">
        <span class="stat-label">Výchozí:</span>
        <span class="stat-value">{{ defaultBatch.quantity }} ks</span>
      </div>
    </div>
    <div v-else class="empty-summary">
      <span class="empty-text">Žádné cenové dávky</span>
    </div>
  </div>
</template>

<style scoped>
.pricing-header {
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
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.batch-summary {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
}

.summary-stat {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.stat-label {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.stat-value {
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  color: var(--text-primary);
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
