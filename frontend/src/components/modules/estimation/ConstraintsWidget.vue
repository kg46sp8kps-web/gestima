<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  constraints: string[]
  multiplier: number
}

const props = defineProps<Props>()

const severity = computed(() => {
  if (props.multiplier >= 2.0) return 'critical'
  if (props.multiplier >= 1.5) return 'warning'
  return 'moderate'
})

function formatConstraint(constraint: string): string {
  return constraint
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
</script>

<template>
  <div class="constraints-widget" :class="severity">
    <h3>
      <AlertTriangle :size="ICON_SIZE.STANDARD" />
      Machining Constraints
    </h3>
    <div class="constraint-multiplier">
      <span class="multiplier-label">Penalty Multiplier:</span>
      <span class="multiplier-value">{{ multiplier.toFixed(2) }}x</span>
    </div>
    <ul class="constraint-list">
      <li v-for="(constraint, i) in constraints" :key="i">
        {{ formatConstraint(constraint) }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.constraints-widget {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  border-left: 3px solid var(--border-default);
}

.constraints-widget.moderate {
  border-left-color: var(--color-info);
}

.constraints-widget.warning {
  border-left-color: var(--color-warning);
}

.constraints-widget.critical {
  border-left-color: var(--color-danger);
}

h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.constraint-multiplier {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.multiplier-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.multiplier-value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-warning);
  font-family: var(--font-mono);
}

.constraints-widget.critical .multiplier-value {
  color: var(--color-danger);
}

.constraint-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.constraint-list li {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--text-body);
}
</style>
