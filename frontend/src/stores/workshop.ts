/** Gestima Dílna — Pinia store */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as workshopApi from '@/api/workshop'
import { useUiStore } from './ui'
import type {
  WorkshopJob,
  WorkshopQueueItem,
  WorkshopOperation,
  WorkshopMaterial,
  WorkshopTransaction,
  WorkshopTransactionCreate,
  WorkshopTimer,
  WorkshopTransType,
} from '@/types/workshop'

export const useWorkshopStore = defineStore('workshop', () => {
  const ui = useUiStore()

  // === State ===
  // Fronta práce (nový model — flat seznam operací)
  const queueItems = ref<WorkshopQueueItem[]>([])
  const activeQueueItem = ref<WorkshopQueueItem | null>(null)
  const loadingQueue = ref(false)

  // Odvozené z výběru v queue (udržovány pro zpětnou kompatibilitu komponent)
  const activeJob = ref<WorkshopJob | null>(null)
  const activeOperation = ref<WorkshopOperation | null>(null)
  const materials = ref<WorkshopMaterial[]>([])
  const loadingMaterials = ref(false)

  // Zachováno pro WorkshopTransactionForm
  const transactions = ref<WorkshopTransaction[]>([])

  // Zachováno pro kompatibilitu (WorkshopJobList není součástí nového layoutu)
  const jobs = ref<WorkshopJob[]>([])
  const operations = ref<WorkshopOperation[]>([])
  const loadingJobs = ref(false)
  const loadingOperations = ref(false)
  const wcFilter = ref<string>('')

  // Pracovní mód: 'setup' = seřizuji, 'production' = vyrábím
  const workMode = ref<'setup' | 'production'>('production')

  // Časovač
  const timer = ref<WorkshopTimer>({
    running: false,
    startedAt: null,
    job: null,
    operNum: null,
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

  async function fetchQueue(wc?: string) {
    loadingQueue.value = true
    try {
      queueItems.value = await workshopApi.getWcQueue(wc)
    } catch {
      ui.showError('Nepodařilo se načíst frontu práce z Inforu')
    } finally {
      loadingQueue.value = false
    }
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
      operations.value = await workshopApi.getJobOperations(job, suffix)
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
    loadingMaterials.value = true
    try {
      materials.value = await workshopApi.getOperationMaterials(job, oper, suffix)
    } catch {
      materials.value = []
    } finally {
      loadingMaterials.value = false
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

      timer.value = { running: true, startedAt, job: job.Job, operNum: oper.OperNum, mode }
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
    const operNum = timer.value.operNum!
    const transType: WorkshopTransType = mode === 'setup' ? 'setup_end' : 'stop'

    if (_timerInterval) {
      clearInterval(_timerInterval)
      _timerInterval = null
    }
    timer.value = { running: false, startedAt: null, job: null, operNum: null, mode: null }
    timerElapsed.value = 0

    const actualHours = (finishedAt.getTime() - startedAt.getTime()) / 3_600_000

    const tx = await createTransaction({
      infor_job: jobNum,
      infor_suffix: activeJob.value?.Suffix ?? '0',
      oper_num: operNum,
      wc: activeOperation.value?.Wc ?? null,
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
      ui.showSuccess(mode === 'setup' ? 'Seřízení ukončeno a odesláno' : 'Čas uložen a odeslán do Inforu')
    } else {
      ui.showError(`STOP selhal: ${posted?.error_msg ?? 'Nepodařilo se odeslat do Inforu'}`)
    }

    return tx
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
    timer.value = { running: false, startedAt: null, job: null, operNum: null, mode: null }
    timerElapsed.value = 0
  }

  return {
    // State — fronta práce
    queueItems,
    activeQueueItem,
    loadingQueue,
    // State — odvozené + sdílené
    activeJob,
    activeOperation,
    materials,
    transactions,
    loadingMaterials,
    workMode,
    timer,
    timerElapsed,
    startingTimer,
    // State — kompatibilita
    jobs,
    operations,
    loadingJobs,
    loadingOperations,
    wcFilter,
    // Computed
    filteredJobs,
    // Actions — fronta
    fetchQueue,
    selectQueueItem,
    // Actions — data
    fetchJobs,
    selectJob,
    fetchOperations,
    selectOperation,
    fetchMaterials,
    createTransaction,
    postTransaction,
    fetchMyTransactions,
    // Actions — časovač
    startTimer,
    stopTimer,
    resetState,
  }
})
