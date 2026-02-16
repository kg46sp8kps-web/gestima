<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DashboardBalanceSheetResponse } from '@/types/accounting'
import SvgHorizontalBars from '@/components/charts/SvgHorizontalBars.vue'
import SvgAreaChart from '@/components/charts/SvgAreaChart.vue'
import { formatCzk, formatMillions, MONTH_SHORT, CHART_COLORS } from '@/composables/useChartUtils'

const props = defineProps<{ data: DashboardBalanceSheetResponse }>()

const colors = ref<Record<string, string>>({})
onMounted(() => {
  const s = getComputedStyle(document.documentElement)
  colors.value = {
    wip: s.getPropertyValue('--chart-material').trim(),
    finished: s.getPropertyValue('--chart-machining').trim(),
    cash: s.getPropertyValue('--chart-revenue').trim(),
    receivables: s.getPropertyValue('--chart-cooperation').trim(),
    payables: s.getPropertyValue('--chart-expenses').trim(),
  }
})

const assetsData = computed(() =>
  props.data.assets.map(a => ({
    label: a.category,
    value: a.total,
  }))
)

const areaSeries = computed(() => {
  if (!Object.keys(colors.value).length) return []
  return [
    { label: 'Nedokončená výroba', data: props.data.wip_monthly, color: (colors.value.wip || CHART_COLORS[0]) as string },
    { label: 'Hotové výrobky', data: props.data.finished_monthly, color: (colors.value.finished || CHART_COLORS[1]) as string },
    { label: 'Hotovost', data: props.data.cash_monthly, color: (colors.value.cash || CHART_COLORS[2]) as string },
    { label: 'Pohledávky', data: props.data.receivables_monthly, color: (colors.value.receivables || CHART_COLORS[3]) as string },
    { label: 'Závazky', data: props.data.payables_monthly, color: (colors.value.payables || CHART_COLORS[4]) as string },
  ].filter(s => s.data.some(v => v > 0))
})

const monthLabels = computed(() =>
  Array.from({ length: 12 }, (_, i) => MONTH_SHORT[i] ?? '')
)
</script>

<template>
  <div class="balance-panel">
    <div class="chart-card">
      <h3 class="chart-title">Skladba aktiv</h3>
      <SvgHorizontalBars :items="assetsData" :max-items="10" :format-value="formatCzk" />
    </div>

    <div class="chart-card">
      <h3 class="chart-title">Měsíční trendy bilance</h3>
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
</template>

<style scoped>
.balance-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
  overflow-y: auto;
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
