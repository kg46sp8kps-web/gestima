<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardMachinesResponse } from '@/types/accounting'
import SvgHorizontalBars from '@/components/charts/SvgHorizontalBars.vue'
import SvgRingChart from '@/components/charts/SvgRingChart.vue'
import { formatCzk, formatMillions, CHART_COLORS } from '@/composables/useChartUtils'

const props = defineProps<{ data: DashboardMachinesResponse }>()

const machinesData = computed(() =>
  props.data.machines
    .sort((a, b) => Math.abs(b.total) - Math.abs(a.total))
    .slice(0, 15)
    .map(m => ({
      label: m.label || m.code,
      value: Math.abs(m.total),
    }))
)

const costCentersData = computed(() =>
  props.data.cost_centers.map((cc, idx) => ({
    label: cc.label || cc.code,
    value: Math.abs(cc.total),
    color: CHART_COLORS[idx % CHART_COLORS.length] as string
  }))
)
</script>

<template>
  <div class="machines-panel">
    <div class="row-layout">
      <div class="chart-card">
        <h3 class="chart-title">Top 15 strojů (podle nákladů)</h3>
        <SvgHorizontalBars :items="machinesData" :max-items="15" :format-value="formatCzk" />
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Náklady podle středisek</h3>
        <SvgRingChart :segments="costCentersData" :size="260" :format-value="formatMillions" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.machines-panel {
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
</style>
