<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as workshopApi from '@/api/workshop'
import * as operatorApi from '@/api/operator'
import type { MachinePlanItem } from '@/types/workshop'
import type { NormDetailRow, NormPeriod, OperatorWorkcenter } from '@/types/operator'
import Input from '@/components/ui/Input.vue'
import JobCard from '../shared/JobCard.vue'

const router = useRouter()
const operator = useOperatorStore()
const auth = useAuthStore()
const ui = useUiStore()

const loadingStats = ref(false)

onMounted(async () => {
  loadingStats.value = true
  await Promise.all([
    operator.fetchActiveJobs(),
    operator.fetchTransactionAlerts(),
    operator.fetchStats(),
    operator.fetchWorkcenters(),
  ])
  loadingStats.value = false
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Dobré ráno'
  if (h < 18) return 'Dobré odpoledne'
  return 'Dobrý večer'
})

// === VP Search ===
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref<MachinePlanItem[]>([])
const showPicker = ref(false)

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  operator.touchActivity()
  searching.value = true

  try {
    const matches = await workshopApi.getMachinePlan({
      search: q,
      sort_by: 'OpDatumSt',
      sort_dir: 'asc',
      limit: 100,
    })

    if (matches.length === 0) {
      ui.showWarning('Žádné VP nenalezeny')
      searchResults.value = []
      showPicker.value = false
      return
    }

    if (matches.length === 1) {
      router.push({ name: 'terminal-job-detail', params: { job: matches[0]!.Job, oper: matches[0]!.OperNum } })
    } else {
      searchResults.value = matches
      showPicker.value = true
    }
  } catch {
    ui.showError('Chyba při vyhledávání')
  } finally {
    searching.value = false
  }
}

function selectSearchResult(item: MachinePlanItem) {
  showPicker.value = false
  searchQuery.value = ''
  searchResults.value = []
  router.push({ name: 'terminal-job-detail', params: { job: item.Job, oper: item.OperNum } })
}

function closePicker() {
  showPicker.value = false
}

// === WC Groups ===
interface WcGroup {
  label: string
  items: OperatorWorkcenter[]
}

function classifyWc(wc: string): string {
  const u = wc.toUpperCase()
  if (u.startsWith('PS') || u === 'PS') return 'pily'
  if (u.startsWith('SH') || u.startsWith('SM')) return 'soustruhy'
  if (u.startsWith('F')) return 'frezy'
  if (u === 'MECH' || u.startsWith('VS') || u.startsWith('VIB') || u.startsWith('LE')) return 'mechanika'
  return 'ostatni'
}

const wcGroups = computed<WcGroup[]>(() => {
  const filtered = operator.workcenters.filter(
    w => !w.wc.toUpperCase().startsWith('KOO') && !w.wc.toUpperCase().startsWith('OTK') && !w.wc.toUpperCase().startsWith('CLO'),
  )
  const map: Record<string, typeof filtered> = {}
  for (const wc of filtered) {
    const key = classifyWc(wc.wc)
    if (!map[key]) map[key] = []
    map[key].push(wc)
  }
  const labels: Record<string, string> = {
    pily: 'Pily',
    soustruhy: 'Soustruhy',
    frezy: 'Frézy',
    mechanika: 'Mechanika',
    ostatni: 'Ostatní',
  }
  const order = ['pily', 'soustruhy', 'frezy', 'mechanika', 'ostatni']
  return order
    .filter(k => map[k]?.length)
    .map(k => ({ label: labels[k]!, items: map[k]! }))
})

function selectWc(wc: string) {
  operator.selectWorkcenter(wc)
  router.push({ name: 'terminal-queue' })
}

function selectGroup(group: WcGroup) {
  operator.selectWorkcenterGroup(group.label, group.items.map((w: OperatorWorkcenter) => w.wc))
  router.push({ name: 'terminal-queue' })
}

function goToJobDetail(job: string, oper: string) {
  router.push({ name: 'terminal-job-detail', params: { job, oper } })
}

