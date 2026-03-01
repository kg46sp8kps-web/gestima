/** Gestima Dílna — Pinia store */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as workshopApi from '@/api/workshop'
import { useUiStore } from './ui'
import type {
  WorkshopJob,
  WorkshopQueueItem,
  WorkshopQueueSortBy,
  WorkshopOperation,
  WorkshopOperationSortBy,
  WorkshopMaterial,
  WorkshopMaterialSortBy,
  WorkshopSortDir,
  WorkshopMaterialIssueCreate,
  WorkshopMaterialIssueResult,
  WorkshopTransaction,
  WorkshopTransactionCreate,
  WorkshopTimer,
  WorkshopTransType,
  WorkshopOrderOverviewRow,
} from '@/types/workshop'
import type { VpListItem } from '@/types/vp'

export const useWorkshopStore = defineStore('workshop', () => {
  const ui = useUiStore()

  // === State ===
  // Fronta práce (nový model — flat seznam operací)
  const queueItems = ref<WorkshopQueueItem[]>([])
  const activeQueueItem = ref<WorkshopQueueItem | null>(null)
  const loadingQueue = ref(false)
  const queueJobFilter = ref<string>('')
  const queueSortBy = ref<WorkshopQueueSortBy>('OpDatumSt')
  const queueSortDir = ref<WorkshopSortDir>('asc')
  // SWR state — queue
  const queueLastFetched = ref<Date | null>(null)
  const queueIsRevalidating = ref(false)

  // Orders overview (SWR — data přežijí tab switch)
  const ordersOverviewRows = ref<WorkshopOrderOverviewRow[]>([])
  const ordersLoading = ref(false)
  const ordersError = ref<string | null>(null)
  const ordersLastFetched = ref<Date | null>(null)
  const ordersIsRevalidating = ref(false)

  // VP list (SWR — data přežijí tab switch)
  const vpListItems = ref<VpListItem[]>([])
  const vpListLoading = ref(false)
  const vpListError = ref<string | null>(null)
  const vpListLastFetched = ref<Date | null>(null)
  const vpListIsRevalidating = ref(false)

  // Odvozené z výběru v queue (udržovány pro zpětnou kompatibilitu komponent)
  const activeJob = ref<WorkshopJob | null>(null)
  const activeOperation = ref<WorkshopOperation | null>(null)
  const materials = ref<WorkshopMaterial[]>([])
  const loadingMaterials = ref(false)
  let materialsRequestSeq = 0
  const materialSortBy = ref<WorkshopMaterialSortBy>('Material')
  const materialSortDir = ref<WorkshopSortDir>('asc')

  // Zachováno pro WorkshopTransactionForm
  const transactions = ref<WorkshopTransaction[]>([])

  // Zachováno pro kompatibilitu (WorkshopJobList není součástí nového layoutu)
  const jobs = ref<WorkshopJob[]>([])
  const operations = ref<WorkshopOperation[]>([])
  const loadingJobs = ref(false)
  const loadingOperations = ref(false)
  const operationSortBy = ref<WorkshopOperationSortBy>('OpDatumSt')
  const operationSortDir = ref<WorkshopSortDir>('asc')
  const wcFilter = ref<string>('')

  // Pracovní mód: 'setup' = seřizuji, 'production' = vyrábím
  const workMode = ref<'setup' | 'production'>('production')

  // Časovač
  const timer = ref<WorkshopTimer>({
    running: false,
    startedAt: null,
    job: null,
    suffix: null,
    operNum: null,
    inforItem: null,
    wc: null,
    mode: null,
  })
  const startingTimer = ref(false)
  let _timerInterval: ReturnType<typeof setInterval> | null = null
  const timerElapsed = ref(0)

  // === Computed ===
  const filteredJobs = computed(() => {
    if (!wcFilter.value) return jobs.value
    return jobs.value.filter((j) => j.Wc === wcFilter.value)
  })

  // === Actions — Fronta práce ===

  async function fetchQueue(opts?: {
    wc?: string
    job?: string
    sortBy?: WorkshopQueueSortBy
    sortDir?: WorkshopSortDir
  }) {
    // SWR: pokud už máme data, ukazujeme revalidating místo full loading
    if (queueItems.value.length > 0) {
      queueIsRevalidating.value = true
    } else {
      loadingQueue.value = true
    }
    try {
      queueItems.value = await workshopApi.getWcQueue({
        wc: opts?.wc,
        job: opts?.job,
        sort_by: opts?.sortBy ?? queueSortBy.value,
        sort_dir: opts?.sortDir ?? queueSortDir.value,
      })
      queueLastFetched.value = new Date()
    } catch {
      ui.showError('Nepodařilo se načíst frontu práce z Inforu')
    } finally {
      loadingQueue.value = false
      queueIsRevalidating.value = false
    }
  }

  async function fetchQueueIfStale(
    opts?: { wc?: string; job?: string; sortBy?: WorkshopQueueSortBy; sortDir?: WorkshopSortDir },
    staleMs = 30000,
  ) {
    if (queueLastFetched.value && Date.now() - queueLastFetched.value.getTime() < staleMs) {
      return // data jsou fresh
    }
    await fetchQueue(opts)
  }

  async function selectQueueItem(item: WorkshopQueueItem) {
    activeQueueItem.value = item
    materials.value = []

    // Derive WorkshopJob from queue item (pro zpětnou kompatibilitu komponent)
    activeJob.value = {
      Job: item.Job,
      Suffix: item.Suffix,
      Type: 'J',
      Wc: item.Wc,
      OperNum: item.OperNum,
      DerJobItem: item.DerJobItem ?? '',
      JobDescription: item.JobDescription,
      JobStat: 'R',
      JobQtyReleased: item.JobQtyReleased,
      QtyComplete: item.QtyComplete,
      QtyScrapped: item.QtyScrapped,
      JshSetupHrs: item.JshSetupHrs,
      DerRunMchHrs: item.DerRunMchHrs,
    }

    // Derive WorkshopOperation from queue item (pro zpětnou kompatibilitu komponent)
    activeOperation.value = {
      Job: item.Job,
      Suffix: item.Suffix,
      OperNum: item.OperNum,
      Wc: item.Wc,
      QtyReleased: item.JobQtyReleased,
      QtyComplete: item.QtyComplete,
      ScrapQty: item.QtyScrapped,
      SetupHrs: item.JshSetupHrs,
      RunHrs: item.DerRunMchHrs,
      OpDatumSt: item.OpDatumSt,
      OpDatumSp: item.OpDatumSp,
    }

    // Načti materiály pro tuto operaci
    await fetchMaterials(item.Job, item.OperNum, item.Suffix)
  }

  // === Actions — původní (kompatibilita) ===

  async function fetchJobs(wc?: string) {
    loadingJobs.value = true
    try {
      jobs.value = await workshopApi.getOpenJobs(wc)
    } catch {
      ui.showError('Nepodařilo se načíst zakázky z Inforu')
    } finally {
      loadingJobs.value = false
    }
  }

  async function selectJob(job: WorkshopJob) {
    activeJob.value = job
    activeOperation.value = null
    operations.value = []
    materials.value = []
    await fetchOperations(job.Job, job.Suffix)
  }

  async function fetchOperations(job: string, suffix = '0') {
    loadingOperations.value = true
    try {
      operations.value = await workshopApi.getJobOperations(job, suffix, operationSortBy.value, operationSortDir.value)
    } catch {
      ui.showError('Nepodařilo se načíst operace zakázky')
    } finally {
      loadingOperations.value = false
    }
  }

  async function selectOperation(oper: WorkshopOperation) {
    activeOperation.value = oper
    materials.value = []
    await fetchMaterials(oper.Job, oper.OperNum, oper.Suffix)
  }

  async function fetchMaterials(job: string, oper: string, suffix = '0') {
    const reqId = ++materialsRequestSeq
    loadingMaterials.value = true
    try {
      const loaded = await workshopApi.getOperationMaterials(job, oper, suffix, materialSortBy.value, materialSortDir.value)
      if (reqId === materialsRequestSeq) {
        materials.value = loaded
      }
    } catch {
      if (reqId === materialsRequestSeq) {
        materials.value = []
      }
    } finally {
      if (reqId === materialsRequestSeq) {
        loadingMaterials.value = false
      }
    }
  }

  async function createTransaction(data: WorkshopTransactionCreate): Promise<WorkshopTransaction | null> {
    try {
      const tx = await workshopApi.createTransaction(data)
      transactions.value.unshift(tx)
      return tx
    } catch {
      ui.showError('Nepodařilo se uložit transakci')
      return null
    }
  }

  async function postTransaction(txId: number) {
    try {
      const updated = await workshopApi.postTransaction(txId)
      const idx = transactions.value.findIndex((t) => t.id === txId)
      if (idx !== -1) transactions.value[idx] = updated
      if (updated.status === 'posted') {
        ui.showSuccess('Transakce odeslána do Inforu')
      } else {
        ui.showError(`Chyba při odesílání: ${updated.error_msg ?? 'Neznámá chyba'}`)
      }
      return updated
    } catch {
      ui.showError('Nepodařilo se odeslat transakci do Inforu')
      return null
    }
  }

  async function fetchMyTransactions() {
    try {
      transactions.value = await workshopApi.listMyTransactions()
    } catch {
      ui.showError('Nepodařilo se načíst transakce')
    }
  }

  async function postMaterialIssue(data: WorkshopMaterialIssueCreate): Promise<WorkshopMaterialIssueResult | null> {
    try {
      const result = await workshopApi.postMaterialIssue(data)
      const unit = (result.UM ?? '').trim()
      const qtyText = unit ? `${result.QtyIssued} ${unit}` : String(result.QtyIssued)
      ui.showSuccess(`Materiál ${result.Material}: odvedeno ${qtyText}`)
      if (activeQueueItem.value) {
        await fetchMaterials(activeQueueItem.value.Job, activeQueueItem.value.OperNum, activeQueueItem.value.Suffix)
      }
      return result
    } catch (error: unknown) {
      const detail = (
        error as { response?: { data?: { detail?: unknown } } }
      )?.response?.data?.detail
      ui.showError(typeof detail === 'string' ? detail : 'Nepodařilo se odvést materiál')
      return null
    }
  }

  function setQueueSort(sortBy: WorkshopQueueSortBy, sortDir: WorkshopSortDir) {
    queueSortBy.value = sortBy
    queueSortDir.value = sortDir
  }

  function setMaterialSort(sortBy: WorkshopMaterialSortBy, sortDir: WorkshopSortDir) {
    materialSortBy.value = sortBy
    materialSortDir.value = sortDir
  }

  function setOperationSort(sortBy: WorkshopOperationSortBy, sortDir: WorkshopSortDir) {
    operationSortBy.value = sortBy
    operationSortDir.value = sortDir
  }

  function setWorkMode(mode: 'setup' | 'production') {
    workMode.value = mode
  }

  // === Časovač ===

  async function _postSilent(txId: number): Promise<WorkshopTransaction | null> {
    try {
      const updated = await workshopApi.postTransaction(txId)
      const idx = transactions.value.findIndex((t) => t.id === txId)
      if (idx !== -1) transactions.value[idx] = updated
      return updated
    } catch {
      return null
    }
  }

  /**
   * Zahájení práce — vytvoří transakci START/SETUP_START a OKAMŽITĚ ji odešle do Inforu.
   *
   * Teprve po úspěšném postu do Inforu spustí lokální JS časovač.
   */
  async function startTimer(job: WorkshopJob, oper: WorkshopOperation): Promise<boolean> {
    if (timer.value.running) return false

    const mode = workMode.value
    const transType: WorkshopTransType = mode === 'setup' ? 'setup_start' : 'start'
    const startedAt = new Date()

    startingTimer.value = true
    try {
      const tx = await createTransaction({
        infor_job: job.Job,
        infor_suffix: job.Suffix ?? '0',
        infor_item: job.DerJobItem ?? null,
        oper_num: oper.OperNum,
        wc: oper.Wc ?? null,
        trans_type: transType,
        started_at: startedAt.toISOString(),
      })
      if (!tx) return false

      const posted = await _postSilent(tx.id)
      if (!posted || posted.status === 'failed') {
        ui.showError(`START selhal: ${posted?.error_msg ?? 'Nepodařilo se odeslat do Inforu'}`)
        return false
      }

      timer.value = {
        running: true,
        startedAt,
        job: job.Job,
        suffix: job.Suffix ?? '0',
        operNum: oper.OperNum,
        inforItem: job.DerJobItem ?? null,
        wc: oper.Wc ?? null,
        mode,
      }
      timerElapsed.value = 0
      _timerInterval = setInterval(() => {
        timerElapsed.value++
      }, 1000)

      ui.showSuccess(mode === 'setup' ? 'Seřízení zahájeno' : 'Výroba zahájena')
      return true
    } finally {
      startingTimer.value = false
    }
  }

  /**
   * Ukončení práce — vytvoří transakci STOP/SETUP_END a odešle ji do Inforu.
   *
   * opts: volitelné kusy/zmetky/dokončení pro production stop (ignorovány pro setup_end).
   */
  async function stopTimer(opts?: {
    qty_completed?: number | null
    qty_scrapped?: number | null
    oper_complete?: boolean
  }): Promise<WorkshopTransaction | null> {
    if (!timer.value.running || !timer.value.startedAt) return null

    const finishedAt = new Date()
    const startedAt = timer.value.startedAt
    const mode = timer.value.mode ?? 'production'
    const jobNum = timer.value.job!
    const suffix = timer.value.suffix ?? '0'
    const operNum = timer.value.operNum!
    const inforItem = timer.value.inforItem
    const wc = timer.value.wc
    const transType: WorkshopTransType = mode === 'setup' ? 'setup_end' : 'stop'

    const actualHours = (finishedAt.getTime() - startedAt.getTime()) / 3_600_000

    const tx = await createTransaction({
      infor_job: jobNum,
      infor_suffix: suffix,
      infor_item: inforItem,
      oper_num: operNum,
      wc,
      trans_type: transType,
      actual_hours: Math.round(actualHours * 10000) / 10000,
      started_at: startedAt.toISOString(),
      finished_at: finishedAt.toISOString(),
      qty_completed: opts?.qty_completed ?? null,
      qty_scrapped: opts?.qty_scrapped ?? null,
      oper_complete: opts?.oper_complete ?? false,
    })
    if (!tx) return null

    const posted = await _postSilent(tx.id)
    if (posted?.status === 'posted') {
      if (_timerInterval) {
        clearInterval(_timerInterval)
        _timerInterval = null
      }
      timer.value = {
        running: false,
        startedAt: null,
        job: null,
        suffix: null,
        operNum: null,
        inforItem: null,
        wc: null,
        mode: null,
      }
      timerElapsed.value = 0
      ui.showSuccess(mode === 'setup' ? 'Seřízení ukončeno a odesláno' : 'Čas uložen a odeslán do Inforu')
      return posted
    } else {
      ui.showError(
        `STOP selhal: ${posted?.error_msg ?? 'Nepodařilo se odeslat do Inforu'} ` +
        'Operace zůstává spuštěná.',
      )
      return null
    }
  }

  // === Actions — Orders Overview (SWR) ===

  async function fetchOrders(opts?: {
    due_from?: string
    due_to?: string
    search?: string
    limit?: number
  }) {
    if (ordersOverviewRows.value.length > 0) {
      ordersIsRevalidating.value = true
    } else {
      ordersLoading.value = true
    }
    ordersError.value = null
    try {
      ordersOverviewRows.value = await workshopApi.getOrdersOverview({
        due_from: opts?.due_from,
        due_to: opts?.due_to,
        search: opts?.search,
        limit: opts?.limit ?? 2000,
      })
      ordersLastFetched.value = new Date()
    } catch (e: unknown) {
      const detail = (
        e as { response?: { data?: { detail?: unknown } } }
      )?.response?.data?.detail
      ordersError.value = typeof detail === 'string' ? detail : 'Nepodařilo se načíst přehled zakázek'
      ordersOverviewRows.value = []
    } finally {
      ordersLoading.value = false
      ordersIsRevalidating.value = false
    }
  }

  async function fetchOrdersIfStale(
    opts?: { due_from?: string; due_to?: string; search?: string; limit?: number },
    staleMs = 60000,
  ) {
    if (ordersLastFetched.value && Date.now() - ordersLastFetched.value.getTime() < staleMs) {
      return
    }
    await fetchOrders(opts)
  }

  // === Actions — VP List (SWR) ===

  async function fetchVpList(opts?: {
    stat?: string
    search?: string
    wc?: string
    sort_by?: string
    sort_dir?: 'asc' | 'desc'
    limit?: number
  }) {
    if (vpListItems.value.length > 0) {
      vpListIsRevalidating.value = true
    } else {
      vpListLoading.value = true
    }
    vpListError.value = null
    try {
      vpListItems.value = await workshopApi.getVpList({
        stat: opts?.stat,
        search: opts?.search,
        wc: opts?.wc,
        sort_by: opts?.sort_by,
        sort_dir: opts?.sort_dir,
        limit: opts?.limit ?? 500,
      })
      vpListLastFetched.value = new Date()
    } catch (e: unknown) {
      const detail = (
        e as { response?: { data?: { detail?: unknown } } }
      )?.response?.data?.detail
      vpListError.value = typeof detail === 'string' ? detail : 'Nepodařilo se načíst výrobní příkazy'
      vpListItems.value = []
    } finally {
      vpListLoading.value = false
      vpListIsRevalidating.value = false
    }
  }

  async function fetchVpListIfStale(
    opts?: { stat?: string; search?: string; wc?: string; sort_by?: string; sort_dir?: 'asc' | 'desc'; limit?: number },
    staleMs = 60000,
  ) {
    if (vpListLastFetched.value && Date.now() - vpListLastFetched.value.getTime() < staleMs) {
      return
    }
    await fetchVpList(opts)
  }

  function resetState() {
    activeQueueItem.value = null
    activeJob.value = null
    activeOperation.value = null
    operations.value = []
    materials.value = []
    if (_timerInterval) {
      clearInterval(_timerInterval)
      _timerInterval = null
    }
    timer.value = {
      running: false,
      startedAt: null,
      job: null,
      suffix: null,
      operNum: null,
      inforItem: null,
      wc: null,
      mode: null,
    }
    timerElapsed.value = 0
  }

  return {
    // State — fronta práce
    queueItems,
    activeQueueItem,
    loadingQueue,
    queueJobFilter,
    queueSortBy,
    queueSortDir,
    queueLastFetched,
    queueIsRevalidating,
    // State — orders overview (SWR)
    ordersOverviewRows,
    ordersLoading,
    ordersError,
    ordersLastFetched,
    ordersIsRevalidating,
    // State — VP list (SWR)
    vpListItems,
    vpListLoading,
    vpListError,
    vpListLastFetched,
    vpListIsRevalidating,
    // State — odvozené + sdílené
    activeJob,
    activeOperation,
    materials,
    transactions,
    loadingMaterials,
    materialSortBy,
    materialSortDir,
    workMode,
    timer,
    timerElapsed,
    startingTimer,
    // State — kompatibilita
    jobs,
    operations,
    loadingJobs,
    loadingOperations,
    operationSortBy,
    operationSortDir,
    wcFilter,
    // Computed
    filteredJobs,
    // Actions — fronta
    fetchQueue,
    fetchQueueIfStale,
    setQueueSort,
    selectQueueItem,
    // Actions — orders overview
    fetchOrders,
    fetchOrdersIfStale,
    // Actions — VP list
    fetchVpList,
    fetchVpListIfStale,
    // Actions — data
    fetchJobs,
    selectJob,
    fetchOperations,
    selectOperation,
    fetchMaterials,
    setMaterialSort,
    setOperationSort,
    postMaterialIssue,
    createTransaction,
    postTransaction,
    fetchMyTransactions,
    setWorkMode,
    // Actions — časovač
    startTimer,
    stopTimer,
    resetState,
  }
})
