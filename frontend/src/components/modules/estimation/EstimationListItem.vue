<template>
  <div
    class="part-item"
    :class="{ selected }"
    @click="$emit('click')"
  >
    <div class="part-header">
      <span class="filename">{{ record.filename }}</span>
      <span class="status-badge" :class="statusClass">
        {{ statusText }}
      </span>
    </div>
    <div v-if="record.estimated_time_min" class="part-time">
      <span class="time-value">{{ record.estimated_time_min.toFixed(1) }}</span>
      <span class="time-unit">min</span>
    </div>
    <div class="part-meta">
      <span class="meta-item">Vol: {{ formatNumber(record.part_volume_mm3) }} mm³</span>
      <span class="meta-item">Rem: {{ (record.removal_ratio * 100).toFixed(0) }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EstimationRecord } from '@/types/estimation'

interface Props {
  record: EstimationRecord
  selected: boolean
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'click'): void
}>()

const statusClass = computed(() => {
  if (props.record.actual_time_min) return 'verified'
  if (props.record.estimated_time_min) return 'estimated'
  return 'pending'
})

const statusText = computed(() => {
  if (props.record.actual_time_min) return 'Verified'
  if (props.record.estimated_time_min) return 'Estimated'
  return 'Pending'
})

function formatNumber(value: number): string {
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(1) + 'k'
  return value.toFixed(0)
}
</script>

<style scoped>
.part-item {
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.part-item:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.part-item.selected {
  background: var(--bg-accent);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.part-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.filename {
  font-weight: 500;
  color: var(--text-primary);
  font-size: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.status-badge.pending {
  background: var(--bg-warning);
  color: var(--color-warning);
}

.status-badge.estimated {
  background: var(--bg-info);
  color: var(--color-info);
}

.status-badge.verified {
  background: var(--bg-success);
  color: var(--color-success);
}

.part-time {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.time-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary);
}

.time-unit {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.part-meta {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.meta-item {
  display: inline-block;
}
</style>
