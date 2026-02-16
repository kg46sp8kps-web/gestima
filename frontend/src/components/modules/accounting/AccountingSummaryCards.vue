<script setup lang="ts">
import { computed } from 'vue'
import type { BalancePivotResponse } from '@/types/accounting'
import { MONTH_LABELS } from '@/types/accounting'

const props = defineProps<{
  data: BalancePivotResponse
}>()

// Revenue accounts (6xxxxx)
const revenueByMonth = computed(() => {
  const months: number[] = []
  for (let m = 1; m <= 12; m++) {
    let total = 0
    for (const ucet of props.data.accounts) {
      if (ucet.startsWith('6')) {
        const cell = props.data.cells[ucet]?.[String(m)]
        if (cell) total += Math.abs(cell.konecny)
      }
    }
    months.push(total)
  }
  return months
})

// Expense accounts (5xxxxx)
const expenseByMonth = computed(() => {
  const months: number[] = []
  for (let m = 1; m <= 12; m++) {
    let total = 0
    for (const ucet of props.data.accounts) {
      if (ucet.startsWith('5')) {
        const cell = props.data.cells[ucet]?.[String(m)]
        if (cell) total += Math.abs(cell.konecny)
      }
    }
    months.push(total)
  }
  return months
})

// Cash + Bank (2xxxxx)
const cashByMonth = computed(() => {
  const months: number[] = []
  for (let m = 1; m <= 12; m++) {
    let total = 0
    for (const ucet of props.data.accounts) {
      if (ucet.startsWith('2')) {
        const cell = props.data.cells[ucet]?.[String(m)]
        if (cell) total += cell.konecny
      }
    }
    months.push(total)
  }
  return months
})

// Inventory (1xxxxx)
const inventoryByMonth = computed(() => {
  const months: number[] = []
  for (let m = 1; m <= 12; m++) {
    let total = 0
    for (const ucet of props.data.accounts) {
      if (ucet.startsWith('1')) {
        const cell = props.data.cells[ucet]?.[String(m)]
        if (cell) total += cell.konecny
      }
    }
    months.push(total)
  }
  return months
})

// Latest non-zero month
const latestMonth = computed(() => {
  for (let m = 12; m >= 1; m--) {
    if ((revenueByMonth.value[m - 1] ?? 0) > 0 || (expenseByMonth.value[m - 1] ?? 0) > 0) return m
  }
  return 1
})

function latestValue(arr: number[]): number {
  return arr[latestMonth.value - 1] ?? 0
}

function trend(arr: number[]): 'up' | 'down' | 'flat' {
  const m = latestMonth.value
  if (m < 2) return 'flat'
  const curr = arr[m - 1] ?? 0
  const prev = arr[m - 2] ?? 0
  if (curr > prev * 1.02) return 'up'
  if (curr < prev * 0.98) return 'down'
  return 'flat'
}

function formatMillions(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return (value / 1_000_000).toFixed(1) + ' M'
  }
  if (Math.abs(value) >= 1_000) {
    return (value / 1_000).toFixed(0) + ' tis'
  }
  return value.toFixed(0)
}

// SVG sparkline path
function sparklinePath(data: number[], width: number, height: number): string {
  const validData = data.slice(0, latestMonth.value)
  if (validData.length < 2) return ''
  const max = Math.max(...validData, 1)
  const min = Math.min(...validData, 0)
  const range = max - min || 1
  const padding = 2

  const points = validData.map((v, i) => {
    const x = padding + (i / (validData.length - 1)) * (width - 2 * padding)
    const y = padding + (1 - (v - min) / range) * (height - 2 * padding)
    return `${x},${y}`
  })

  return 'M' + points.join(' L')
}

interface CardDef {
  label: string
  value: number
  data: number[]
  color: string
  gradient: string
  trendDir: 'up' | 'down' | 'flat'
}

const cards = computed<CardDef[]>(() => [
  {
    label: 'Výnosy',
    value: latestValue(revenueByMonth.value),
    data: revenueByMonth.value,
    color: 'var(--chart-revenue)',
    gradient: 'linear-gradient(135deg, var(--status-ok) 0%, var(--chart-revenue) 100%)',
    trendDir: trend(revenueByMonth.value),
  },
  {
    label: 'Náklady',
    value: latestValue(expenseByMonth.value),
    data: expenseByMonth.value,
    color: 'var(--chart-setup)',
    gradient: 'linear-gradient(135deg, var(--status-warn) 0%, var(--chart-setup) 100%)',
    trendDir: trend(expenseByMonth.value),
  },
  {
    label: 'Bilance',
    value: latestValue(revenueByMonth.value) - latestValue(expenseByMonth.value),
    data: revenueByMonth.value.map((r, i) => r - (expenseByMonth.value[i] ?? 0)),
    color: latestValue(revenueByMonth.value) - latestValue(expenseByMonth.value) >= 0 ? 'var(--chart-material)' : 'var(--chart-expenses)',
    gradient: latestValue(revenueByMonth.value) - latestValue(expenseByMonth.value) >= 0
      ? 'linear-gradient(135deg, var(--text-secondary) 0%, var(--chart-material) 100%)'
      : 'linear-gradient(135deg, var(--status-error) 0%, var(--chart-expenses) 100%)',
    trendDir: trend(revenueByMonth.value.map((r, i) => r - (expenseByMonth.value[i] ?? 0))),
  },
  {
    label: 'Zásoby',
    value: latestValue(inventoryByMonth.value),
    data: inventoryByMonth.value,
    color: 'var(--chart-wages)',
    gradient: 'linear-gradient(135deg, var(--text-secondary) 0%, var(--chart-wages) 100%)',
    trendDir: trend(inventoryByMonth.value),
  },
])
</script>

<template>
  <div class="summary-cards">
    <div
      v-for="card in cards"
      :key="card.label"
      class="card"
    >
      <div class="card-header">
        <span class="card-label">{{ card.label }}</span>
        <span class="card-month">{{ MONTH_LABELS[latestMonth] }} {{ data.rok }}</span>
      </div>
      <div class="card-value" :style="{ color: card.color }">
        {{ formatMillions(card.value) }} Kč
      </div>
      <div class="card-trend" :class="card.trendDir">
        <span class="trend-icon">
          {{ card.trendDir === 'up' ? '▲' : card.trendDir === 'down' ? '▼' : '—' }}
        </span>
        <span class="trend-label">
          {{ card.trendDir === 'up' ? 'Růst' : card.trendDir === 'down' ? 'Pokles' : 'Stabilní' }}
        </span>
      </div>
      <svg class="sparkline" viewBox="0 0 120 32" preserveAspectRatio="none">
        <path
          :d="sparklinePath(card.data, 120, 32)"
          fill="none"
          :stroke="card.color"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="0.7"
        />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
}

.card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  overflow: hidden;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}

.card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.card-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
}

.card-month {
  font-size: var(--text-2xs);
  color: var(--text-tertiary);
  background: var(--bg-raised);
  padding: var(--space-0\.5) var(--space-2);
  border-radius: var(--radius-sm);
}

.card-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  font-variant-numeric: tabular-nums;
  margin-bottom: var(--space-1);
  line-height: 1.2;
}

.card-trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.card-trend.up {
  color: var(--color-success);
}

.card-trend.down {
  color: var(--color-danger);
}

.card-trend.flat {
  color: var(--text-tertiary);
}

.trend-icon {
  font-size: 9px;
}

.sparkline {
  width: 100%;
  height: 32px;
}

@media (max-width: 900px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
