<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type {
  BalancePivotResponse,
  TurnoverResponse,
  DashboardOverviewResponse,
  DashboardCostsResponse,
  DashboardMachinesResponse,
  DashboardRevenueResponse,
} from '@/types/accounting'
import {
  getAccountingBalances,
  getAccountingTurnovers,
  refreshAccountingCache,
  getDashboardOverview,
  getDashboardCosts,
  getDashboardMachines,
  getDashboardRevenue,
} from '@/api/accounting'
import AccountingToolbar from './accounting/AccountingToolbar.vue'
import DashboardOverviewPanel from './accounting/DashboardOverviewPanel.vue'
import DashboardDetailsPanel from './accounting/DashboardDetailsPanel.vue'
import BalancePivotPanel from './accounting/BalancePivotPanel.vue'
import TurnoverPivotPanel from './accounting/TurnoverPivotPanel.vue'

interface Props {
  windowTitle?: string
  linkingGroup?: string | null
}
defineProps<Props>()

type TabKey = 'executive' | 'details' | 'data'

const activeTab = ref<TabKey>('executive')
const dataSubTab = ref<'balances' | 'turnovers'>('balances')
const selectedYear = ref(new Date().getFullYear())
const loading = ref(false)
const error = ref<string | null>(null)

const overviewData = ref<DashboardOverviewResponse | null>(null)
const costsData = ref<DashboardCostsResponse | null>(null)
const machinesData = ref<DashboardMachinesResponse | null>(null)
const revenueData = ref<DashboardRevenueResponse | null>(null)
const balanceData = ref<BalancePivotResponse | null>(null)
const turnoverData = ref<TurnoverResponse | null>(null)

async function loadData() {
  loading.value = true
  error.value = null
  try {
    if (activeTab.value === 'executive') {
      if (!overviewData.value) {
        overviewData.value = await getDashboardOverview(selectedYear.value)
      }
      if (!balanceData.value) {
        balanceData.value = await getAccountingBalances(selectedYear.value)
      }
    } else if (activeTab.value === 'details') {
      if (!costsData.value) {
        costsData.value = await getDashboardCosts(selectedYear.value)
      }
      if (!revenueData.value) {
        revenueData.value = await getDashboardRevenue(selectedYear.value)
      }
      if (!machinesData.value) {
        machinesData.value = await getDashboardMachines(selectedYear.value)
      }
    } else if (activeTab.value === 'data') {
      if (dataSubTab.value === 'balances' && !balanceData.value) {
        balanceData.value = await getAccountingBalances(selectedYear.value)
      } else if (dataSubTab.value === 'turnovers' && !turnoverData.value) {
        turnoverData.value = await getAccountingTurnovers(selectedYear.value)
      }
    }
  } catch (e: unknown) {
    error.value = (e as Error)?.message ?? 'Chyba při načítání dat'
  } finally {
    loading.value = false
  }
}

async function handleRefresh() {
  await refreshAccountingCache(selectedYear.value)
  clearAllData()
  await loadData()
}

function clearAllData() {
  overviewData.value = null
  costsData.value = null
  machinesData.value = null
  revenueData.value = null
  balanceData.value = null
  turnoverData.value = null
}

function switchTab(tab: TabKey) {
  activeTab.value = tab
  loadData()
}

function switchDataSubTab(subtab: 'balances' | 'turnovers') {
  dataSubTab.value = subtab
  loadData()
}

function switchYear(year: number) {
  selectedYear.value = year
  clearAllData()
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="accounting-module">
    <AccountingToolbar
      :selected-year="selectedYear"
      :active-tab="activeTab"
      :loading="loading"
      :active-accounts-count="balanceData?.non_zero_accounts"
      @update:year="switchYear"
      @update:tab="switchTab"
      @refresh="handleRefresh"
    />

    <div v-if="error" class="error-bar">{{ error }}</div>

    <div v-if="loading" class="loading-state">Načítám data z CsiXls...</div>

    <template v-else>
      <DashboardOverviewPanel v-if="activeTab === 'executive' && overviewData" :data="overviewData" />

      <DashboardDetailsPanel
        v-if="activeTab === 'details'"
        :costs-data="costsData"
        :revenue-data="revenueData"
        :machines-data="machinesData"
      />

      <template v-if="activeTab === 'data'">
        <div class="data-tab-toolbar">
          <button
            :class="['data-sub-btn', { active: dataSubTab === 'balances' }]"
            @click="switchDataSubTab('balances')"
          >
            Zůstatky
          </button>
          <button
            :class="['data-sub-btn', { active: dataSubTab === 'turnovers' }]"
            @click="switchDataSubTab('turnovers')"
          >
            Obraty
          </button>
        </div>
        <BalancePivotPanel v-if="dataSubTab === 'balances' && balanceData" :data="balanceData" />
        <TurnoverPivotPanel v-if="dataSubTab === 'turnovers' && turnoverData" :data="turnoverData" />
      </template>
    </template>
  </div>
</template>

<style scoped>
.accounting-module {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--base);
}

.error-bar {
  padding: var(--pad) 16px;
  background: rgba(248,113,113,0.15);
  color: var(--err);
  font-size: var(--fs);
  border-bottom: 1px solid rgba(248,113,113,0.15);
  display: flex;
  align-items: center;
  gap: 6px;
}

.data-tab-toolbar {
  display: flex;
  gap: 2px;
  padding: var(--pad) 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
}

.data-sub-btn {
  padding: 4px var(--pad);
  font-size: var(--fs);
  font-weight: 500;
  border: none;
  border-radius: var(--rs);
  background: transparent;
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms;
}

.data-sub-btn:hover {
  background: var(--raised);
  color: var(--t2);
}

.data-sub-btn.active {
  background: var(--raised);
  color: var(--t1);
  font-weight: 600;
}
</style>
