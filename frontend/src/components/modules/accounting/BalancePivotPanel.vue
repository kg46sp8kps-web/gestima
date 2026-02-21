<script setup lang="ts">
import { ref, computed } from 'vue'
import type { BalancePivotResponse } from '@/types/accounting'
import { MONTH_LABELS, ACCOUNT_GROUPS } from '@/types/accounting'

const props = defineProps<{
  data: BalancePivotResponse
}>()

const filterPrefix = ref<string | null>(null)
const searchText = ref('')
const hideZero = ref(true)
const displayMode = ref<'konecny' | 'pocatecni'>('konecny')

const filteredAccounts = computed(() => {
  return props.data.accounts.filter((ucet) => {
    if (filterPrefix.value && !ucet.startsWith(filterPrefix.value)) return false

    if (searchText.value) {
      const q = searchText.value.toLowerCase()
      const popis = props.data.account_names[ucet]?.toLowerCase() ?? ''
      if (!ucet.includes(q) && !popis.includes(q)) return false
    }

    if (hideZero.value) {
      const acctCells = props.data.cells[ucet]
      if (!acctCells) return false
      const hasNonZero = Object.values(acctCells).some(
        (c) => c.konecny !== 0 || c.pocatecni !== 0,
      )
      if (!hasNonZero) return false
    }

    return true
  })
})

function getCellValue(ucet: string, month: number): number {
  const cell = props.data.cells[ucet]?.[String(month)]
  if (!cell) return 0
  return displayMode.value === 'konecny' ? cell.konecny : cell.pocatecni
}

function formatCzk(value: number): string {
  if (value === 0) return '—'
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}
</script>

<template>
  <div class="balance-pivot-panel">
    <!-- Filter bar -->
    <div class="filter-bar">
      <div class="prefix-filters">
        <button
          v-for="grp in ACCOUNT_GROUPS"
          :key="grp.prefix"
          :class="['prefix-btn', { active: filterPrefix === grp.prefix }]"
          :title="grp.label"
          @click="filterPrefix = filterPrefix === grp.prefix ? null : grp.prefix"
        >
          {{ grp.prefix }}xx
        </button>
      </div>
      <input
        v-model="searchText"
        class="search-input"
        type="text"
        placeholder="Hledat účet nebo popis..."
      />
      <label class="checkbox-label">
        <input v-model="hideZero" type="checkbox" />
        Skrýt nulové
      </label>
      <select v-model="displayMode" class="mode-select">
        <option value="konecny">Konečný</option>
        <option value="pocatecni">Počáteční</option>
      </select>
      <span class="stats">{{ filteredAccounts.length }}/{{ data.accounts.length }}</span>
    </div>

    <!-- Pivot table -->
    <div class="table-wrapper">
      <table class="pivot-table">
        <thead>
          <tr>
            <th class="sticky-col col-ucet">Účet</th>
            <th class="sticky-col col-popis">Popis</th>
            <th v-for="m in data.months" :key="m" class="col-month">
              {{ MONTH_LABELS[m] }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ucet in filteredAccounts" :key="ucet">
            <td class="sticky-col col-ucet mono">{{ ucet }}</td>
            <td class="sticky-col col-popis" :title="data.account_names[ucet]">
              {{ data.account_names[ucet] }}
            </td>
            <td
              v-for="m in data.months"
              :key="m"
              class="col-month"
              :class="{ negative: getCellValue(ucet, m) < 0 }"
            >
              {{ formatCzk(getCellValue(ucet, m)) }}
            </td>
          </tr>
          <tr v-if="filteredAccounts.length === 0">
            <td :colspan="2 + data.months.length" class="empty-row">
              Žádné účty neodpovídají filtru
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.balance-pivot-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border-default);
  flex-wrap: wrap;
  background: var(--bg-surface);
}

.prefix-filters {
  display: flex;
  gap: var(--space-0\.5);
}

.prefix-btn {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--duration-fast);
}

.prefix-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-body);
}

.prefix-btn.active {
  background: var(--brand-subtle);
  color: var(--brand-text);
  border-color: var(--brand);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
}

.mode-select {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.stats {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  white-space: nowrap;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
}

.pivot-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.pivot-table th,
.pivot-table td {
  padding: var(--density-cell-py) var(--density-cell-px);
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.pivot-table thead th {
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 2px solid var(--border-default);
  z-index: 2;
}

.sticky-col {
  position: sticky;
  background: var(--bg-base);
  z-index: 1;
}

thead .sticky-col {
  z-index: 3;
  background: var(--bg-surface);
}

.col-ucet {
  left: 0;
  min-width: 70px;
}

.col-popis {
  left: 70px;
  min-width: 180px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-month {
  text-align: right;
  min-width: 85px;
  font-variant-numeric: tabular-nums;
  color: var(--text-body);
}

.mono {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.negative {
  color: var(--color-danger);
}

.empty-row {
  text-align: center;
  color: var(--text-tertiary);
  padding: var(--space-8);
}

tr:hover td {
  background: var(--bg-raised);
}

tr:hover .sticky-col {
  background: var(--bg-raised);
}
</style>
