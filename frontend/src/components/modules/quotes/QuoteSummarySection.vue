<script setup lang="ts">
import { BarChart3 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Summary {
  total_items: number
  unique_parts: number
  matched_parts: number
  new_parts: number
  missing_batches: number
}

interface Props {
  summary: Summary
}

defineProps<Props>()
</script>

<template>
  <div class="summary-panel">
    <h2><BarChart3 :size="ICON_SIZE.STANDARD" class="section-icon" /> Přehled poptávky</h2>
    <div class="summary-grid">
      <div class="summary-item">
        <span class="summary-label">Celkem položek:</span>
        <span class="summary-value">{{ summary.total_items }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Unikátní díly:</span>
        <span class="summary-value">{{ summary.unique_parts }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Díly v DB:</span>
        <span class="summary-value success">{{ summary.matched_parts }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Nové díly:</span>
        <span class="summary-value warning">{{ summary.new_parts }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Chybějící kalkulace:</span>
        <span class="summary-value error">{{ summary.missing_batches }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary-panel {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.summary-panel h2 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.section-icon {
  display: inline;
  margin-right: var(--space-3);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.summary-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.summary-value {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.summary-value.success {
  color: var(--color-success);
}

.summary-value.warning {
  color: var(--palette-warning);
}

.summary-value.error {
  color: var(--color-danger);
}
</style>
