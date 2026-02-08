<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  roughingMin: number
  finishingMin: number
  setupMin: number
  totalMin: number
}

const props = defineProps<Props>()

const roughingPercent = computed(() =>
  ((props.roughingMin / props.totalMin) * 100).toFixed(0)
)
const finishingPercent = computed(() =>
  ((props.finishingMin / props.totalMin) * 100).toFixed(0)
)
const setupPercent = computed(() =>
  ((props.setupMin / props.totalMin) * 100).toFixed(0)
)
</script>

<template>
  <div class="time-breakdown-widget">
    <h3>Time Breakdown</h3>
    <div class="breakdown-grid">
      <div class="breakdown-item roughing">
        <div class="breakdown-bar">
          <div class="bar-fill" :style="{ width: roughingPercent + '%' }"></div>
        </div>
        <div class="breakdown-content">
          <span class="label">Roughing</span>
          <span class="value">{{ roughingMin.toFixed(2) }} min</span>
          <span class="percent">{{ roughingPercent }}%</span>
        </div>
      </div>

      <div class="breakdown-item finishing">
        <div class="breakdown-bar">
          <div class="bar-fill" :style="{ width: finishingPercent + '%' }"></div>
        </div>
        <div class="breakdown-content">
          <span class="label">Finishing</span>
          <span class="value">{{ finishingMin.toFixed(2) }} min</span>
          <span class="percent">{{ finishingPercent }}%</span>
        </div>
      </div>

      <div class="breakdown-item setup">
        <div class="breakdown-bar">
          <div class="bar-fill" :style="{ width: setupPercent + '%' }"></div>
        </div>
        <div class="breakdown-content">
          <span class="label">Setup</span>
          <span class="value">{{ setupMin.toFixed(2) }} min</span>
          <span class="percent">{{ setupPercent }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-breakdown-widget {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.breakdown-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.breakdown-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.breakdown-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.breakdown-bar .bar-fill {
  height: 100%;
  transition: width var(--duration-normal) var(--ease-out);
}

.breakdown-item.roughing .bar-fill {
  background: var(--color-primary);
}

.breakdown-item.finishing .bar-fill {
  background: var(--color-success);
}

.breakdown-item.setup .bar-fill {
  background: var(--color-warning);
}

.breakdown-content {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: var(--space-3);
  align-items: baseline;
}

.breakdown-content .label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.breakdown-content .value {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.breakdown-content .percent {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
</style>
