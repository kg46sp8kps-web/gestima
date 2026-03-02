<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'
import { useUiStore } from '@/stores/ui'
import * as workshopApi from '@/api/workshop'
import * as tsdApi from '@/api/industreamTsd'
import * as tsdFiddlerApi from '@/api/tsdFiddler'
import type { MachinePlanItem, WorkshopMaterial } from '@/types/workshop'
import Input from '@/components/ui/Input.vue'
import InlineDocViewer from '../shared/InlineDocViewer.vue'

const props = defineProps<{
  job: string
  oper: string
}>()

const router = useRouter()
const operator = useOperatorStore()
const ui = useUiStore()

const loading = ref(true)
const queueItem = ref<MachinePlanItem | null>(null)
const materials = ref<WorkshopMaterial[]>([])
const loadingMaterials = ref(false)

// Timer state
const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | null = null

// TSD state — single code path: local start → Infor Presunout on end
const isRunning = ref(false)
const isSetup = ref(false)
const startedAt = ref<number>(0) // epoch ms for timer
const submitting = ref(false)
const qtyCompleted = ref<number | undefined>(undefined)
const qtyScrapped = ref<number | undefined>(undefined)
const error = ref<string>('')

// FIDDLER state — Fiddler-verified START/END pairing with machine transactions
const fiddlerRunning = ref(false)
const fiddlerSetup = ref(false)
const fiddlerStartedAt = ref<number>(0)
const fiddlerSubmitting = ref(false)
const fiddlerQtyCompleted = ref<number | undefined>(undefined)
const fiddlerQtyScrapped = ref<number | undefined>(undefined)
const fiddlerError = ref<string>('')

