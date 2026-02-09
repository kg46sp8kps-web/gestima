<template>
  <section class="similar-widget">
    <div class="section-header">
      <h4 class="section-title">Similar Parts ({{ similarParts.length }})</h4>
      <button v-if="loading" class="refresh-btn" disabled>
        Loading...
      </button>
      <button v-else class="refresh-btn" @click="$emit('refresh')">
        Refresh
      </button>
    </div>
    <ul class="similar-list">
      <li v-for="sim in similarParts" :key="sim.id" class="similar-item">
        <span class="similar-name">{{ sim.filename }}</span>
        <div class="similar-meta">
          <span v-if="sim.estimated_time_min" class="similar-time">
            {{ sim.estimated_time_min.toFixed(1) }} min
          </span>
          <span class="similar-score">
            {{ (sim.similarity_score * 100).toFixed(0) }}% similar
          </span>
        </div>
      </li>
    </ul>
    <p v-if="suggestedTime" class="hint">
      Typical time: {{ suggestedTime }} minutes
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SimilarPart } from '@/types/estimation'

interface Props {
  similarParts: SimilarPart[]
  loading: boolean
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'refresh'): void
}>()

const suggestedTime = computed(() => {
  const withEstimates = props.similarParts.filter(s => s.estimated_time_min)
  if (withEstimates.length === 0) return null

  const times = withEstimates.map(s => s.estimated_time_min!)
  const avg = times.reduce((sum, t) => sum + t, 0) / times.length
  const min = Math.min(...times)
  const max = Math.max(...times)

  return `${min.toFixed(1)} - ${max.toFixed(1)} (avg: ${avg.toFixed(1)})`
})
</script>

<style scoped>
.similar-widget {
  margin-bottom: var(--space-5);
}

.section-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.refresh-btn {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.refresh-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.similar-list {
  margin: 0 0 var(--space-3) 0;
  padding: 0;
  list-style: none;
}

.similar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.similar-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.similar-meta {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-xs);
}

.similar-time {
  font-weight: 600;
  color: var(--color-primary);
}

.similar-score {
  color: var(--text-muted);
}

.hint {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-info);
  color: var(--color-info);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  margin: 0;
}
</style>
