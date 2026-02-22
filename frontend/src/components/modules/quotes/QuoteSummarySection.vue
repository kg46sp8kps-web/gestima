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
  padding: 12px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.summary-panel h2 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--t1);
}

.section-icon {
  display: inline;
  margin-right: var(--pad);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--pad);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: var(--fs);
  color: var(--t3);
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.summary-value.success {
  color: var(--ok);
}

.summary-value.warning {
  color: var(--warn);
}

.summary-value.error {
  color: var(--err);
}
</style>
