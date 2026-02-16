<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type {
  DashboardCostsResponse,
  DashboardRevenueResponse,
  DashboardMachinesResponse
} from '@/types/accounting'
import SvgRingChart from '@/components/charts/SvgRingChart.vue'
import SvgHorizontalBars from '@/components/charts/SvgHorizontalBars.vue'
import SvgAreaChart from '@/components/charts/SvgAreaChart.vue'
import { formatCzk, formatMillions, MONTH_SHORT, CHART_COLORS } from '@/composables/useChartUtils'

interface Props {
  costsData: DashboardCostsResponse | null
  revenueData: DashboardRevenueResponse | null
  machinesData: DashboardMachinesResponse | null
}

const props = defineProps<Props>()

const colors = ref<Record<string, string>>({})
onMounted(() => {
  const s = getComputedStyle(document.documentElement)
  colors.value = {
    revenue: s.getPropertyValue('--chart-revenue').trim() || s.getPropertyValue('--color-success').trim(),
    material: s.getPropertyValue('--chart-material').trim() || s.getPropertyValue('--color-success').trim(),
  }
})

const costRingSegments = computed(() =>
  props.costsData?.by_category.map((cat, idx) => ({
    label: cat.category,
    value: cat.amount,
    color: CHART_COLORS[idx % CHART_COLORS.length] as string
  })) ?? []
)

const costTopAccounts = computed(() =>
  props.costsData?.top_accounts.slice(0, 5).map(acc => ({
    label: `${acc.ucet} - ${acc.popis.slice(0, 20)}`,
    value: Math.abs(acc.total),
  })) ?? []
)

const revenueRingSegments = computed(() =>
  props.revenueData?.streams.map((stream, idx) => {
    const color = (colors.value.revenue || CHART_COLORS[idx % CHART_COLORS.length]) as string
    return {
      label: stream.category,
      value: stream.total,
      color
    }
  }) ?? []
)

const revenueAreaSeries = computed(() => {
  if (!props.revenueData || !colors.value.revenue) return []
  return props.revenueData.streams.map((stream, idx) => {
    const color = (colors.value.revenue || CHART_COLORS[idx % CHART_COLORS.length]) as string
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

const machinesBarData = computed(() =>
  props.machinesData?.machines
    .sort((a, b) => Math.abs(b.total) - Math.abs(a.total))
    .slice(0, 10)
    .map(m => ({
      label: m.label || m.code,
      value: Math.abs(m.total),
    })) ?? []
)
</script>

<template>
  <div class="details-panel">
    <div class="section">
      <h2 class="section-title">Struktura nákladů</h2>
      <div class="row-layout">
        <div class="chart-card">
          <h3 class="chart-title">Náklady podle kategorie</h3>
          <SvgRingChart
            v-if="costRingSegments.length"
            :segments="costRingSegments"
            :size="220"
            :format-value="formatMillions"
          />
          <div v-else class="loading-placeholder">Žádná data</div>
        </div>

        <div class="chart-card">
          <h3 class="chart-title">Top 5 účtů</h3>
          <SvgHorizontalBars
            v-if="costTopAccounts.length"
            :items="costTopAccounts"
            :max-items="5"
            :format-value="formatCzk"
          />
          <div v-else class="loading-placeholder">Žádná data</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title">Tržby</h2>
      <div class="row-layout">
        <div class="chart-card">
          <h3 class="chart-title">Tržby podle proudů</h3>
          <SvgRingChart
            v-if="revenueRingSegments.length && revenueData"
            :segments="revenueRingSegments"
            :size="220"
            :center-label="formatMillions(revenueData.ytd_total)"
            center-sub="Celkem"
            :format-value="formatMillions"
          />
          <div v-else class="loading-placeholder">Žádná data</div>
        </div>

        <div class="chart-card">
          <h3 class="chart-title">Měsíční vývoj tržeb</h3>
          <SvgAreaChart
            v-if="revenueAreaSeries.length"
            :series="revenueAreaSeries"
            :labels="monthLabels"
            :height="280"
            :format-value="formatMillions"
          />
          <div v-else class="loading-placeholder">Žádná data</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title">Náklady na stroje</h2>
      <div class="chart-card full-width">
        <h3 class="chart-title">Top 10 strojů podle nákladů</h3>
        <SvgHorizontalBars
          v-if="machinesBarData.length"
          :items="machinesBarData"
          :max-items="10"
          :format-value="formatCzk"
        />
        <div v-else class="loading-placeholder">Žádná data</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.details-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-5);
  overflow-y: auto;
}

.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--border-default);
}

.row-layout {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
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
  height: 220px;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
</style>
