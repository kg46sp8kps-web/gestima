<script setup lang="ts">
import { computed } from 'vue'
import { formatMillions, calculateYTicks, roundToNice } from '@/composables/useChartUtils'

interface BarGroup {
  label: string
  values: { key: string; value: number; color: string }[]
  ghostValues?: { key: string; value: number; color: string }[]
}

const props = withDefaults(defineProps<{
  data: BarGroup[]
  height?: number
  showLegend?: boolean
  formatValue?: (v: number) => string
}>(), {
  height: 300,
  showLegend: true,
  formatValue: formatMillions
})

const MARGIN = { top: 20, right: 20, bottom: 40, left: 60 }
const WIDTH = 600
const CHART_WIDTH = WIDTH - MARGIN.left - MARGIN.right
const CHART_HEIGHT = computed(() => props.height - MARGIN.top - MARGIN.bottom)

// Calculate Y-axis max and ticks
const yMax = computed(() => {
  if (!props.data.length) return 100
  const allValues = props.data.flatMap(g => g.values.map(v => v.value))
  const max = Math.max(...allValues, 0)
  return roundToNice(max * 1.1) // Add 10% padding
})

const yTicks = computed(() => calculateYTicks(yMax.value, 5))

// Calculate bar positions
const barGroupWidth = computed(() => {
  if (!props.data.length) return 0
  return CHART_WIDTH / props.data.length
})

const barWidth = computed(() => {
  if (!props.data.length) return 0
  const maxBarsInGroup = Math.max(...props.data.map(g => g.values.length))
  return (barGroupWidth.value * 0.7) / maxBarsInGroup // 70% of group width for bars
})

const barGap = computed(() => barGroupWidth.value * 0.05) // 5% gap

// Legend items (unique keys)
const legendItems = computed(() => {
  const keysSet = new Set<string>()
  const items: { key: string; color: string }[] = []

  props.data.forEach(group => {
    group.values.forEach(v => {
      if (!keysSet.has(v.key)) {
        keysSet.add(v.key)
        items.push({ key: v.key, color: v.color })
      }
    })
  })

  return items
})

// Transform value to Y coordinate
function valueToY(value: number): number {
  if (yMax.value === 0) return CHART_HEIGHT.value
  return CHART_HEIGHT.value - (value / yMax.value) * CHART_HEIGHT.value
}

// Calculate bar X position within group
function getBarX(groupIndex: number, barIndex: number): number {
  const group = props.data[groupIndex]
  if (!group) return 0
  const groupX = groupIndex * barGroupWidth.value
  const barOffset = barIndex * (barWidth.value + barGap.value)
  return groupX + (barGroupWidth.value - group.values.length * (barWidth.value + barGap.value)) / 2 + barOffset
}
</script>

<template>
  <div class="svg-bar-chart">
    <svg
      :viewBox="`0 0 ${WIDTH} ${height}`"
      preserveAspectRatio="xMidYMid meet"
      class="chart-svg"
    >
      <defs>
        <linearGradient id="grid-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:var(--border-subtle);stop-opacity:0.5" />
          <stop offset="100%" style="stop-color:var(--border-subtle);stop-opacity:0" />
        </linearGradient>
      </defs>

      <g :transform="`translate(${MARGIN.left}, ${MARGIN.top})`">
        <!-- Grid lines (horizontal) -->
        <g class="grid">
          <line
            v-for="(tick, i) in yTicks"
            :key="`grid-${i}`"
            :x1="0"
            :x2="CHART_WIDTH"
            :y1="valueToY(tick)"
            :y2="valueToY(tick)"
            stroke="var(--border-subtle)"
            stroke-width="1"
            stroke-dasharray="2,4"
          />
        </g>

        <!-- Y-axis -->
        <g class="y-axis">
          <line
            :x1="0"
            :y1="0"
            :x2="0"
            :y2="CHART_HEIGHT"
            stroke="var(--border-default)"
            stroke-width="1"
          />
          <g
            v-for="(tick, i) in yTicks"
            :key="`y-tick-${i}`"
          >
            <text
              :x="-8"
              :y="valueToY(tick)"
              text-anchor="end"
              dominant-baseline="middle"
              fill="var(--text-secondary)"
              font-size="10"
              font-family="var(--font-mono)"
            >
              {{ formatValue(tick) }}
            </text>
          </g>
        </g>

        <!-- X-axis -->
        <g class="x-axis">
          <line
            :x1="0"
            :y1="CHART_HEIGHT"
            :x2="CHART_WIDTH"
            :y2="CHART_HEIGHT"
            stroke="var(--border-default)"
            stroke-width="1"
          />
          <g
            v-for="(group, i) in data"
            :key="`x-label-${i}`"
          >
            <text
              :x="i * barGroupWidth + barGroupWidth / 2"
              :y="CHART_HEIGHT + 20"
              text-anchor="middle"
              fill="var(--text-secondary)"
              font-size="11"
            >
              {{ group.label }}
            </text>
          </g>
        </g>

        <!-- Bars -->
        <g class="bars">
          <g
            v-for="(group, groupIdx) in data"
            :key="`group-${groupIdx}`"
            class="bar-group"
          >
            <!-- Ghost bars (previous year, semi-transparent) -->
            <g v-if="group.ghostValues?.length" class="ghost-bars">
              <rect
                v-for="(ghost, ghostIdx) in group.ghostValues"
                :key="`ghost-${groupIdx}-${ghostIdx}`"
                :x="getBarX(groupIdx, ghostIdx)"
                :y="valueToY(ghost.value)"
                :width="barWidth"
                :height="CHART_HEIGHT - valueToY(ghost.value)"
                :fill="ghost.color"
                opacity="0.15"
                rx="2"
                :stroke="ghost.color"
                stroke-width="1"
                stroke-dasharray="4,2"
              >
                <title>{{ group.label }} - {{ ghost.key }}: {{ formatValue(ghost.value) }}</title>
              </rect>
            </g>
            <!-- Current bars -->
            <g
              v-for="(bar, barIdx) in group.values"
              :key="`bar-${groupIdx}-${barIdx}`"
            >
              <rect
                :x="getBarX(groupIdx, barIdx)"
                :y="valueToY(bar.value)"
                :width="barWidth"
                :height="CHART_HEIGHT - valueToY(bar.value)"
                :fill="bar.color"
                opacity="0.9"
                rx="2"
              >
                <title>{{ group.label }} - {{ bar.key }}: {{ formatValue(bar.value) }}</title>
              </rect>
            </g>
          </g>
        </g>
      </g>
    </svg>

    <!-- Legend -->
    <div v-if="showLegend && legendItems.length" class="legend">
      <div
        v-for="item in legendItems"
        :key="item.key"
        class="legend-item"
      >
        <div class="legend-color" :style="{ backgroundColor: item.color }" />
        <span class="legend-label">{{ item.key }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-bar-chart {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chart-svg {
  width: 100%;
  height: auto;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  justify-content: center;
  padding: var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-sm);
}

.legend-label {
  font-weight: var(--font-medium);
}
</style>
