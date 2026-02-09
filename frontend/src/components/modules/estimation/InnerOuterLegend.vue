<template>
  <div class="inner-outer-legend">
    <h5>Surface Classification:</h5>
    <div class="legend-items">
      <div class="legend-item">
        <span class="color-box outer"></span>
        <span>Vnější plochy (outer surfaces)</span>
      </div>
      <div class="legend-item">
        <span class="color-box inner"></span>
        <span>Vnitřní plochy (inner/cavity surfaces)</span>
      </div>
    </div>
    <p v-if="innerRatio !== undefined" class="stat">
      Inner surface ratio: {{ (innerRatio * 100).toFixed(0) }}%
    </p>
    <p class="hint">
      Inner surface ratio = key proxy metric for part complexity
    </p>
  </div>
</template>

<script setup lang="ts">
interface Props {
  innerRatio?: number
}

defineProps<Props>()
</script>

<style scoped>
.inner-outer-legend {
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
}

.inner-outer-legend h5 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  font-weight: 600;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.color-box {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-default);
}

.color-box.outer {
  background: #4A90E2;
}

.color-box.inner {
  background: #E74C3C;
}

.stat {
  margin: var(--space-2) 0;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-style: italic;
}
</style>
