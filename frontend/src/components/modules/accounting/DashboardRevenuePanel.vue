<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DashboardRevenueResponse } from '@/types/accounting'
import SvgRingChart from '@/components/charts/SvgRingChart.vue'
import SvgAreaChart from '@/components/charts/SvgAreaChart.vue'
import { formatMillions, MONTH_SHORT, CHART_COLORS } from '@/composables/useChartUtils'

const props = defineProps<{ data: DashboardRevenueResponse }>()

const colors = ref<string[]>([])
onMounted(() => {
  const s = getComputedStyle(document.documentElement)
  colors.value = [
    s.getPropertyValue('--chart-revenue').trim(),
    s.getPropertyValue('--chart-profit').trim(),
    s.getPropertyValue('--chart-cooperation').trim(),
  ]
})

const ringSegments = computed(() =>
  props.data.streams.map((stream, idx) => {
    const color = (colors.value[idx] || CHART_COLORS[idx % CHART_COLORS.length]) as string
    return {
      label: stream.category,
      value: stream.total,
      color
    }
  })
)

const areaSeries = computed(() => {
  if (!colors.value.length) return []
  return props.data.streams.map((stream, idx) => {
    const color = (colors.value[idx] || CHART_COLORS[idx % CHART_COLORS.length]) as string
    return {
      label: stream.category,
      data: stream.monthly,
      color
    }
  })
})

const monthLabels = computed(() =>
  Array.from({ length: 12 }, (_, i) => MONTH_SHORT[i] ?? '')
)
</script>

<template>
  <div class="revenue-panel">
    <div class="row-layout">
      <div class="chart-card">
        <h3 class="chart-title">Tržby podle proudů</h3>
        <SvgRingChart
          :segments="ringSegments"
          :size="260"
          :center-label="formatMillions(data.ytd_total)"
          center-sub="Celkem"
          :format-value="formatMillions"
        />
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Měsíční vývoj tržeb</h3>
        <SvgAreaChart
          v-if="areaSeries.length"
          :series="areaSeries"
          :labels="monthLabels"
          :height="320"
          :format-value="formatMillions"
        />
        <div v-else class="loading-placeholder">Načítám barvy...</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.revenue-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
  overflow-y: auto;
}

.row-layout {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
  align-items: start;
}

.chart-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.chart-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 320px;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
</style>
