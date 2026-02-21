<script setup lang="ts">
import { computed } from 'vue'
import { ChevronUp, ChevronDown } from 'lucide-vue-next'
import { sparklinePath } from '@/composables/useChartUtils'
import { ICON_SIZE } from '@/config/design'

type RagStatus = 'success' | 'warning' | 'danger'

interface Props {
  label: string
  value: string
  subLabel?: string
  changePct?: number | null
  changeLabel?: string
  sparklineData?: number[]
  status?: RagStatus | null
  statusLabel?: string
  invertChangeColor?: boolean
  targetValue?: string
}

const props = withDefaults(defineProps<Props>(), {
  changeLabel: 'YoY',
  invertChangeColor: false
})

const borderColor = computed(() => {
  if (!props.status) return 'var(--border-default)'
  const colorMap: Record<RagStatus, string> = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    danger: 'var(--color-danger)'
  }
  return colorMap[props.status]
})

const changeColor = computed(() => {
  if (props.changePct == null) return 'var(--text-tertiary)'
  const isPositive = props.changePct >= 0
  const shouldBeGreen = props.invertChangeColor ? !isPositive : isPositive
  return shouldBeGreen ? 'var(--color-success)' : 'var(--color-danger)'
})

const changeIcon = computed(() => {
  if (props.changePct == null) return null
  return props.changePct >= 0 ? ChevronUp : ChevronDown
})

const sparkPath = computed(() => {
  if (!props.sparklineData || props.sparklineData.length < 2) return ''
  return sparklinePath(props.sparklineData, 200, 30)
})

const statusColor = computed(() => {
  if (!props.status) return 'var(--text-tertiary)'
  const colorMap: Record<RagStatus, string> = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    danger: 'var(--color-danger)'
  }
  return colorMap[props.status]
})
</script>

<template>
  <div class="kpi-card" :style="{ borderLeftColor: borderColor }">
    <div class="kpi-header">
      <span class="kpi-label">{{ label }}</span>
      <div v-if="status" class="kpi-status">
        <span class="status-dot" :style="{ backgroundColor: statusColor }" />
        <span class="status-text" :style="{ color: statusColor }">{{ statusLabel }}</span>
      </div>
    </div>

    <div class="kpi-value-row">
      <div class="kpi-value-block">
        <span class="kpi-value">{{ value }}</span>
        <span v-if="subLabel" class="kpi-sub-label">{{ subLabel }}</span>
      </div>

      <div v-if="changePct != null" class="kpi-change">
        <component :is="changeIcon" v-if="changeIcon" :size="ICON_SIZE.SMALL" :style="{ color: changeColor }" />
        <span class="change-pct" :style="{ color: changeColor }">
          {{ Math.abs(changePct).toFixed(1) }} %
        </span>
        <span class="change-label">{{ changeLabel }}</span>
      </div>
    </div>

    <div v-if="sparkPath" class="kpi-sparkline">
      <svg width="100%" height="30" viewBox="0 0 200 30" preserveAspectRatio="none">
        <path
          :d="sparkPath"
          fill="none"
          :stroke="statusColor"
          stroke-width="1.5"
          opacity="0.7"
        />
      </svg>
    </div>

    <div v-if="targetValue" class="kpi-target">
      {{ targetValue }}
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-left-width: 4px;
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.kpi-card:hover {
  background: var(--bg-raised);
}

.kpi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.kpi-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.kpi-status {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.kpi-value-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
}

.kpi-value-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-0\.5);
}

.kpi-value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  font-family: var(--font-mono);
  line-height: 1.2;
}

.kpi-sub-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.kpi-change {
  display: flex;
  align-items: center;
  gap: var(--space-0\.5);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  white-space: nowrap;
}

.change-pct {
  font-family: var(--font-mono);
}

.change-label {
  color: var(--text-tertiary);
  margin-left: 2px;
}

.kpi-sparkline {
  width: 100%;
  height: 30px;
  margin-top: var(--space-1);
}

.kpi-target {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-1);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
}
</style>
