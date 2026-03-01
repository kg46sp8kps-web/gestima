import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as operatorApi from '@/api/operator'
import type { ActiveJob, OperatorStats, OperatorWorkcenter, TransactionAlert } from '@/types/operator'

export const useOperatorStore = defineStore('operator', () => {
  const selectedWc = ref<string | null>(null)
  const selectedWcGroup = ref<{ label: string; wcs: string[] } | null>(null)
  const activeJobs = ref<ActiveJob[]>([])
  const transactionAlerts = ref<TransactionAlert[]>([])
  const stats = ref<OperatorStats | null>(null)
  const workcenters = ref<OperatorWorkcenter[]>([])
  const lastActivity = ref<number>(Date.now())
  const isOnline = ref<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true)

  let refreshInterval: ReturnType<typeof setInterval> | null = null

  const hasActiveJob = computed(() => activeJobs.value.length > 0)
  const unresolvedTxCount = computed(() => transactionAlerts.value.length)
  const unresolvedErrorCount = computed(
    () => transactionAlerts.value.filter((t) => t.severity === 'error').length,
  )

  async function fetchActiveJobs() {
    try {
      activeJobs.value = await operatorApi.getActiveJobs()
    } catch {
      // silent
    }
  }

  async function fetchStats() {
    try {
      stats.value = await operatorApi.getStats()
    } catch {
      // silent
    }
  }

  async function fetchWorkcenters() {
    try {
      workcenters.value = await operatorApi.getWorkcenters()
    } catch {
      // silent
    }
  }

  async function fetchTransactionAlerts(limit = 30) {
    try {
      transactionAlerts.value = await operatorApi.getTransactionAlerts(limit)
    } catch {
      // silent
    }
  }

  async function retryTransaction(txId: number): Promise<boolean> {
    try {
      await operatorApi.retryTransaction(txId)
      await fetchTransactionAlerts()
      await fetchActiveJobs()
      return true
    } catch {
      return false
    }
  }

  function selectWorkcenter(wc: string) {
    selectedWc.value = wc
    selectedWcGroup.value = null
    lastActivity.value = Date.now()
  }

  function selectWorkcenterGroup(label: string, wcs: string[]) {
    selectedWcGroup.value = { label, wcs }
    selectedWc.value = null
    lastActivity.value = Date.now()
  }

  function touchActivity() {
    lastActivity.value = Date.now()
  }

  function setOnlineStatus(value: boolean) {
    isOnline.value = value
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    refreshInterval = setInterval(() => {
      fetchActiveJobs()
      fetchTransactionAlerts()
    }, 30_000)
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  function $reset() {
    selectedWc.value = null
    selectedWcGroup.value = null
    activeJobs.value = []
    transactionAlerts.value = []
    stats.value = null
    workcenters.value = []
    stopAutoRefresh()
  }

  return {
    selectedWc,
    selectedWcGroup,
    activeJobs,
    transactionAlerts,
    stats,
    workcenters,
    lastActivity,
    isOnline,
    hasActiveJob,
    unresolvedTxCount,
    unresolvedErrorCount,
    fetchActiveJobs,
    fetchStats,
    fetchWorkcenters,
    fetchTransactionAlerts,
    retryTransaction,
    selectWorkcenter,
    selectWorkcenterGroup,
    touchActivity,
    setOnlineStatus,
    startAutoRefresh,
    stopAutoRefresh,
    $reset,
  }
})
