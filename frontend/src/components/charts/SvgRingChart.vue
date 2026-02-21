<script setup lang="ts">
import { computed } from 'vue'
import { formatMillions } from '@/composables/useChartUtils'

interface RingSegment {
  label: string
  value: number
  color: string
}

const props = withDefaults(defineProps<{
  segments: RingSegment[]
  size?: number
  thickness?: number
  centerLabel?: string
  centerSub?: string
  formatValue?: (v: number) => string
}>(), {
  size: 200,
  thickness: 30,
  formatValue: formatMillions
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.thickness) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const total = computed(() => props.segments.reduce((sum, s) => sum + s.value, 0))

// Calculate segment paths using stroke-dasharray technique
const segmentPaths = computed(() => {
  if (total.value === 0) return []

  let currentOffset = -circumference.value / 4 // Start at top (-90deg)

  return props.segments.map(segment => {
    const dashLength = (segment.value / total.value) * circumference.value
    const path = {
      color: segment.color,
      dasharray: `${dashLength} ${circumference.value}`,
      dashoffset: currentOffset,
      label: segment.label,
      value: segment.value,
      percentage: ((segment.value / total.value) * 100).toFixed(1)
    }
    currentOffset -= dashLength
    return path
  })
})
</script>

<template>
  <div class="svg-ring-chart">
    <svg
      :width="size"
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      class="ring-svg"
    >
      <!-- Background circle -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="'var(--bg-raised)'"
        :stroke-width="thickness"
      />

      <!-- Segment circles (using stroke-dasharray) -->
      <circle
        v-for="(seg, i) in segmentPaths"
        :key="`segment-${i}`"
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="seg.color"
        :stroke-width="thickness"
        :stroke-dasharray="seg.dasharray"
        :stroke-dashoffset="seg.dashoffset"
        stroke-linecap="butt"
        opacity="0.9"
      >
        <title>{{ seg.label }}: {{ formatValue(seg.value) }} ({{ seg.percentage }}%)</title>
      </circle>

      <!-- Center text -->
      <g v-if="centerLabel || centerSub" class="center-text">
        <text
          :x="center"
          :y="centerSub ? center - 8 : center"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="var(--text-primary)"
          font-size="20"
          font-weight="700"
          font-family="var(--font-mono)"
        >
          {{ centerLabel }}
        </text>
        <text
          v-if="centerSub"
          :x="center"
          :y="center + 12"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="var(--text-secondary)"
          font-size="10"
          font-weight="500"
        >
          {{ centerSub }}
        </text>
      </g>
    </svg>

    <!-- Legend -->
    <div v-if="segments.length" class="legend">
      <div
        v-for="(seg, i) in segments"
        :key="`legend-${i}`"
        class="legend-item"
      >
        <div class="legend-color" :style="{ backgroundColor: seg.color }" />
        <div class="legend-text">
          <span class="legend-label">{{ seg.label }}</span>
          <span class="legend-value">{{ formatValue(seg.value) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-ring-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.ring-svg {
  /* Rotate -90deg so first segment starts at top */
  transform: rotate(-90deg);
}

.legend {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
  max-width: 300px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  transition: background var(--duration-fast);
}

.legend-item:hover {
  background: var(--bg-raised);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.legend-text {
  display: flex;
  justify-content: space-between;
  flex: 1;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.legend-label {
  color: var(--text-body);
  font-weight: var(--font-medium);
}

.legend-value {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
}
</style>
