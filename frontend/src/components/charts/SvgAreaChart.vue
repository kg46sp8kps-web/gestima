<script setup lang="ts">
import { computed } from 'vue'
import { formatMillions, calculateYTicks, roundToNice } from '@/composables/useChartUtils'

interface AreaSeries {
  label: string
  data: number[]
  color: string
}

const props = withDefaults(defineProps<{
  series: AreaSeries[]
  labels: string[]
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

// Calculate Y-axis max
const yMax = computed(() => {
  if (!props.series.length) return 100
  const allValues = props.series.flatMap(s => s.data)
  const max = Math.max(...allValues, 0)
  return roundToNice(max * 1.1) // Add 10% padding
})

const yTicks = computed(() => calculateYTicks(yMax.value, 5))

// Transform value to Y coordinate
function valueToY(value: number): number {
  if (yMax.value === 0) return CHART_HEIGHT.value
  return CHART_HEIGHT.value - (value / yMax.value) * CHART_HEIGHT.value
}

// Generate SVG path for line
function generateLinePath(data: number[]): string {
  if (!data.length) return ''

  const points = data.map((value, i) => {
    const x = (i / (data.length - 1 || 1)) * CHART_WIDTH
    const y = valueToY(value)
    return `${x},${y}`
  })

  return 'M' + points.join(' L')
}

// Generate SVG polygon for filled area
function generateAreaPath(data: number[]): string {
  if (!data.length) return ''

  const topPoints = data.map((value, i) => {
    const x = (i / (data.length - 1 || 1)) * CHART_WIDTH
    const y = valueToY(value)
    return `${x},${y}`
  })

  // Close path along bottom
  const bottomRight = `${CHART_WIDTH},${CHART_HEIGHT.value}`
  const bottomLeft = `0,${CHART_HEIGHT.value}`

  return `M0,${CHART_HEIGHT.value} L${topPoints.join(' L')} L${bottomRight} Z`
}

// X-axis label positions
const xLabelPositions = computed(() => {
  return props.labels.map((_, i) => {
    return (i / (props.labels.length - 1 || 1)) * CHART_WIDTH
  })
})
</script>

<template>
  <div class="svg-area-chart">
    <svg
      :viewBox="`0 0 ${WIDTH} ${height}`"
      preserveAspectRatio="xMidYMid meet"
      class="chart-svg"
    >
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
            v-for="(label, i) in labels"
            :key="`x-label-${i}`"
          >
            <text
              :x="xLabelPositions[i]"
              :y="CHART_HEIGHT + 20"
              text-anchor="middle"
              fill="var(--text-secondary)"
              font-size="11"
            >
              {{ label }}
            </text>
          </g>
        </g>

        <!-- Area fills -->
        <g class="areas">
          <path
            v-for="(s, i) in series"
            :key="`area-${i}`"
            :d="generateAreaPath(s.data)"
            :fill="s.color"
            opacity="0.2"
          >
            <title>{{ s.label }}</title>
          </path>
        </g>

        <!-- Lines -->
        <g class="lines">
          <path
            v-for="(s, i) in series"
            :key="`line-${i}`"
            :d="generateLinePath(s.data)"
            fill="none"
            :stroke="s.color"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <title>{{ s.label }}</title>
          </path>
        </g>

        <!-- Data points (circles) -->
        <g class="points">
          <g
            v-for="(s, seriesIdx) in series"
            :key="`points-${seriesIdx}`"
          >
            <circle
              v-for="(value, pointIdx) in s.data"
              :key="`point-${seriesIdx}-${pointIdx}`"
              :cx="(pointIdx / (s.data.length - 1 || 1)) * CHART_WIDTH"
              :cy="valueToY(value)"
              r="3"
              :fill="s.color"
              opacity="0.8"
            >
              <title>{{ labels[pointIdx] }} - {{ s.label }}: {{ formatValue(value) }}</title>
            </circle>
          </g>
        </g>
      </g>
    </svg>

    <!-- Legend -->
    <div v-if="showLegend && series.length" class="legend">
      <div
        v-for="(s, i) in series"
        :key="`legend-${i}`"
        class="legend-item"
      >
        <div class="legend-color" :style="{ backgroundColor: s.color }" />
        <span class="legend-label">{{ s.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-area-chart {
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