const fiddlerElapsed = computed(() => {
  if (!fiddlerRunning.value || !fiddlerStartedAt.value) return ''
  const diff = Math.max(0, Math.floor((now.value - fiddlerStartedAt.value) / 1000))
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const elapsed = computed(() => {
  if (!isRunning.value || !startedAt.value) return ''
  const diff = Math.max(0, Math.floor((now.value - startedAt.value) / 1000))
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

onMounted(async () => {
  ticker = setInterval(() => { now.value = Date.now() }, 1000)
  await loadData()
})

onUnmounted(() => {
  if (ticker) clearInterval(ticker)
})

async function loadData() {
  loading.value = true
  loadingMaterials.value = true
  try {
    // Parallel fetch: job data (DB-first, <10ms) + materials (Infor, ~500ms)
    const [flatItems, mats] = await Promise.all([
      workshopApi.getMachinePlan({ job: props.job }),
      workshopApi.getOperationMaterials(props.job, props.oper, '0').catch(() => [] as WorkshopMaterial[]),
    ])

    queueItem.value = flatItems.find(
      i => i.Job === props.job && i.OperNum === props.oper,
    ) ?? null

    materials.value = mats

    // If we found suffix, re-fetch materials with correct suffix (only if different from '0')
    if (queueItem.value && queueItem.value.Suffix && queueItem.value.Suffix !== '0') {
      try {
        materials.value = await workshopApi.getOperationMaterials(
          props.job, props.oper, queueItem.value.Suffix,
        )
      } catch { /* keep first fetch result */ }
    }

  } finally {
    loading.value = false
    loadingMaterials.value = false
  }
}

function formatDate(d: string | null | undefined): string {
  if (!d) return '-'
  if (d.length >= 8 && /^\d{8}/.test(d)) {
    return `${d.slice(6, 8)}.${d.slice(4, 6)}.${d.slice(0, 4)}`
  }
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return d
  return dt.toLocaleDateString('cs-CZ')
}

function statClass(stat: string | undefined): string {
  switch (stat) {
    case 'R': return 'stat-badge stat-badge--r'
    case 'F': return 'stat-badge stat-badge--f'
    case 'S': return 'stat-badge stat-badge--s'
    case 'W': return 'stat-badge stat-badge--w'
    default: return 'stat-badge'
  }
}

// === Document viewer ===
const docViewerMode = ref<'pdf' | '3d' | 'all'>('all')
const docViewerOpen = ref(false)

function openPdf() {
  if (!queueItem.value?.DerJobItem) return
  docViewerMode.value = 'pdf'
  docViewerOpen.value = true
}

function open3d() {
  if (!queueItem.value?.DerJobItem) return
  docViewerMode.value = '3d'
  docViewerOpen.value = true
}

// === VP detail (all operations) ===
const vpDetailOpen = ref(false)
const vpOperations = ref<import('@/types/workshop').WorkshopOperation[]>([])
const loadingVpOps = ref(false)

async function openVpDetail() {
  if (!queueItem.value) return
  vpDetailOpen.value = true
  loadingVpOps.value = true
  try {
    vpOperations.value = await workshopApi.getJobOperations(
      queueItem.value.Job,
      queueItem.value.Suffix ?? '0',
      'OperNum',
      'asc',
    )
  } catch {
    vpOperations.value = []
  } finally {
    loadingVpOps.value = false
  }
}

function vpOpProgress(op: import('@/types/workshop').WorkshopOperation): number {
  if (!op.QtyReleased || op.QtyReleased <= 0) return 0
  return Math.min(100, Math.round(((op.QtyComplete ?? 0) / op.QtyReleased) * 100))
}

// === TSD handlers — single code path ===

function _tsdReq(): tsdApi.TsdStartRequest | null {
  if (!queueItem.value) return null
  return {
    job: queueItem.value.Job,
    suffix: queueItem.value.Suffix ?? '0',
    oper_num: queueItem.value.OperNum,
    wc: queueItem.value.Wc ?? '',
    item: queueItem.value.DerJobItem ?? '',
  }
}

function extractError(e: unknown): string {
  if (e && typeof e === 'object') {
    const obj = e as Record<string, unknown>
    const resp = obj.response as Record<string, unknown> | undefined
    const data = resp?.data as Record<string, unknown> | undefined
    if (typeof data?.detail === 'string') return data.detail
    if (typeof obj.message === 'string') return obj.message
  }
  return 'Chyba'
}

async function startSetup() {
  const req = _tsdReq()
  if (!req || isRunning.value) return
  operator.touchActivity()
  error.value = ''
  try {
    await tsdApi.startSetup(req)
    isRunning.value = true
    isSetup.value = true
    startedAt.value = Date.now()
    ui.showSuccess('Seřízení zahájeno')
  } catch (e: unknown) {
    error.value = extractError(e)
    ui.showError(`START SETUP: ${error.value}`)
  }
}

async function startProduction() {
  const req = _tsdReq()
  if (!req || isRunning.value) return
  operator.touchActivity()
  error.value = ''
  try {
    await tsdApi.startWork(req)
    isRunning.value = true
    isSetup.value = false
    startedAt.value = Date.now()
    ui.showSuccess('Výroba zahájena')
  } catch (e: unknown) {
    error.value = extractError(e)
    ui.showError(`START WORK: ${error.value}`)
  }
}

async function stopWork() {
  if (!isRunning.value) return
  const req = _tsdReq()
  if (!req) return
  operator.touchActivity()
  submitting.value = true
  error.value = ''
  try {
    if (isSetup.value) {
      // End Setup → auto-starts Work
      await tsdApi.endSetup(req)
      // Setup ended, work auto-started — switch to production mode
      isSetup.value = false
      startedAt.value = Date.now() // reset timer for production phase
      ui.showSuccess('Seřízení ukončeno, výroba zahájena')
    } else {
      // End Work → ends run + machine run
      await tsdApi.endWork({
        ...req,
        qty_complete: qtyCompleted.value ?? 0,
        qty_scrapped: qtyScrapped.value ?? 0,
      })
      isRunning.value = false
      startedAt.value = 0
      qtyCompleted.value = undefined
      qtyScrapped.value = undefined
      await operator.fetchStats()
      ui.showSuccess('Práce ukončena a odeslána do Inforu')
    }
  } catch (e: unknown) {
    error.value = extractError(e)
    ui.showError(`STOP: ${error.value}`)
  } finally {
    submitting.value = false
  }
}

// === FIDDLER handlers — START/END pairing with machine transactions ===

function _fiddlerReq(): tsdFiddlerApi.TsdFiddlerStartRequest | null {
  if (!queueItem.value) return null
  return {
    job: queueItem.value.Job,
    suffix: queueItem.value.Suffix ?? '0',
    oper_num: queueItem.value.OperNum,
    item: queueItem.value.DerJobItem ?? '',
    whse: 'MAIN',
  }
}

async function fiddlerStartSetup() {
  const req = _fiddlerReq()
  if (!req || fiddlerRunning.value) return
  operator.touchActivity()
  fiddlerError.value = ''
  try {
    await tsdFiddlerApi.startSetup(req)
    fiddlerRunning.value = true
    fiddlerSetup.value = true
    fiddlerStartedAt.value = Date.now()
    ui.showSuccess('FIDDLER: Serizeni zahajeno')
  } catch (e: unknown) {
    fiddlerError.value = extractError(e)
    ui.showError(`FIDDLER START SETUP: ${fiddlerError.value}`)
  }
}

async function fiddlerStartProduction() {
  const req = _fiddlerReq()
  if (!req || fiddlerRunning.value) return
  operator.touchActivity()
  fiddlerError.value = ''
  try {
    const result = await tsdFiddlerApi.startWork(req)
    fiddlerRunning.value = true
    fiddlerSetup.value = false
    fiddlerStartedAt.value = Date.now()
    ui.showSuccess(`FIDDLER: Vyroba zahajena (stroj=${result.stroj ?? '?'})`)
  } catch (e: unknown) {
    fiddlerError.value = extractError(e)
    ui.showError(`FIDDLER START WORK: ${fiddlerError.value}`)
  }
}

async function fiddlerStopWork() {
  if (!fiddlerRunning.value) return
  const req = _fiddlerReq()
  if (!req) return
  operator.touchActivity()
  fiddlerSubmitting.value = true
  fiddlerError.value = ''
  try {
    if (fiddlerSetup.value) {
      // End Setup → auto-starts Work
      const result = await tsdFiddlerApi.endSetup(req)
      fiddlerSetup.value = false
      fiddlerStartedAt.value = Date.now()
      ui.showSuccess(`FIDDLER: Serizeni ukonceno, vyroba zahajena (stroj=${result.stroj ?? '?'})`)
    } else {
      // End Work
      await tsdFiddlerApi.endWork({
        ...req,
        qty_complete: fiddlerQtyCompleted.value ?? 0,
        qty_scrapped: fiddlerQtyScrapped.value ?? 0,
      })
      fiddlerRunning.value = false
      fiddlerStartedAt.value = 0
      fiddlerQtyCompleted.value = undefined
      fiddlerQtyScrapped.value = undefined
      await operator.fetchStats()
      ui.showSuccess('FIDDLER: Prace ukoncena (hodiny pocita Infor ze START/END)')
    }
  } catch (e: unknown) {
    fiddlerError.value = extractError(e)
    ui.showError(`FIDDLER STOP: ${fiddlerError.value}`)
  } finally {
    fiddlerSubmitting.value = false
  }
}

function goBack() {
  router.back()
}
</script>

<template>
  <div class="detail">
    <!-- Back button -->
    <button class="back-btn" @click="goBack">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
      Zpět
    </button>

    <div v-if="loading" class="detail-loading">Načítám...</div>

    <template v-else-if="queueItem">
      <!-- Tier banner -->
      <div v-if="queueItem.IsHot" class="tier-banner tier-banner--hot">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 23c-3.6 0-7-2.4-7-7 0-3.3 2.3-5.8 4-7.5.5-.5 1.5-.2 1.5.5v2.2c0 .4.5.6.8.3C13.4 9.5 15 6.5 15 4c0-.7.8-1 1.3-.5C18.7 6 21 9.5 21 13c0 5.5-4 10-9 10z"/></svg>
        HOT
      </div>
      <div v-else-if="queueItem.Tier === 'urgent'" class="tier-banner tier-banner--urgent">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        URGENT
      </div>

      <!-- Job info -->
      <div class="info-section">
        <div class="info-row">
          <span class="info-label">Zakázka</span>
          <span class="info-value"><strong>{{ queueItem.Job }}</strong></span>
        </div>
        <div class="info-row">
          <span class="info-label">Operace</span>
          <span class="info-value">{{ queueItem.OperNum }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Pracoviště</span>
          <span class="info-value">{{ queueItem.Wc }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Stav VP</span>
          <span class="info-value">
            <span :class="statClass(queueItem.JobStat)">{{ queueItem.JobStat }}</span>
          </span>
        </div>
        <div v-if="queueItem.DerJobItem" class="info-row">
          <span class="info-label">Artikl</span>
          <span class="info-value">{{ queueItem.DerJobItem }}</span>
        </div>
        <div v-if="queueItem.JobDescription" class="info-row">
          <span class="info-label">Popis</span>
          <span class="info-value">{{ queueItem.JobDescription }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Množství</span>
          <span class="info-value">
            {{ queueItem.QtyComplete ?? 0 }} / {{ queueItem.JobQtyReleased ?? '?' }} ks
          </span>
        </div>
        <div v-if="queueItem.OrderDueDate" class="info-row">
          <span class="info-label">Termín zakázky</span>
          <span class="info-value" :class="{ 'due-hot': queueItem.IsHot, 'due-urgent': queueItem.Tier === 'urgent' }">
            {{ formatDate(queueItem.OrderDueDate) }}
          </span>
        </div>
        <div v-if="queueItem.CoNum" class="info-row">
          <span class="info-label">Zakázka CO</span>
          <span class="info-value">{{ queueItem.CoNum }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Plán. začátek op.</span>
          <span class="info-value">{{ formatDate(queueItem.OpDatumSt) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Plán. konec op.</span>
          <span class="info-value">{{ formatDate(queueItem.OpDatumSp) }}</span>
        </div>
      </div>

      <!-- Document buttons: PDF + 3D separately -->
      <div v-if="queueItem.DerJobItem" class="doc-btn-row">
        <button class="doc-btn-full" @click="openPdf">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Výkres
        </button>
        <button class="doc-btn-full" @click="open3d">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
            <line x1="12" y1="22.08" x2="12" y2="12"/>
          </svg>
          3D Model
        </button>
      </div>

      <!-- VP detail button -->
      <button class="doc-btn-full" @click="openVpDetail">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="9" y1="21" x2="9" y2="9"/>
        </svg>
        Detail VP — všechny operace
      </button>

      <!-- Inline doc viewer overlay (fullscreen) -->
      <InlineDocViewer
        :item="queueItem.DerJobItem ?? ''"
        :visible="docViewerOpen"
        :mode="docViewerMode"
        @close="docViewerOpen = false"
      />

      <!-- VP detail overlay -->
      <div v-if="vpDetailOpen" class="vp-overlay" @click.self="vpDetailOpen = false">
        <div class="vp-panel">
          <div class="vp-header">
            <h3 class="vp-title">{{ queueItem.Job }} — operace</h3>
            <button class="vp-close" @click="vpDetailOpen = false">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="vp-content">
            <div v-if="loadingVpOps" class="vp-loading">Načítám operace...</div>
            <div v-else-if="vpOperations.length === 0" class="vp-loading">Žádné operace</div>
            <div v-else class="vp-ops-list">
              <div
                v-for="op in vpOperations"
                :key="op.OperNum"
                :class="['vp-op', { 'vp-op--current': op.OperNum === props.oper }]"
              >
                <div class="vp-op-head">
                  <span class="vp-op-num">Op {{ op.OperNum }}</span>
                  <span class="vp-op-wc">{{ op.Wc }}</span>
                  <span class="vp-op-pct">{{ vpOpProgress(op) }}%</span>
                </div>
                <div class="vp-op-bar">
                  <div
                    class="vp-op-bar-fill"
                    :style="{ width: vpOpProgress(op) + '%' }"
                  />
                </div>
                <div class="vp-op-qty">
                  {{ op.QtyComplete ?? 0 }} / {{ op.QtyReleased ?? '?' }} ks
                  <span v-if="op.ScrapQty" class="vp-op-scrap">
                    ({{ op.ScrapQty }} zmetky)
                  </span>
                </div>
                <div v-if="op.OpDatumSt || op.OpDatumSp" class="vp-op-dates">
                  {{ formatDate(op.OpDatumSt) }} → {{ formatDate(op.OpDatumSp) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action area — single code path: TSD Presunout (WrapperSp TT=4 + SFC34 + Kapacity) -->
      <div class="action-area">
        <div v-if="error" class="error-msg">{{ error }}</div>

        <!-- Not running: show start buttons -->
        <template v-if="!isRunning">
          <div class="start-grid">
            <button class="action-square setup" @click="startSetup">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
              <span>SEŘÍZENÍ</span>
            </button>
            <button class="action-square start" @click="startProduction">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>VÝROBA</span>
            </button>
          </div>
        </template>

        <!-- Running: show timer + stop -->
        <template v-else>
          <div class="running-panel">
            <div :class="['running-timer', { 'running-timer--setup': isSetup }]">
              <span :class="['running-dot', { setup: isSetup }]" />
              <span class="running-label">{{ isSetup ? 'Seřízení' : 'Výroba' }}</span>
              <span class="running-elapsed">{{ elapsed }}</span>
            </div>

            <!-- Qty inputs (only for production, not setup) -->
            <div v-if="!isSetup" class="qty-inputs">
              <div class="qty-group">
                <label class="qty-label">Kusy OK</label>
                <Input
                  :model-value="qtyCompleted ?? null"
                  @update:modelValue="(v) => { qtyCompleted = v == null ? undefined : Number(v) }"
                  :bare="true"
                  type="number"
                  class="qty-input"
                  inputmode="numeric"
                  :min="0"
                  placeholder="0"
                />
              </div>
              <div class="qty-group">
                <label class="qty-label">Zmetky</label>
                <Input
                  :model-value="qtyScrapped ?? null"
                  @update:modelValue="(v) => { qtyScrapped = v == null ? undefined : Number(v) }"
                  :bare="true"
                  type="number"
                  class="qty-input scrap"
                  inputmode="numeric"
                  :min="0"
                  placeholder="0"
                />
              </div>
            </div>

            <button
              class="action-btn stop"
              :disabled="submitting"
              @click="stopWork"
            >
              <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="1"/>
              </svg>
              {{ submitting ? 'Odesílám...' : (isSetup ? 'UKONČIT SEŘÍZENÍ' : 'UKONČIT PRÁCI') }}
            </button>
          </div>
        </template>
      </div>

      <!-- FIDDLER (START/END) — Fiddler-verified pairing with machine transactions -->
      <div class="fiddler-section">
        <h3 class="section-title fiddler-title">FIDDLER (START/END)</h3>

        <div v-if="fiddlerError" class="error-msg">{{ fiddlerError }}</div>

        <!-- Not running: show FIDDLER start buttons -->
        <template v-if="!fiddlerRunning">
          <div class="start-grid">
            <button class="action-square fiddler-setup" @click="fiddlerStartSetup">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
              <span>SERIZENI (FIDDLER)</span>
            </button>
            <button class="action-square fiddler-start" @click="fiddlerStartProduction">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>VYROBA (FIDDLER)</span>
            </button>
          </div>
        </template>

        <!-- Running: show FIDDLER timer + stop -->
        <template v-else>
          <div class="running-panel">
            <div :class="['running-timer fiddler-timer', { 'fiddler-timer--setup': fiddlerSetup }]">
              <span :class="['running-dot fiddler-dot', { setup: fiddlerSetup }]" />
              <span class="running-label">{{ fiddlerSetup ? 'Serizeni (F)' : 'Vyroba (F)' }}</span>
              <span class="running-elapsed fiddler-elapsed">{{ fiddlerElapsed }}</span>
            </div>

            <!-- Qty inputs (only for production, not setup) -->
            <div v-if="!fiddlerSetup" class="qty-inputs">
              <div class="qty-group">
                <label class="qty-label">Kusy OK</label>
                <Input
                  :model-value="fiddlerQtyCompleted ?? null"
                  @update:modelValue="(v) => { fiddlerQtyCompleted = v == null ? undefined : Number(v) }"
                  :bare="true"
                  type="number"
                  class="qty-input"
                  inputmode="numeric"
                  :min="0"
                  placeholder="0"
                />
              </div>
              <div class="qty-group">
                <label class="qty-label">Zmetky</label>
                <Input
                  :model-value="fiddlerQtyScrapped ?? null"
                  @update:modelValue="(v) => { fiddlerQtyScrapped = v == null ? undefined : Number(v) }"
                  :bare="true"
                  type="number"
                  class="qty-input scrap"
                  inputmode="numeric"
                  :min="0"
                  placeholder="0"
                />
              </div>
            </div>

            <button
              class="action-btn fiddler-stop"
              :disabled="fiddlerSubmitting"
              @click="fiddlerStopWork"
            >
              <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="1"/>
              </svg>
              {{ fiddlerSubmitting ? 'Odesílám...' : (fiddlerSetup ? 'UKONCIT SERIZENI (F)' : 'UKONCIT (FIDDLER)') }}
            </button>
          </div>
        </template>
      </div>

      <!-- Materials section -->
      <div v-if="materials.length > 0" class="materials-section">
        <h3 class="section-title">Materiály</h3>
        <div class="mat-list">
          <div v-for="mat in materials" :key="mat.Material" class="mat-item">
            <div class="mat-info">
              <strong>{{ mat.Material }}</strong>
              <span v-if="mat.Desc" class="mat-desc">{{ mat.Desc }}</span>
            </div>
            <div class="mat-qty">
              {{ mat.QtyIssued ?? 0 }} / {{ mat.TotCons ?? '?' }} {{ mat.UM ?? '' }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="detail-loading">Operace nenalezena</div>
  </div>
</template>

<style scoped>
.detail {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--t3);
  font-size: 14px;
  font-family: var(--font);
  cursor: pointer;
  padding: 4px 0;
  -webkit-tap-highlight-color: transparent;
  align-self: flex-start;
}
.back-btn:active { color: var(--t1); }

/* Tier banner */
.tier-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--rs, 8px);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.tier-banner--hot {
  background: color-mix(in srgb, var(--red, #ef5350) 12%, transparent);
  border: 1px solid rgba(239, 83, 80, 0.3);
  color: var(--red, #ef5350);
  animation: pulse-tier 1.5s ease-in-out infinite;
}
.tier-banner--urgent {
  background: color-mix(in srgb, var(--amber, #ff9800) 12%, transparent);
  border: 1px solid rgba(255, 152, 0, 0.3);
  color: var(--amber, #ff9800);
}
@keyframes pulse-tier {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Status badges */
.stat-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
  line-height: 1;
}
.stat-badge--r {
  background: color-mix(in srgb, var(--green, #4caf50) 20%, transparent);
  color: var(--green, #4caf50);
}
.stat-badge--f {
  background: color-mix(in srgb, var(--amber, #ff9800) 20%, transparent);
  color: var(--amber, #ff9800);
}
.stat-badge--s {
  background: color-mix(in srgb, var(--blue, #2196f3) 20%, transparent);
  color: var(--blue, #2196f3);
}
.stat-badge--w {
  background: color-mix(in srgb, var(--t4) 20%, transparent);
  color: var(--t4);
}

/* Due date urgency */
.due-hot { color: var(--red, #ef5350) !important; font-weight: 600; }
.due-urgent { color: var(--amber, #ff9800) !important; font-weight: 600; }

.detail-loading {
  color: var(--t4);
  font-size: 14px;
  text-align: center;
  padding: 40px 0;
}

/* Info section */
.info-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  padding: 14px 16px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.info-label {
  font-size: 13px;
  color: var(--t4);
  flex-shrink: 0;
}
.info-value {
  font-size: 14px;
  color: var(--t1);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Document buttons */
.doc-btn-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.doc-btn-full {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  width: 100%;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  color: var(--t2);
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 100ms, border-color 100ms;
}
.doc-btn-full:active {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--t4);
}

/* Action buttons */
.action-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Start grid — two buttons side by side, 50/50 width, 3:1 aspect ratio */
.start-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.action-square {
  aspect-ratio: 3 / 1;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: none;
  border-radius: var(--rs, 8px);
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font);
  letter-spacing: 0.04em;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 100ms;
}
.action-square:active {
  opacity: 0.8;
}
.action-square.start {
  background: rgba(76, 175, 80, 0.15);
  color: var(--ok);
  border: 2px solid rgba(76, 175, 80, 0.3);
}
.action-square.setup {
  background: rgba(255, 193, 7, 0.1);
  color: var(--warn);
  border: 2px solid rgba(255, 193, 7, 0.2);
}

.action-btn {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: none;
  border-radius: var(--rs, 8px);
  font-size: 18px;
  font-weight: 700;
  font-family: var(--font);
  letter-spacing: 0.04em;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 100ms;
}
.action-btn:active:not(:disabled) {
  opacity: 0.8;
}
.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.stop {
  background: rgba(229, 57, 53, 0.15);
  color: var(--red);
  border: 2px solid rgba(229, 57, 53, 0.3);
  margin-top: 8px;
}

/* Running panel */
.running-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.running-timer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  background: rgba(76, 175, 80, 0.06);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: var(--rs, 8px);
}

.running-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--ok);
  animation: pulse-glow 1.5s ease-in-out infinite;
}
.running-dot.setup {
  background: var(--warn);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.5); }
  50% { box-shadow: 0 0 0 6px rgba(76, 175, 80, 0); }
}

.running-label {
  font-size: 14px;
  color: var(--t2);
}

.running-elapsed {
  font-size: 28px;
  font-weight: 700;
  color: var(--ok);
  font-variant-numeric: tabular-nums;
}

/* Qty inputs */
.qty-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.qty-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.qty-label {
  font-size: 12px;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.qty-input {
  height: 56px;
  font-size: 24px;
  font-weight: 600;
  font-family: var(--font);
  text-align: center;
  color: var(--t1);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  outline: none;
  -webkit-appearance: none;
}
.qty-input:focus {
  border-color: var(--red, #e53935);
  background: rgba(255, 255, 255, 0.06);
}
.qty-input.scrap:focus {
  border-color: var(--warn);
}

/* Materials */
.materials-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0;
}

.mat-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  gap: 8px;
}
.mat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  font-size: 14px;
  color: var(--t1);
}
.mat-desc {
  font-size: 12px;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mat-qty {
  font-size: 13px;
  color: var(--t2);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* Error message */
.error-msg {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--red, #ef5350);
  background: rgba(239, 83, 80, 0.08);
  border: 1px solid rgba(239, 83, 80, 0.2);
  border-radius: 6px;
  word-break: break-word;
}

.running-timer--setup {
  background: rgba(255, 193, 7, 0.06) !important;
  border-color: rgba(255, 193, 7, 0.2) !important;
}

/* VP detail overlay */
.vp-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 16px;
}
.vp-panel {
  width: 100%;
  max-width: 600px;
  background: var(--ground, #181a1f);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.vp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.vp-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}
.vp-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--t3);
  cursor: pointer;
  border-radius: 4px;
}
.vp-close:active {
  background: rgba(255, 255, 255, 0.06);
}
.vp-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}
.vp-loading {
  color: var(--t4);
  font-size: 14px;
  text-align: center;
  padding: 30px 0;
}
.vp-ops-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.vp-op {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
}
.vp-op--current {
  border-color: var(--red, #e53935);
  background: rgba(229, 57, 53, 0.06);
}
.vp-op-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.vp-op-num {
  font-size: 14px;
  font-weight: 600;
  color: var(--t1);
}
.vp-op-wc {
  font-size: 12px;
  color: var(--t3);
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 0 5px;
}
.vp-op-pct {
  margin-left: auto;
  font-size: 13px;
  font-weight: 600;
  color: var(--t2);
  font-variant-numeric: tabular-nums;
}
.vp-op-bar {
  height: 5px;
  background: var(--b1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.vp-op-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--green, #4caf50);
  transition: width 300ms ease;
}
.vp-op--current .vp-op-bar-fill {
  background: var(--red, #e53935);
}
.vp-op-qty {
  font-size: 12px;
  color: var(--t3);
  font-variant-numeric: tabular-nums;
}
.vp-op-scrap {
  color: var(--warn);
}
.vp-op-dates {
  font-size: 11px;
  color: var(--t4);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

/* FIDDLER section */
.fiddler-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--b2);
}
.fiddler-title {
  color: var(--cyan, #00bcd4) !important;
}
.action-square.fiddler-setup {
  background: rgba(0, 188, 212, 0.08);
  color: var(--cyan, #00bcd4);
  border: 2px solid rgba(0, 188, 212, 0.3);
  font-size: 13px;
}
.action-square.fiddler-start {
  background: rgba(0, 188, 212, 0.08);
  color: var(--cyan, #00bcd4);
  border: 2px solid rgba(0, 188, 212, 0.3);
  font-size: 13px;
}
.fiddler-timer {
  background: rgba(0, 188, 212, 0.06) !important;
  border-color: rgba(0, 188, 212, 0.2) !important;
}
.fiddler-timer--setup {
  background: rgba(0, 188, 212, 0.04) !important;
  border-color: rgba(0, 188, 212, 0.15) !important;
}
.fiddler-dot {
  background: var(--cyan, #00bcd4) !important;
}
.fiddler-elapsed {
  color: var(--cyan, #00bcd4) !important;
}
.action-btn.fiddler-stop {
  background: rgba(0, 188, 212, 0.1);
  color: var(--cyan, #00bcd4);
  border: 2px solid rgba(0, 188, 212, 0.3);
}
</style>
