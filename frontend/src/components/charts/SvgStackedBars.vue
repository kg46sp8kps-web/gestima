<script setup lang="ts">
import { computed } from 'vue'
import { formatMillions, calculateYTicks, roundToNice } from '@/composables/useChartUtils'

interface StackedGroup {
  label: string
  segments: { key: string; value: number; color: string }[]
}

interface KeyDefinition {
  key: string
  label: string
  color: string
}

const props = withDefaults(defineProps<{
  data: StackedGroup[]
  height?: number
  showLegend?: boolean
  keys: KeyDefinition[]
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

// Calculate Y-axis max (max stack total)
const yMax = computed(() => {
  if (!props.data.length) return 100
  const stackTotals = props.data.map(g =>
    g.segments.reduce((sum, s) => sum + s.value, 0)
  )
  const max = Math.max(...stackTotals, 0)
  return roundToNice(max * 1.1) // Add 10% padding
})

const yTicks = computed(() => calculateYTicks(yMax.value, 5))

// Bar dimensions
const barWidth = computed(() => {
  if (!props.data.length) return 0
  const totalGaps = (props.data.length + 1) * 0.1 * CHART_WIDTH / props.data.length
  return (CHART_WIDTH - totalGaps) / props.data.length
})

const barGap = computed(() => barWidth.value * 0.1)

// Transform value to Y coordinate
function valueToY(value: number): number {
  if (yMax.value === 0) return CHART_HEIGHT.value
  return CHART_HEIGHT.value - (value / yMax.value) * CHART_HEIGHT.value
}

// Calculate stacked segments for each bar
const stackedBars = computed(() => {
  return props.data.map((group, groupIdx) => {
    let cumulativeY = 0
    const segments = group.segments.map(seg => {
      const segmentHeight = (seg.value / yMax.value) * CHART_HEIGHT.value
      const y = CHART_HEIGHT.value - cumulativeY - segmentHeight
      cumulativeY += segmentHeight

      return {
        key: seg.key,
        color: seg.color,
        value: seg.value,
        x: groupIdx * (barWidth.value + barGap.value) + barGap.value,
        y,
        height: segmentHeight
      }
    })

    return {
      label: group.label,
      segments,
      total: group.segments.reduce((sum, s) => sum + s.value, 0)
    }
  })
})
</script>

<template>
  <div class="svg-stacked-bars">
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
            stroke="var(--b1)"
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
            stroke="var(--b2)"
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
              fill="var(--t3)"
              font-size="10"
              font-family="var(--mono)"
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
            stroke="var(--b2)"
            stroke-width="1"
          />
          <g
            v-for="(bar, i) in stackedBars"
            :key="`x-label-${i}`"
          >
            <text
              :x="(bar.segments[0]?.x ?? 0) + barWidth / 2"
              :y="CHART_HEIGHT + 20"
              text-anchor="middle"
              fill="var(--t3)"
              font-size="11"
            >
              {{ bar.label }}
            </text>
          </g>
        </g>

        <!-- Stacked bars -->
        <g class="bars">
          <g
            v-for="(bar, barIdx) in stackedBars"
            :key="`bar-${barIdx}`"
            class="bar-stack"
          >
            <rect
              v-for="(seg, segIdx) in bar.segments"
              :key="`seg-${barIdx}-${segIdx}`"
              :x="seg.x"
              :y="seg.y"
              :width="barWidth"
              :height="seg.height"
              :fill="seg.color"
              opacity="0.9"
              :rx="segIdx === 0 ? 0 : segIdx === bar.segments.length - 1 ? 2 : 0"
            >
              <title>{{ bar.label }} - {{ seg.key }}: {{ formatValue(seg.value) }}</title>
            </rect>
          </g>
        </g>
      </g>
    </svg>

    <!-- Legend -->
    <div v-if="showLegend && keys.length" class="legend">
      <div
        v-for="keyDef in keys"
        :key="keyDef.key"
        class="legend-item"
      >
        <div class="legend-color" :style="{ backgroundColor: keyDef.color }" />
        <span class="legend-label">{{ keyDef.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-stacked-bars {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.chart-svg {
  width: 100%;
  height: auto;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--pad);
  justify-content: center;
  padding: 6px;
  background: var(--surface);
  border-radius: var(--r);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  color: var(--t3);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: var(--rs);
}

.legend-label {
  font-weight: 500;
}
</style>
