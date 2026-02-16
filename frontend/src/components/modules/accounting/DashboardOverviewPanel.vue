<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DashboardOverviewResponse } from '@/types/accounting'
import SvgBarChart from '@/components/charts/SvgBarChart.vue'
import KpiCard from '@/components/charts/KpiCard.vue'
import { formatMillions, formatPct, MONTH_SHORT } from '@/composables/useChartUtils'
import { ragStatus, growthRate, generateOverviewInsights } from '@/composables/useDashboardInsights'

const props = defineProps<{ data: DashboardOverviewResponse }>()

const colors = ref({ revenue: '', expenses: '', profit: '' })
onMounted(() => {
  const s = getComputedStyle(document.documentElement)
  colors.value = {
    revenue: s.getPropertyValue('--chart-revenue').trim() || s.getPropertyValue('--color-success').trim(),
    expenses: s.getPropertyValue('--chart-expenses').trim() || s.getPropertyValue('--color-danger').trim(),
    profit: s.getPropertyValue('--chart-profit').trim() || s.getPropertyValue('--color-info').trim(),
  }
})

const monthlyRevenue = computed(() => props.data.monthly.map(m => m.revenue))
const monthlyExpenses = computed(() => props.data.monthly.map(m => m.expenses))
const monthlyProfit = computed(() => props.data.monthly.map(m => m.profit))

const marginStatus = computed(() =>
  ragStatus(props.data.ytd_margin_pct, { danger: 1, warning: 3 })
)

const cashDaysStatus = computed(() => {
  if (props.data.days_cash_on_hand == null) return null
  return ragStatus(props.data.days_cash_on_hand, { danger: 7, warning: 30 })
})

const expensesGrowth = computed(() =>
  growthRate(props.data.ytd_expenses, props.data.prev_ytd_expenses)
)

const barData = computed(() => {
  if (!colors.value.revenue) return []
  return props.data.monthly
    .filter(m => m.revenue > 0 || m.expenses > 0)
    .map(m => ({
      label: MONTH_SHORT[m.mesic - 1] || '',
      values: [
        { key: 'Výnosy', value: m.revenue, color: colors.value.revenue },
        { key: 'Náklady', value: m.expenses, color: colors.value.expenses },
      ],
      ghostValues: props.data.prev_monthly ? [
        {
          key: 'Výnosy (prev)',
          value: props.data.prev_monthly[m.mesic - 1]?.revenue ?? 0,
          color: colors.value.revenue
        },
        {
          key: 'Náklady (prev)',
          value: props.data.prev_monthly[m.mesic - 1]?.expenses ?? 0,
          color: colors.value.expenses
        },
      ] : undefined
    }))
})

const insights = computed(() => generateOverviewInsights(props.data))
</script>

<template>
  <div class="overview-panel">
    <div class="kpi-grid-4">
      <KpiCard
        label="Tržby"
        :value="formatMillions(data.ytd_revenue)"
        sub-label="Kč celkem"
        :change-pct="data.revenue_yoy_pct"
        change-label="YoY"
        :sparkline-data="monthlyRevenue"
        :status="data.revenue_yoy_pct != null && data.revenue_yoy_pct >= 0 ? 'success' : data.revenue_yoy_pct != null && data.revenue_yoy_pct < -10 ? 'danger' : 'warning'"
      />

      <KpiCard
        label="Náklady"
        :value="formatMillions(data.ytd_expenses)"
        sub-label="Kč celkem"
        :change-pct="expensesGrowth"
        change-label="YoY"
        :sparkline-data="monthlyExpenses"
        :invert-change-color="true"
      />

      <KpiCard
        label="Zisk"
        :value="formatMillions(data.ytd_profit)"
        :sub-label="data.ytd_profit >= 0 ? 'zisk' : 'ztráta'"
        :change-pct="data.profit_yoy_pct"
        change-label="YoY"
        :sparkline-data="monthlyProfit"
        :status="marginStatus"
      />

      <KpiCard
        label="Marže"
        :value="formatPct(data.ytd_margin_pct)"
        sub-label="z tržeb"
        :change-pct="data.margin_delta_pp"
        change-label="pp YoY"
        :status="marginStatus"
        target-value="Cíl: 5 %"
      />
    </div>

    <div class="kpi-grid-3">
      <KpiCard
        label="Cash"
        :value="formatMillions(data.cash_position)"
        :sub-label="data.days_cash_on_hand != null ? `${data.days_cash_on_hand.toFixed(0)} dnů pokrytí` : 'Kč'"
        :status="cashDaysStatus ?? undefined"
      />

      <KpiCard
        label="Pohledávky"
        :value="formatMillions(data.receivables)"
        :sub-label="data.receivables_to_revenue_pct != null ? `${data.receivables_to_revenue_pct.toFixed(1)} % tržeb` : 'Kč'"
        :status="data.receivables_to_revenue_pct != null && data.receivables_to_revenue_pct > 15 ? 'warning' : 'success'"
      />

      <KpiCard
        label="Zásoby"
        :value="formatMillions(data.inventory_total)"
        :sub-label="data.inventory_to_revenue_pct != null ? `${data.inventory_to_revenue_pct.toFixed(1)} % tržeb` : 'Kč'"
      />
    </div>

    <div class="chart-section">
      <h3 class="chart-title">Měsíční vývoj výnosů a nákladů</h3>
      <SvgBarChart v-if="barData.length" :data="barData" :height="280" />
      <div v-else class="loading-placeholder">Načítám data...</div>
    </div>

    <div v-if="insights.length" class="insights-section">
      <h3 class="chart-title">Klíčová zjištění</h3>
      <div class="insights-grid">
        <div
          v-for="(insight, idx) in insights"
          :key="idx"
          class="insight-card"
          :class="`insight-${insight.severity}`"
        >
          <div class="insight-border" />
          <span class="insight-text">{{ insight.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
  overflow-y: auto;
}

.kpi-grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.kpi-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.chart-section {
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
  height: 280px;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.insights-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.insight-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.insight-border {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}

.insight-card.insight-success .insight-border {
  background: var(--color-success);
}

.insight-card.insight-warning .insight-border {
  background: var(--color-warning);
}

.insight-card.insight-danger .insight-border {
  background: var(--color-danger);
}

.insight-text {
  font-size: var(--text-sm);
  color: var(--text-body);
  line-height: 1.5;
}
</style>
