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
  gap: var(--pad);
  padding: var(--pad) 16px;
  border-bottom: 1px solid var(--b2);
  flex-wrap: wrap;
  background: var(--surface);
}

.prefix-filters {
  display: flex;
  gap: 2px;
}

.prefix-btn {
  padding: 4px 6px;
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  cursor: pointer;
  color: var(--t3);
  transition: all 100ms;
}

.prefix-btn:hover {
  border-color: var(--b3);
  color: var(--t2);
}

.prefix-btn.active {
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
  border-color: var(--red);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  cursor: pointer;
}

.mode-select {
  padding: 4px 6px;
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  color: var(--t2);
}

.stats {
  font-size: var(--fs);
  color: var(--t3);
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
  font-size: var(--fs);
}

.pivot-table th,
.pivot-table td {
  padding: 3px 10px;
  border-bottom: 1px solid var(--b1);
  white-space: nowrap;
}

.pivot-table thead th {
  position: sticky;
  top: 0;
  background: var(--surface);
  font-weight: 600;
  color: var(--t3);
  font-size: var(--fs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 2px solid var(--b2);
  z-index: 2;
}

.sticky-col {
  position: sticky;
  background: var(--base);
  z-index: 1;
}

thead .sticky-col {
  z-index: 3;
  background: var(--surface);
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
  color: var(--t2);
}

.mono {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--t3);
}

.negative {
  color: var(--err);
}

.empty-row {
  text-align: center;
  color: var(--t3);
  padding: 24px;
}

tr:hover td {
  background: var(--raised);
}

tr:hover .sticky-col {
  background: var(--raised);
}
</style>
