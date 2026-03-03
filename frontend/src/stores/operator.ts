import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as operatorApi from '@/api/operator'
import type {
  ActiveJob,
  NormDetailRow,
  OperatorStats,
  OperatorWorkcenter,
  TransactionAlert,
} from '@/types/operator'
import type { NormQueryParams } from '@/api/operator'
import type { PriorityTier } from '@/types/production-planner'

export const useOperatorStore = defineStore('operator', () => {
  const selectedWc = ref<string | null>(null)
  const selectedWcGroup = ref<{ label: string; wcs: string[] } | null>(null)
  const activeJobs = ref<ActiveJob[]>([])
  const transactionAlerts = ref<TransactionAlert[]>([])
  const stats = ref<OperatorStats | null>(null)
  const workcenters = ref<OperatorWorkcenter[]>([])
  const lastActivity = ref<number>(Date.now())
  const isOnline = ref<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true)

  // Norm performance state
  const normDetails = ref<NormDetailRow[]>([])
  const normDetailsLoading = ref(false)

  // SSE tier overrides — persists across terminal page navigation
  const tierOverrides = ref<Record<string, PriorityTier>>({})

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

  async function fetchNormDetails(params: NormQueryParams = { period: 'day' }) {
    normDetailsLoading.value = true
    try {
      normDetails.value = await operatorApi.getNormDetails(params)
    } catch {
      normDetails.value = []
    } finally {
      normDetailsLoading.value = false
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

  /** Store SSE tier change — case-insensitive key (uppercased) */
  function applyTierChange(job: string, tier: PriorityTier) {
    tierOverrides.value[job.toUpperCase()] = tier
  }

  /** Get tier override for a job (case-insensitive lookup) */
  function getTierOverride(job: string): PriorityTier | undefined {
    return tierOverrides.value[job.toUpperCase()]
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
    normDetails.value = []
    normDetailsLoading.value = false
    tierOverrides.value = {}
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
    normDetails,
    normDetailsLoading,
    hasActiveJob,
    unresolvedTxCount,
    unresolvedErrorCount,
    fetchActiveJobs,
    fetchStats,
    fetchWorkcenters,
    fetchTransactionAlerts,
    fetchNormDetails,
    retryTransaction,
    selectWorkcenter,
    selectWorkcenterGroup,
    touchActivity,
    setOnlineStatus,
    tierOverrides,
    applyTierChange,
    getTierOverride,
    startAutoRefresh,
    stopAutoRefresh,
    $reset,
  }
})