function transTypeLabel(type: string): string {
  if (type === 'setup_start') return 'Zahájit seřízení'
  if (type === 'setup_end') return 'Ukončit seřízení'
  if (type === 'start') return 'Zahájit výrobu'
  if (type === 'stop') return 'Ukončit výrobu'
  return type
}

function transStatusLabel(status: string): string {
  if (status === 'failed') return 'Chyba'
  if (status === 'posting') return 'Odesílá se'
  if (status === 'pending') return 'Čeká na odeslání'
  return status
}

function transSeverityClass(severity: string): string {
  if (severity === 'error') return 'tx-alert tx-alert--error'
  if (severity === 'warning') return 'tx-alert tx-alert--warning'
  return 'tx-alert'
}

const retryingTxId = ref<number | null>(null)

async function retryAlertTx(txId: number) {
  if (retryingTxId.value != null) return
  retryingTxId.value = txId
  try {
    const ok = await operator.retryTransaction(txId)
    if (ok) {
      ui.showSuccess('Transakce znovu odeslána')
      await operator.fetchStats()
    } else {
      ui.showError('Retry selhal')
    }
  } finally {
    retryingTxId.value = null
  }
}

// === Drill-down overlay ===
type DrillMode = { type: 'period'; period: NormPeriod } | { type: 'custom'; dateFrom: string; dateTo: string }
const drillDown = ref<DrillMode | null>(null)
const drillDetails = ref<NormDetailRow[]>([])
const drillLoading = ref(false)

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')
const showCustomPicker = ref(false)

const drillTitle = computed(() => {
  if (!drillDown.value) return ''
  if (drillDown.value.type === 'period') {
    const periodLabels: Record<NormPeriod, string> = { day: 'Dnes', week: 'Týden', month: 'Měsíc' }
    return `Plnění normy — ${periodLabels[drillDown.value.period]}`
  }
  return `Plnění normy — ${formatDate(drillDown.value.dateFrom)} – ${formatDate(drillDown.value.dateTo)}`
})

const drillSummaryPct = computed(() => {
  if (!drillDetails.value.length) return null
  let totalActual = 0
  let totalPlanned = 0
  for (const d of drillDetails.value) {
    totalActual += d.actual_run_min + d.actual_setup_min
    if (d.planned_run_min != null) totalPlanned += d.planned_run_min
    if (d.planned_setup_min != null) totalPlanned += d.planned_setup_min
  }
  if (totalActual <= 0 || totalPlanned <= 0) return null
  return Math.round((totalPlanned / totalActual) * 100)
})

async function openDrillDown(period: NormPeriod) {
  drillDown.value = { type: 'period', period }
  drillLoading.value = true
  try {
    drillDetails.value = await operatorApi.getNormDetails({ period })
  } catch {
    drillDetails.value = []
  } finally {
    drillLoading.value = false
  }
}

function openCustomPicker() {
  // Default: last 30 days
  const now = new Date()
  const from = new Date(now)
  from.setDate(from.getDate() - 30)
  customDateFrom.value = from.toISOString().slice(0, 10)
  customDateTo.value = now.toISOString().slice(0, 10)
  showCustomPicker.value = true
}

async function submitCustomRange() {
  if (!customDateFrom.value || !customDateTo.value) return
  showCustomPicker.value = false
  drillDown.value = { type: 'custom', dateFrom: customDateFrom.value, dateTo: customDateTo.value }
  drillLoading.value = true
  try {
    drillDetails.value = await operatorApi.getNormDetails({
      date_from: customDateFrom.value,
      date_to: customDateTo.value,
    })
  } catch {
    drillDetails.value = []
  } finally {
    drillLoading.value = false
  }
}

function closeDrillDown() {
  drillDown.value = null
  drillDetails.value = []
}

function normColorClass(pct: number | null): string {
  if (pct == null) return ''
  if (pct >= 100) return 'norm-green'
  if (pct >= 80) return 'norm-amber'
  return 'norm-red'
}

function formatPct(pct: number | null): string {
  if (pct == null) return '-'
  return `${pct}%`
}

function formatDate(d: string | null | undefined): string {
  if (!d) return '-'
  if (d.length >= 10) {
    const [y, m, day] = d.slice(0, 10).split('-')
    if (y && m && day) return `${day}.${m}.${y}`
  }
  return d
}

