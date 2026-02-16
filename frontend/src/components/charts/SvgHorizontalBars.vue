<script setup lang="ts">
import { computed } from 'vue'
import { formatCzk, CHART_COLORS } from '@/composables/useChartUtils'

interface HBarItem {
  label: string
  value: number
  color?: string
}

const props = withDefaults(defineProps<{
  items: HBarItem[]
  maxItems?: number
  formatValue?: (v: number) => string
}>(), {
  maxItems: 10,
  formatValue: formatCzk
})

const LABEL_WIDTH = 120
const VALUE_WIDTH = 100
const BAR_HEIGHT = 24
const BAR_GAP = 4

// Limit items and sort by value descending
const displayItems = computed(() => {
  return [...props.items]
    .sort((a, b) => b.value - a.value)
    .slice(0, props.maxItems)
    .map((item, idx) => ({
      ...item,
      color: item.color || CHART_COLORS[idx % CHART_COLORS.length]
    }))
})

const maxValue = computed(() => {
  if (!displayItems.value.length) return 100
  return Math.max(...displayItems.value.map(i => i.value), 1)
})

const totalHeight = computed(() => {
  return displayItems.value.length * (BAR_HEIGHT + BAR_GAP)
})

const WIDTH = 600
const BAR_MAX_WIDTH = WIDTH - LABEL_WIDTH - VALUE_WIDTH - 40

function getBarWidth(value: number): number {
  return (value / maxValue.value) * BAR_MAX_WIDTH
}
</script>

<template>
  <div class="svg-horizontal-bars">
    <svg
      :viewBox="`0 0 ${WIDTH} ${totalHeight}`"
      preserveAspectRatio="xMidYMid meet"
      class="bars-svg"
    >
      <g
        v-for="(item, idx) in displayItems"
        :key="`bar-${idx}`"
        :transform="`translate(0, ${idx * (BAR_HEIGHT + BAR_GAP)})`"
        class="bar-row"
      >
        <!-- Label (left) -->
        <text
          :x="LABEL_WIDTH - 8"
          :y="BAR_HEIGHT / 2"
          text-anchor="end"
          dominant-baseline="middle"
          fill="var(--text-body)"
          font-size="11"
          font-weight="500"
        >
          {{ item.label }}
        </text>

        <!-- Bar background -->
        <rect
          :x="LABEL_WIDTH"
          :y="2"
          :width="BAR_MAX_WIDTH"
          :height="BAR_HEIGHT - 4"
          fill="var(--bg-surface)"
          rx="2"
        />

        <!-- Bar (colored) -->
        <rect
          :x="LABEL_WIDTH"
          :y="2"
          :width="getBarWidth(item.value)"
          :height="BAR_HEIGHT - 4"
          :fill="item.color"
          opacity="0.9"
          rx="2"
        >
          <title>{{ item.label }}: {{ formatValue(item.value) }}</title>
        </rect>

        <!-- Value (right) -->
        <text
          :x="LABEL_WIDTH + BAR_MAX_WIDTH + 8"
          :y="BAR_HEIGHT / 2"
          text-anchor="start"
          dominant-baseline="middle"
          fill="var(--text-secondary)"
          font-size="10"
          font-family="var(--font-mono)"
          font-weight="600"
        >
          {{ formatValue(item.value) }}
        </text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.svg-horizontal-bars {
  width: 100%;
}

.bars-svg {
  width: 100%;
  height: auto;
}

.bar-row {
  transition: opacity var(--duration-fast);
}

.bar-row:hover {
  opacity: 0.9;
}
</style>
