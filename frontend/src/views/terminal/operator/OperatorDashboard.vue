<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as workshopApi from '@/api/workshop'
import type { MachinePlanItem } from '@/types/workshop'
import type { OperatorWorkcenter } from '@/types/operator'
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
    // Single DB query — searches Job + Item + Description server-side
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
      // Single operation — go straight to detail
      router.push({ name: 'terminal-job-detail', params: { job: matches[0]!.Job, oper: matches[0]!.OperNum } })
    } else {
      // Multiple results — show picker
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

    <!-- Section: Stats -->
    <section v-if="operator.stats" class="dash-section">
      <h2 class="dash-title">Statistiky</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-val">{{ operator.stats.today_hours.toFixed(1) }}h</div>
          <div class="stat-label">Dnes hodiny</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">{{ operator.stats.today_pieces }}</div>
          <div class="stat-label">Dnes kusy</div>
        </div>
        <div class="stat-card">
          <div class="stat-val warn">{{ operator.stats.today_scrap }}</div>
          <div class="stat-label">Dnes zmetky</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">{{ operator.stats.week_hours.toFixed(1) }}h</div>
          <div class="stat-label">Týden hodiny</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">{{ operator.stats.week_pieces }}</div>
          <div class="stat-label">Týden kusy</div>
        </div>
      </div>
    </section>

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

.tx-main {
  flex: 1;
  min-width: 0;
}

.tx-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: var(--t1);
}

.tx-status {
  color: var(--t3);
  font-size: 12px;
}

.tx-meta {
  margin-top: 3px;
  font-size: 12px;
  color: var(--t3);
}

.tx-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--red);
  word-break: break-word;
}

.tx-running {
  margin-top: 6px;
  font-size: 12px;
  color: var(--amber);
}

.tx-retry {
  min-width: 74px;
  height: 34px;
  border: 1px solid var(--b2);
  border-radius: 8px;
  background: var(--base);
  color: var(--t1);
  font-size: 12px;
  font-weight: 600;
}

.tx-retry:disabled {
  opacity: 0.6;
}

.dash-empty {
  color: var(--t4);
  font-size: 14px;
  padding: 12px 0;
}

/* Search */
.search-form {
  display: flex;
  gap: 8px;
}
.search-input {
  flex: 1;
  height: 48px;
  font-size: 16px;
  font-family: var(--font);
  color: var(--t1);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  padding: 0 14px;
  outline: none;
  -webkit-appearance: none;
}
.search-input:focus {
  border-color: var(--red, #e53935);
  background: rgba(255, 255, 255, 0.06);
}
.search-input::placeholder {
  color: var(--t4);
}
.search-btn {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(229, 57, 53, 0.1);
  border: 1px solid rgba(229, 57, 53, 0.3);
  border-radius: var(--rs, 8px);
  color: var(--red, #e53935);
  cursor: pointer;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.search-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.search-btn:active:not(:disabled) {
  background: rgba(229, 57, 53, 0.2);
}
.search-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(229, 57, 53, 0.3);
  border-top-color: var(--red, #e53935);
  border-radius: 50%;
  animation: spin 600ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Picker overlay */
.picker-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 16px;
}
.picker-panel {
  width: 100%;
  max-width: 600px;
  background: var(--ground, #181a1f);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.picker-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}
.picker-close {
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
.picker-close:active {
  background: rgba(255, 255, 255, 0.06);
}
.picker-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
@media (max-width: 500px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  padding: 12px;
  text-align: center;
}
.stat-val {
  font-size: 22px;
  font-weight: 600;
  color: var(--t1);
  font-variant-numeric: tabular-nums;
}
.stat-val.warn {
  color: var(--warn);
}
.stat-label {
  font-size: 11px;
  color: var(--t4);
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Workcenter groups */
.wc-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  margin-bottom: 2px;
}
.wc-group-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--t2);
}
.wc-group-all {
  font-size: 12px;
  font-weight: 600;
  color: var(--red, #e53935);
  background: rgba(229, 57, 53, 0.08);
  border: 1px solid rgba(229, 57, 53, 0.25);
  border-radius: 6px;
  padding: 3px 10px;
  cursor: pointer;
  font-family: var(--font);
  -webkit-tap-highlight-color: transparent;
}
.wc-group-all:active {
  background: rgba(229, 57, 53, 0.16);
}

/* Workcenter grid */
.wc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.wc-card {
  min-height: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  padding: 12px 8px;
  cursor: pointer;
  font-family: var(--font);
  -webkit-tap-highlight-color: transparent;
  transition: background 100ms, border-color 100ms;
}
.wc-card:active {
  background: rgba(255, 255, 255, 0.06);
}
.wc-card.selected {
  border-color: var(--red, #e53935);
  background: rgba(229, 57, 53, 0.06);
}

.wc-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}
.wc-count {
  font-size: 12px;
  color: var(--t4);
}
</style>