function barWidth(pct: number | null): string {
  if (pct == null) return '0%'
  return `${Math.min(pct, 150)}%`
}
</script>

<template>
  <div class="dash">
    <!-- Header -->
    <div class="dash-header">
      <div class="dash-greeting">{{ greeting }}, <strong>{{ auth.user?.username }}</strong></div>
      <div v-if="operator.selectedWc" class="dash-wc">
        Pracoviště: <strong>{{ operator.selectedWc }}</strong>
      </div>
    </div>

    <!-- VP Search -->
    <section class="dash-section">
      <h2 class="dash-title">Vyhledat VP / položku</h2>
      <form class="search-form" @submit.prevent="doSearch">
        <Input
          v-model="searchQuery"
          :bare="true"
          testid="operator-search-input"
          type="search"
          class="search-input"
          placeholder="Číslo VP nebo položky..."
          inputmode="text"
          autocomplete="off"
        />
        <button type="submit" class="search-btn" :disabled="searching || !searchQuery.trim()">
          <svg v-if="!searching" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span v-else class="search-spinner" />
        </button>
      </form>
    </section>

    <!-- Search results picker overlay -->
    <div v-if="showPicker" class="picker-overlay" @click.self="closePicker">
      <div class="picker-panel">
        <div class="picker-header">
          <h3 class="picker-title">Nalezené operace</h3>
          <button class="picker-close" @click="closePicker">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="picker-list">
          <JobCard
            v-for="item in searchResults"
            :key="`${item.Job}-${item.OperNum}`"
            :job="item.Job"
            :oper-num="item.OperNum"
            :wc="item.Wc"
            :item="item.DerJobItem"
            :description="item.JobDescription"
            :qty-released="item.JobQtyReleased"
            :qty-complete="item.QtyComplete"
            :due-date="item.OpDatumSp"
            :order-due-date="item.OrderDueDate"
            :job-stat="item.JobStat"
            :tier="item.Tier"
            :is-hot="item.IsHot"
            @click="selectSearchResult(item)"
          />
        </div>
      </div>
    </div>

    <!-- Section: Active jobs -->
    <section v-if="operator.activeJobs.length > 0" class="dash-section">
      <h2 class="dash-title">Aktivní práce</h2>
      <div class="dash-cards">
        <JobCard
          v-for="aj in operator.activeJobs"
          :key="`${aj.job}-${aj.oper_num}`"
          :job="aj.job"
          :oper-num="aj.oper_num"
          :wc="aj.wc"
          :item="aj.der_job_item ?? aj.item"
          :description="aj.description"
          :job-stat="aj.job_stat"
          :qty-released="aj.qty_released"
          :qty-complete="aj.qty_complete"
          :due-date="aj.op_datum_sp"
          :running="true"
          @click="goToJobDetail(aj.job, aj.oper_num)"
        />
      </div>
    </section>

    <!-- Section: Transaction alerts -->
    <section v-if="operator.transactionAlerts.length > 0" class="dash-section">
      <h2 class="dash-title">Transakce k dořešení</h2>
      <div class="tx-list">
        <div
          v-for="tx in operator.transactionAlerts"
          :key="tx.id"
          :class="transSeverityClass(tx.severity)"
        >
          <div class="tx-main">
            <div class="tx-head">
              <strong>#{{ tx.id }} · {{ tx.job }} / Op {{ tx.oper_num }}</strong>
              <span class="tx-status">{{ transStatusLabel(tx.status) }}</span>
            </div>
            <div class="tx-meta">
              {{ transTypeLabel(tx.trans_type) }}
              <span v-if="tx.wc"> · {{ tx.wc }}</span>
            </div>
            <div v-if="tx.error_msg" class="tx-error">{{ tx.error_msg }}</div>
            <div v-if="tx.blocks_running" class="tx-running">
              Operace zůstává běžící, dokud nebude STOP potvrzen v Inforu.
            </div>
          </div>
          <button
            v-if="tx.retry_allowed"
            class="tx-retry"
            :disabled="retryingTxId === tx.id"
            :data-testid="`operator-retry-tx-${tx.id}`"
            @click="retryAlertTx(tx.id)"
          >
            {{ retryingTxId === tx.id ? 'Odesílám…' : 'Retry' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Section: Plnění norem -->
    <section v-if="operator.stats" class="dash-section">
      <h2 class="dash-title">Plnění norem</h2>
      <div class="stats-grid">
        <!-- Dnes hodiny (klikatelné) -->
        <button class="stat-card stat-card--clickable" @click="openDrillDown('day')">
          <div class="stat-val">{{ operator.stats.today_hours.toFixed(1) }}h</div>
          <div class="stat-label">Dnes hodiny</div>
        </button>
        <button class="stat-card stat-card--clickable" @click="openDrillDown('week')">
          <div class="stat-val">{{ operator.stats.week_hours.toFixed(1) }}h</div>
          <div class="stat-label">Týden hodiny</div>
        </button>

        <!-- Norm tiles: den / týden / měsíc -->
        <button
          :class="['stat-card stat-card--clickable stat-card--norm', normColorClass(operator.stats.today_norm_pct)]"
          @click="openDrillDown('day')"
        >
          <div class="stat-val">{{ formatPct(operator.stats.today_norm_pct) }}</div>
          <div class="stat-label">Dnes norma</div>
        </button>
        <button
          :class="['stat-card stat-card--clickable stat-card--norm', normColorClass(operator.stats.week_norm_pct)]"
          @click="openDrillDown('week')"
        >
          <div class="stat-val">{{ formatPct(operator.stats.week_norm_pct) }}</div>
          <div class="stat-label">Týden norma</div>
        </button>
        <button
          :class="['stat-card stat-card--clickable stat-card--norm', normColorClass(operator.stats.month_norm_pct)]"
          @click="openDrillDown('month')"
        >
          <div class="stat-val">{{ formatPct(operator.stats.month_norm_pct) }}</div>
          <div class="stat-label">Měsíc norma</div>
        </button>

        <!-- Custom range tile -->
        <button
          class="stat-card stat-card--clickable stat-card--history"
          @click="openCustomPicker"
        >
          <div class="stat-val">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div class="stat-label">Historie</div>
        </button>
      </div>
    </section>

    <!-- Custom date picker overlay -->
    <div v-if="showCustomPicker" class="drill-overlay" @click.self="showCustomPicker = false">
      <div class="custom-picker-panel">
        <div class="drill-header">
          <h3 class="drill-title">Vlastní období</h3>
          <button class="drill-close" @click="showCustomPicker = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="custom-picker-body">
          <div class="custom-picker-field">
            <label class="custom-picker-label">Od</label>
            <input
              v-model="customDateFrom"
              type="date"
              class="custom-picker-input"
            />
          </div>
          <div class="custom-picker-field">
            <label class="custom-picker-label">Do</label>
            <input
              v-model="customDateTo"
              type="date"
              class="custom-picker-input"
            />
          </div>
          <button
            class="custom-picker-submit"
            :disabled="!customDateFrom || !customDateTo"
            @click="submitCustomRange"
          >
            Zobrazit
          </button>
        </div>
      </div>
    </div>

    <!-- Drill-down overlay -->
    <div v-if="drillDown" class="drill-overlay" @click.self="closeDrillDown">
      <div class="drill-panel">
        <div class="drill-header">
          <h3 class="drill-title">{{ drillTitle }}</h3>
          <button class="drill-close" @click="closeDrillDown">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div v-if="drillSummaryPct != null" class="drill-summary">
          <span :class="['drill-summary-pct', normColorClass(drillSummaryPct)]">
            Celkově: {{ drillSummaryPct }}%
          </span>
          <span class="drill-summary-count">{{ drillDetails.length }} operací</span>
        </div>

        <div class="drill-content">
          <div v-if="drillLoading" class="drill-loading">Načítám...</div>
          <div v-else-if="drillDetails.length === 0" class="drill-loading">Žádná data</div>
          <div v-else class="drill-list">
            <div v-for="(d, i) in drillDetails" :key="i" class="drill-item">
              <div class="drill-item-head">
                <span class="drill-item-job">{{ d.job }} Op{{ d.oper_num }}</span>
                <span v-if="d.trans_type" :class="['drill-item-type', `drill-item-type--${d.trans_type}`]">{{ d.trans_type === 'S' ? 'Seříz.' : d.trans_type === 'R' ? 'Výr.' : d.trans_type }}</span>
                <span v-if="d.wc" class="drill-item-wc">{{ d.wc }}</span>
                <span v-if="d.trans_date" class="drill-item-date">{{ formatDate(d.trans_date) }}</span>
              </div>
              <div v-if="d.der_job_item" class="drill-item-article">{{ d.der_job_item }}</div>

              <!-- Run (výroba) -->
              <template v-if="d.actual_run_min > 0 || d.planned_run_min != null">
                <div class="drill-item-detail">
                  <span v-if="d.qty_complete > 0">{{ d.qty_complete }}ks</span>
                  <span v-if="d.planned_min_per_piece != null" class="drill-item-norm">
                    Norma: {{ d.planned_min_per_piece }} min/ks
                  </span>
                </div>
                <div class="drill-item-times">
                  <span class="drill-item-times-label">Výroba:</span>
                  <span v-if="d.planned_run_min != null">Plán {{ d.planned_run_min }} min</span>
                  <span v-if="d.planned_run_min != null && d.actual_run_min > 0"> → </span>
                  <span v-if="d.actual_run_min > 0">Skut {{ d.actual_run_min }} min</span>
                </div>
                <div v-if="d.run_fulfillment_pct != null" class="drill-item-bar-row">
                  <div class="drill-bar-track">
                    <div
                      :class="['drill-bar-fill', normColorClass(d.run_fulfillment_pct)]"
                      :style="{ width: barWidth(d.run_fulfillment_pct) }"
                    />
                  </div>
                  <span :class="['drill-bar-pct', normColorClass(d.run_fulfillment_pct)]">
                    {{ d.run_fulfillment_pct }}%
                  </span>
                </div>
              </template>

              <!-- Setup (seřízení) -->
              <template v-if="d.actual_setup_min > 0 || d.planned_setup_min != null">
                <div class="drill-item-times drill-item-setup">
                  <span class="drill-item-times-label">Seřízení:</span>
                  <span v-if="d.planned_setup_min != null">Plán {{ d.planned_setup_min }} min</span>
                  <span v-if="d.planned_setup_min != null && d.actual_setup_min > 0"> → </span>
                  <span v-if="d.actual_setup_min > 0">Skut {{ d.actual_setup_min }} min</span>
                </div>
                <div v-if="d.setup_fulfillment_pct != null" class="drill-item-bar-row">
                  <div class="drill-bar-track">
                    <div
                      :class="['drill-bar-fill', normColorClass(d.setup_fulfillment_pct)]"
                      :style="{ width: barWidth(d.setup_fulfillment_pct) }"
                    />
                  </div>
                  <span :class="['drill-bar-pct', normColorClass(d.setup_fulfillment_pct)]">
                    {{ d.setup_fulfillment_pct }}%
                  </span>
                </div>
              </template>

              <div v-if="d.qty_scrapped > 0" class="drill-item-scrap">
                Zmetky: {{ d.qty_scrapped }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Section: Workcenter selection (grouped) -->
    <section class="dash-section">
      <h2 class="dash-title">
        {{ operator.selectedWc ? 'Změnit pracoviště' : 'Vyberte pracoviště' }}
      </h2>
      <div v-if="wcGroups.length === 0 && !loadingStats" class="dash-empty">
        Žádná pracoviště
      </div>
      <template v-for="group in wcGroups" :key="group.label">
        <div class="wc-group-header">
          <div class="wc-group-label">{{ group.label }}</div>
          <button
            v-if="group.items.length > 1"
            class="wc-group-all"
            @click="selectGroup(group)"
          >
            Vše ({{ group.items.reduce((s: number, w: OperatorWorkcenter) => s + w.oper_count, 0) }})
          </button>
        </div>
        <div class="wc-grid">
          <button
            v-for="wc in group.items"
            :key="wc.wc"
            :class="['wc-card', { selected: operator.selectedWc === wc.wc }]"
            @click="selectWc(wc.wc)"
          >
            <div class="wc-name">{{ wc.wc }}</div>
            <div class="wc-count">{{ wc.oper_count }} op.</div>
          </button>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.dash {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dash-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dash-greeting {
  font-size: 18px;
  color: var(--t2);
}
.dash-wc {
  font-size: 13px;
  color: var(--t3);
}

.dash-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dash-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0;
}

.dash-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tx-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tx-alert {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  background: var(--surface, var(--base));
  padding: 10px;
}
.tx-alert--error {
  border-color: rgba(186, 26, 26, 0.4);
  background: rgba(186, 26, 26, 0.08);
}
.tx-alert--warning {
  border-color: rgba(245, 124, 0, 0.4);
  background: rgba(245, 124, 0, 0.08);
}
.tx-main { flex: 1; min-width: 0; }
.tx-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: var(--t1);
}
.tx-status { color: var(--t3); font-size: 12px; }
.tx-meta { margin-top: 3px; font-size: 12px; color: var(--t3); }
.tx-error { margin-top: 6px; font-size: 12px; color: var(--red); word-break: break-word; }
.tx-running { margin-top: 6px; font-size: 12px; color: var(--amber); }
.tx-retry {
  min-width: 74px; height: 34px;
  border: 1px solid var(--b2); border-radius: 8px;
  background: var(--base); color: var(--t1);
  font-size: 12px; font-weight: 600;
}
.tx-retry:disabled { opacity: 0.6; }

.dash-empty { color: var(--t4); font-size: 14px; padding: 12px 0; }

/* Search */
.search-form { display: flex; gap: 8px; }
.search-input {
  flex: 1; height: 48px; font-size: 16px;
  font-family: var(--font); color: var(--t1);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  padding: 0 14px; outline: none; -webkit-appearance: none;
}
.search-input:focus { border-color: var(--red, #e53935); background: rgba(255, 255, 255, 0.06); }
.search-input::placeholder { color: var(--t4); }
.search-btn {
  width: 48px; height: 48px; display: flex; align-items: center; justify-content: center;
  background: rgba(229, 57, 53, 0.1); border: 1px solid rgba(229, 57, 53, 0.3);
  border-radius: var(--rs, 8px); color: var(--red, #e53935);
  cursor: pointer; flex-shrink: 0; -webkit-tap-highlight-color: transparent;
}
.search-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.search-btn:active:not(:disabled) { background: rgba(229, 57, 53, 0.2); }
.search-spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(229, 57, 53, 0.3); border-top-color: var(--red, #e53935);
  border-radius: 50%; animation: spin 600ms linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Picker overlay */
.picker-overlay {
  position: fixed; inset: 0; z-index: 90;
  background: rgba(0, 0, 0, 0.7);
  display: flex; align-items: stretch; justify-content: center; padding: 16px;
}
.picker-panel {
  width: 100%; max-width: 600px;
  background: var(--ground, #181a1f); border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  display: flex; flex-direction: column; overflow: hidden;
}
.picker-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.picker-title { font-size: 15px; font-weight: 600; color: var(--t1); margin: 0; }
.picker-close {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--t3); cursor: pointer; border-radius: 4px;
}
.picker-close:active { background: rgba(255, 255, 255, 0.06); }
.picker-list {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 8px;
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
@media (max-width: 500px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  padding: 12px; text-align: center; font-family: var(--font);
}
.stat-card--clickable {
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: background 100ms, border-color 100ms;
}
.stat-card--clickable:active { background: rgba(255, 255, 255, 0.06); border-color: var(--t4); }
.stat-val {
  font-size: 22px; font-weight: 600; color: var(--t1);
  font-variant-numeric: tabular-nums;
  display: flex; align-items: center; justify-content: center;
}
.stat-label {
  font-size: 11px; color: var(--t4); margin-top: 2px;
  text-transform: uppercase; letter-spacing: 0.04em;
}

/* Norm color variants */
.stat-card--norm.norm-green {
  border-color: rgba(76, 175, 80, 0.3); background: rgba(76, 175, 80, 0.06);
}
.stat-card--norm.norm-green .stat-val { color: var(--green, #4caf50); }
.stat-card--norm.norm-amber {
  border-color: rgba(255, 152, 0, 0.3); background: rgba(255, 152, 0, 0.06);
}
.stat-card--norm.norm-amber .stat-val { color: var(--amber, #ff9800); }
.stat-card--norm.norm-red {
  border-color: rgba(229, 57, 53, 0.3); background: rgba(229, 57, 53, 0.06);
}
.stat-card--norm.norm-red .stat-val { color: var(--red, #e53935); }

/* History tile */
.stat-card--history {
  border-color: rgba(33, 150, 243, 0.3); background: rgba(33, 150, 243, 0.06);
}
.stat-card--history .stat-val { color: var(--blue, #2196f3); }

/* Custom date picker */
.custom-picker-panel {
  width: 100%; max-width: 360px;
  background: var(--ground, #181a1f); border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  display: flex; flex-direction: column; overflow: hidden;
  align-self: center;
}
.custom-picker-body {
  padding: 16px; display: flex; flex-direction: column; gap: 14px;
}
.custom-picker-field {
  display: flex; flex-direction: column; gap: 4px;
}
.custom-picker-label {
  font-size: 12px; color: var(--t3); text-transform: uppercase; letter-spacing: 0.04em;
}
.custom-picker-input {
  height: 48px; font-size: 16px; font-family: var(--font); color: var(--t1);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  padding: 0 14px; outline: none;
  color-scheme: dark;
}
.custom-picker-input:focus { border-color: var(--blue, #2196f3); background: rgba(255, 255, 255, 0.06); }
.custom-picker-submit {
  height: 48px; border: none; border-radius: var(--rs, 8px);
  background: rgba(33, 150, 243, 0.15); color: var(--blue, #2196f3);
  font-size: 16px; font-weight: 700; font-family: var(--font);
  cursor: pointer; -webkit-tap-highlight-color: transparent;
}
.custom-picker-submit:disabled { opacity: 0.4; cursor: not-allowed; }
.custom-picker-submit:active:not(:disabled) { background: rgba(33, 150, 243, 0.25); }

/* Drill-down overlay */
.drill-overlay {
  position: fixed; inset: 0; z-index: 90;
  background: rgba(0, 0, 0, 0.7);
  display: flex; align-items: stretch; justify-content: center; padding: 16px;
}
.drill-panel {
  width: 100%; max-width: 600px;
  background: var(--ground, #181a1f); border: 1px solid var(--b2); border-radius: var(--rs, 8px);
  display: flex; flex-direction: column; overflow: hidden;
}
.drill-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.drill-title { font-size: 15px; font-weight: 600; color: var(--t1); margin: 0; }
.drill-close {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--t3); cursor: pointer; border-radius: 4px;
}
.drill-close:active { background: rgba(255, 255, 255, 0.06); }

.drill-summary {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid var(--b1); font-size: 14px;
}
.drill-summary-pct { font-weight: 700; }
.drill-summary-pct.norm-green { color: var(--green, #4caf50); }
.drill-summary-pct.norm-amber { color: var(--amber, #ff9800); }
.drill-summary-pct.norm-red { color: var(--red, #e53935); }
.drill-summary-count { color: var(--t3); font-size: 13px; }

.drill-content { flex: 1; overflow-y: auto; padding: 12px 16px; }
.drill-loading { color: var(--t4); font-size: 14px; text-align: center; padding: 30px 0; }

.drill-list { display: flex; flex-direction: column; gap: 10px; }

.drill-item {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--b2); border-radius: var(--rs, 8px);
}
.drill-item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.drill-item-job { font-size: 14px; font-weight: 600; color: var(--t1); }
.drill-item-wc {
  font-size: 11px; color: var(--t3);
  border: 1px solid var(--b2); border-radius: 4px; padding: 0 5px;
}
.drill-item-date {
  margin-left: auto; font-size: 11px; color: var(--t4); font-variant-numeric: tabular-nums;
}
.drill-item-article { font-size: 12px; color: var(--t3); margin-bottom: 4px; }
.drill-item-type {
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  border-radius: 4px; padding: 1px 5px;
}
/* TransType badge colors: R=výroba (green), S=seřízení (amber), C=close (grey) */
.drill-item-type--R { background: rgba(76, 175, 80, 0.12); color: var(--ok, #4caf50); }
.drill-item-type--S { background: rgba(255, 193, 7, 0.15); color: var(--warn, #ffc107); }
.drill-item-type--C { background: rgba(255, 255, 255, 0.06); color: var(--t3); }
.drill-item-detail { font-size: 12px; color: var(--t2); display: flex; gap: 10px; }
.drill-item-norm { color: var(--t3); }
.drill-item-times {
  font-size: 12px; color: var(--t3); margin-top: 3px; font-variant-numeric: tabular-nums;
  display: flex; gap: 6px; align-items: baseline;
}
.drill-item-times-label { font-weight: 600; font-size: 11px; min-width: 52px; }
.drill-item-setup { color: var(--warn, #ffc107); }
.drill-item-setup .drill-item-times-label { color: var(--warn, #ffc107); }
.drill-item-bar-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.drill-bar-track { flex: 1; height: 6px; background: var(--b1); border-radius: 3px; overflow: hidden; }
.drill-bar-fill {
  height: 100%; border-radius: 3px; transition: width 300ms ease; max-width: 100%;
}
.drill-bar-fill.norm-green { background: var(--green, #4caf50); }
.drill-bar-fill.norm-amber { background: var(--amber, #ff9800); }
.drill-bar-fill.norm-red { background: var(--red, #e53935); }

/* Setup bar uses amber/orange tones */
.drill-item-setup + .drill-item-bar-row .drill-bar-fill.norm-green { background: var(--warn, #ffc107); }
.drill-item-setup + .drill-item-bar-row .drill-bar-fill.norm-amber { background: var(--amber, #ff9800); }
.drill-item-setup + .drill-item-bar-row .drill-bar-fill.norm-red { background: var(--red, #e53935); }
.drill-item-setup + .drill-item-bar-row .drill-bar-pct.norm-green { color: var(--warn, #ffc107); }
.drill-item-setup + .drill-item-bar-row .drill-bar-pct.norm-amber { color: var(--amber, #ff9800); }

.drill-bar-pct {
  font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums;
  min-width: 42px; text-align: right;
}
.drill-bar-pct.norm-green { color: var(--green, #4caf50); }
.drill-bar-pct.norm-amber { color: var(--amber, #ff9800); }
.drill-bar-pct.norm-red { color: var(--red, #e53935); }
.drill-item-scrap { margin-top: 3px; font-size: 11px; color: var(--warn); }

/* Workcenter groups */
.wc-group-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 8px; margin-bottom: 2px;
}
.wc-group-label { font-size: 13px; font-weight: 600; color: var(--t2); }
.wc-group-all {
  font-size: 12px; font-weight: 600; color: var(--red, #e53935);
  background: rgba(229, 57, 53, 0.08); border: 1px solid rgba(229, 57, 53, 0.25);
  border-radius: 6px; padding: 3px 10px; cursor: pointer;
  font-family: var(--font); -webkit-tap-highlight-color: transparent;
}
.wc-group-all:active { background: rgba(229, 57, 53, 0.16); }

.wc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.wc-card {
  min-height: 72px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px;
  background: rgba(255, 255, 255, 0.03); border: 1px solid var(--b2);
  border-radius: var(--rs, 8px); padding: 12px 8px; cursor: pointer;
  font-family: var(--font); -webkit-tap-highlight-color: transparent;
  transition: background 100ms, border-color 100ms;
}
.wc-card:active { background: rgba(255, 255, 255, 0.06); }
.wc-card.selected { border-color: var(--red, #e53935); background: rgba(229, 57, 53, 0.06); }
.wc-name { font-size: 16px; font-weight: 600; color: var(--t1); }
.wc-count { font-size: 12px; color: var(--t4); }
</style>
