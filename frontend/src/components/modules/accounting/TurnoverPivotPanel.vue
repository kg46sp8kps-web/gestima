<script setup lang="ts">
import { ref, computed } from 'vue'
import type { TurnoverResponse, TurnoverRecord } from '@/types/accounting'
import { MONTH_LABELS } from '@/types/accounting'
import TurnoverFiltersBar from './TurnoverFiltersBar.vue'

const props = defineProps<{
  data: TurnoverResponse
}>()

const filterPrefix = ref<string | null>(null)
const searchText = ref('')
const hideZero = ref(true)
const filterDan1 = ref<string>('')
const filterDan2 = ref<string>('')
const filterDan3 = ref<string>('')
const expandedAccounts = ref<Set<string>>(new Set())

const filteredRecords = computed(() => {
  return props.data.records.filter((r) => {
    if (filterPrefix.value && !r.ucet.startsWith(filterPrefix.value)) return false
    if (searchText.value) {
      const q = searchText.value.toLowerCase()
      if (!r.ucet.includes(q) && !r.popis.toLowerCase().includes(q)) return false
    }
    if (hideZero.value && Math.abs(r.md) < 0.01 && Math.abs(r.dal) < 0.01) return false
    if (filterDan1.value && r.dAn1 !== filterDan1.value) return false
    if (filterDan2.value && r.dAn2 !== filterDan2.value) return false
    if (filterDan3.value && r.dAn3 !== filterDan3.value) return false
    return true
  })
})

interface AccountGroup {
  ucet: string
  popis: string
  months: Record<number, { md: number; dal: number }>
  details: TurnoverRecord[]
  hasAnalytics: boolean
}

const groupedData = computed(() => {
  const groups = new Map<string, AccountGroup>()
  for (const r of filteredRecords.value) {
    if (!groups.has(r.ucet)) {
      groups.set(r.ucet, {
        ucet: r.ucet,
        popis: r.popis,
        months: {},
        details: [],
        hasAnalytics: false,
      })
    }
    const g = groups.get(r.ucet)!
    if (!g.months[r.mesic]) {
      g.months[r.mesic] = { md: 0, dal: 0 }
    }
    const monthData = g.months[r.mesic]
    if (monthData) {
      monthData.md += r.md
      monthData.dal += r.dal
    }
    g.details.push(r)
    if (r.dAn1 || r.dAn2 || r.dAn3) {
      g.hasAnalytics = true
    }
  }
  return Array.from(groups.values()).sort((a, b) => a.ucet.localeCompare(b.ucet))
})

function toggleExpand(ucet: string) {
  if (expandedAccounts.value.has(ucet)) {
    expandedAccounts.value.delete(ucet)
  } else {
    expandedAccounts.value.add(ucet)
  }
}

function formatCzk(value: number): string {
  if (Math.abs(value) < 0.01) return '—'
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function analyticsLabel(r: TurnoverRecord): string {
  const parts: string[] = []
  if (r.dAn1) parts.push(r.dAn1)
  if (r.dAn2) parts.push(r.dAn2)
  if (r.dAn3) parts.push(r.dAn3)
  return parts.join(' / ') || '—'
}
</script>

<template>
  <div class="turnover-pivot-panel">
    <TurnoverFiltersBar
      v-model:filter-prefix="filterPrefix"
      v-model:search-text="searchText"
      v-model:hide-zero="hideZero"
      v-model:filter-dan1="filterDan1"
      v-model:filter-dan2="filterDan2"
      v-model:filter-dan3="filterDan3"
      :account-count="groupedData.length"
      :analytics="data.analytics"
    />

    <div class="table-wrapper">
      <table class="pivot-table">
        <thead>
          <tr>
            <th class="sticky-col col-ucet">Účet</th>
            <th class="sticky-col col-popis">Popis</th>
            <template v-for="m in 12" :key="m">
              <th class="col-md">{{ MONTH_LABELS[m] }} Md</th>
              <th class="col-dal">{{ MONTH_LABELS[m] }} Dal</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in groupedData" :key="group.ucet">
            <tr
              class="account-row"
              :class="{ expandable: group.hasAnalytics }"
              @click="group.hasAnalytics && toggleExpand(group.ucet)"
            >
              <td class="sticky-col col-ucet mono">
                <span v-if="group.hasAnalytics" class="expand-icon">
                  {{ expandedAccounts.has(group.ucet) ? '▼' : '▶' }}
                </span>
                {{ group.ucet }}
              </td>
              <td class="sticky-col col-popis" :title="group.popis">
                {{ group.popis }}
              </td>
              <template v-for="m in 12" :key="m">
                <td class="col-md" :class="{ negative: (group.months[m]?.md ?? 0) < 0 }">
                  {{ formatCzk(group.months[m]?.md ?? 0) }}
                </td>
                <td class="col-dal" :class="{ negative: (group.months[m]?.dal ?? 0) < 0 }">
                  {{ formatCzk(group.months[m]?.dal ?? 0) }}
                </td>
              </template>
            </tr>
            <template v-if="expandedAccounts.has(group.ucet)">
              <tr
                v-for="(detail, idx) in group.details"
                :key="`${group.ucet}-${idx}`"
                class="detail-row"
              >
                <td class="sticky-col col-ucet"></td>
                <td class="sticky-col col-popis detail-label">
                  {{ analyticsLabel(detail) }}
                </td>
                <template v-for="m in 12" :key="m">
                  <td class="col-md" :class="{ negative: detail.md < 0 }">
                    {{ detail.mesic === m ? formatCzk(detail.md) : '' }}
                  </td>
                  <td class="col-dal" :class="{ negative: detail.dal < 0 }">
                    {{ detail.mesic === m ? formatCzk(detail.dal) : '' }}
                  </td>
                </template>
              </tr>
            </template>
          </template>
          <tr v-if="groupedData.length === 0">
            <td :colspan="2 + 24" class="empty-row">Žádné záznamy</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.turnover-pivot-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
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
  min-width: 80px;
}

.col-popis {
  left: 80px;
  min-width: 160px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-md,
.col-dal {
  text-align: right;
  min-width: 70px;
  font-variant-numeric: tabular-nums;
  color: var(--t2);
}

.col-dal {
  border-right: 1px solid var(--b1);
}

.mono {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--t3);
}

.negative {
  color: var(--err);
}

.account-row.expandable {
  cursor: pointer;
}

.account-row.expandable:hover td {
  background: var(--raised);
}

.account-row.expandable:hover .sticky-col {
  background: var(--raised);
}

.expand-icon {
  font-size: var(--fs);
  margin-right: 4px;
  color: var(--t3);
}

.detail-row td {
  font-size: var(--fs);
  color: var(--t3);
  background: var(--base);
}

.detail-row .sticky-col {
  background: var(--base);
}

.detail-label {
  font-style: italic;
  padding-left: 20px;
}

.empty-row {
  text-align: center;
  color: var(--t3);
  padding: 24px;
}
</style>
