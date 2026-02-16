<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DashboardCostsResponse } from '@/types/accounting'
import SvgRingChart from '@/components/charts/SvgRingChart.vue'
import SvgHorizontalBars from '@/components/charts/SvgHorizontalBars.vue'
import SvgStackedBars from '@/components/charts/SvgStackedBars.vue'
import { formatCzk, formatMillions, CHART_COLORS, MONTH_SHORT } from '@/composables/useChartUtils'

const props = defineProps<{ data: DashboardCostsResponse }>()

const colors = ref<Record<string, string>>({})
onMounted(() => {
  const s = getComputedStyle(document.documentElement)
  colors.value = {
    MAT: s.getPropertyValue('--chart-material').trim(),
    MZDY: s.getPropertyValue('--chart-wages').trim(),
    KOO: s.getPropertyValue('--chart-cooperation').trim(),
    VAR: s.getPropertyValue('--chart-machining').trim(),
    FIX: s.getPropertyValue('--chart-depreciation').trim(),
    Fstr: s.getPropertyValue('--chart-energy').trim(),
    Vstr: s.getPropertyValue('--chart-tools').trim(),
  }
})

const ringSegments = computed(() =>
  props.data.by_category.map((cat, idx) => ({
    label: cat.category,
    value: cat.amount,
    color: CHART_COLORS[idx % CHART_COLORS.length] as string
  }))
)

const topAccountsData = computed(() =>
  props.data.top_accounts.slice(0, 10).map(acc => ({
    label: `${acc.ucet} - ${acc.popis.slice(0, 20)}`,
    value: Math.abs(acc.total),
  }))
)

const stackedData = computed(() => {
  if (!Object.keys(colors.value).length) return []
  const getColor = (key: string, idx: number) => (colors.value[key] || CHART_COLORS[idx]) as string
  return props.data.by_type_monthly.map(m => ({
    label: MONTH_SHORT[m.mesic - 1] || '',
    segments: [
      { key: 'MAT', value: m.MAT, color: getColor('MAT', 0) },
      { key: 'MZDY', value: m.MZDY, color: getColor('MZDY', 1) },
      { key: 'KOO', value: m.KOO, color: getColor('KOO', 2) },
      { key: 'VAR', value: m.VAR, color: getColor('VAR', 3) },
      { key: 'FIX', value: m.FIX, color: getColor('FIX', 4) },
      { key: 'Fstr', value: m.Fstr, color: getColor('Fstr', 5) },
      { key: 'Vstr', value: m.Vstr, color: getColor('Vstr', 6) },
    ].filter(s => s.value > 0)
  }))
})

const stackedKeys = computed(() => {
  const getColor = (key: string, idx: number) => (colors.value[key] || CHART_COLORS[idx]) as string
  return [
    { key: 'MAT', label: 'Materiál', color: getColor('MAT', 0) },
    { key: 'MZDY', label: 'Mzdy', color: getColor('MZDY', 1) },
    { key: 'KOO', label: 'Kooperace', color: getColor('KOO', 2) },
    { key: 'VAR', label: 'Variabilní', color: getColor('VAR', 3) },
    { key: 'FIX', label: 'Fixní', color: getColor('FIX', 4) },
    { key: 'Fstr', label: 'Fin. stroje', color: getColor('Fstr', 5) },
    { key: 'Vstr', label: 'Výr. stroje', color: getColor('Vstr', 6) },
  ]
})
</script>

<template>
  <div class="costs-panel">
    <div class="row-layout">
      <div class="chart-card">
        <h3 class="chart-title">Náklady podle kategorie</h3>
        <SvgRingChart :segments="ringSegments" :size="220" :format-value="formatMillions" />
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Top 10 účtů (podle objemu)</h3>
        <SvgHorizontalBars :items="topAccountsData" :max-items="10" :format-value="formatCzk" />
      </div>
    </div>

    <div class="chart-card full-width">
      <h3 class="chart-title">Měsíční náklady podle typu</h3>
      <SvgStackedBars v-if="stackedData.length" :data="stackedData" :keys="stackedKeys" :height="320" />
      <div v-else class="loading-placeholder">Načítám barvy...</div>
    </div>
  </div>
</template>

<style scoped>
.costs-panel {
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
}

.chart-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.chart-card.full-width {
  grid-column: 1 / -1;
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
