<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'
import { getMachinePlanDnd } from '@/api/machinePlanDnd'
import type { MachinePlanItem } from '@/types/workshop'
import type { PriorityTier } from '@/types/production-planner'
import { onSseEvent } from '@/composables/useSse'
import JobCard from '../shared/JobCard.vue'
import QueueDrawingBrowser from './QueueDrawingBrowser.vue'

const viewMode = ref<'cards' | 'drawings'>('cards')

const router = useRouter()
const operator = useOperatorStore()

const loading = ref(false)
const refreshing = ref(false)
const plannedItems = ref<MachinePlanItem[]>([])

// --- SAW filter state ---
const sawFilterMill = ref(false)
const sawFilterLathe = ref(false)
const sawGroupMaterial = ref(false)

// Header info — single WC or group label
const headerLabel = computed(() => {
  if (operator.selectedWcGroup) return operator.selectedWcGroup.label
  return operator.selectedWc ?? ''
})

const isGroup = computed(() => Boolean(operator.selectedWcGroup))

// Which WCs to fetch
const targetWcs = computed<string[]>(() => {
  if (operator.selectedWcGroup) return operator.selectedWcGroup.wcs
  if (operator.selectedWc) return [operator.selectedWc]
  return []
})

// Is this a SAW workcenter? (all targetWcs start with PS*)
const isSawView = computed(() => {
  if (targetWcs.value.length === 0) return false
  return targetWcs.value.every(wc => wc.toUpperCase().startsWith('PS'))
})

// --- WC type classification (same logic as Dashboard classifyWc) ---
function classifyNextWc(wc: string | null | undefined): 'mill' | 'lathe' | 'other' {
  if (!wc) return 'other'
  const u = wc.toUpperCase()
  if (u.startsWith('F')) return 'mill'
  if (u.startsWith('SH') || u.startsWith('SM')) return 'lathe'
  return 'other'
}

// --- Toggle handlers (mutual exclusivity for mill/lathe) ---
function toggleMill() {
  sawFilterMill.value = !sawFilterMill.value
  if (sawFilterMill.value) sawFilterLathe.value = false
}
function toggleLathe() {
  sawFilterLathe.value = !sawFilterLathe.value
  if (sawFilterLathe.value) sawFilterMill.value = false
}
function toggleMaterial() {
  sawGroupMaterial.value = !sawGroupMaterial.value
}

// --- Effective due date (same logic as JobCard: OrderDueDate → OpDatumSp fallback) ---
function effectiveDue(item: MachinePlanItem): string {
  const d = item.OrderDueDate ?? item.OpDatumSp
  if (!d) return '99991231'
  return d.replace(/-/g, '')  // normalize "2026-03-15" → "20260315"
}

// --- Shared sort: hot → effective due date ASC ---
function hotDateSort(a: MachinePlanItem, b: MachinePlanItem): number {
  const hotA = a.IsHot ? 0 : 1
  const hotB = b.IsHot ? 0 : 1
  if (hotA !== hotB) return hotA - hotB
  const da = effectiveDue(a)
  const db = effectiveDue(b)
  return da < db ? -1 : da > db ? 1 : 0
}

// --- Display items: filtered + sorted (flat list — source of truth for cards i PDF) ---
const displayItems = computed<MachinePlanItem[]>(() => {
  let items = [...plannedItems.value]

  // SAW filter: mill or lathe
  if (isSawView.value && sawFilterMill.value) {
    items = items.filter(i => classifyNextWc(i.NextWc) === 'mill')
  } else if (isSawView.value && sawFilterLathe.value) {
    items = items.filter(i => classifyNextWc(i.NextWc) === 'lathe')
  }

  // Material grouping → flat list ordered group-by-group
  if (isSawView.value && sawGroupMaterial.value) {
    return _buildGroupedFlatList(items)
  }

  // Default sort: hot → OrderDueDate
  items.sort(hotDateSort)
  return items
})

// --- Material groups for card rendering (derived from displayItems) ---
interface MaterialGroupData {
  material: string
  label: string
  hasHot: boolean
  items: MachinePlanItem[]
}

function _materialGroupLabel(key: string): string {
  if (key === '__none__') return 'Bez materi\u00e1lu'
  if (key === '__unknown__') return 'Nezn\u00e1m\u00fd materi\u00e1l'
  return key
}

function _materialGroupOrder(key: string): number {
  if (key === '__none__') return 2
  if (key === '__unknown__') return 1
  return 0
}

function _buildGroupedFlatList(items: MachinePlanItem[]): MachinePlanItem[] {
  const groupMap = new Map<string, MachinePlanItem[]>()
  for (const item of items) {
    const key = item.MaterialGroupName ?? '__none__'
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key)!.push(item)
  }

  const groups: { key: string; hasHot: boolean; earliestDue: string; items: MachinePlanItem[] }[] = []
  for (const [key, groupItems] of groupMap) {
    groupItems.sort(hotDateSort)
    const hasHot = groupItems.some(i => i.IsHot)
    const earliestDue = groupItems
      .map(i => effectiveDue(i))
      .sort()[0] ?? '99991231'
    groups.push({ key, hasHot, earliestDue, items: groupItems })
  }

  groups.sort((a, b) => {
    const oa = _materialGroupOrder(a.key)
    const ob = _materialGroupOrder(b.key)
    if (oa !== ob) return oa - ob
    if (a.hasHot !== b.hasHot) return a.hasHot ? -1 : 1
    return a.earliestDue < b.earliestDue ? -1 : a.earliestDue > b.earliestDue ? 1 : 0
  })

  return groups.flatMap(g => g.items)
}

// Material groups for card headers (only when grouping active)
const materialGroups = computed<MaterialGroupData[] | null>(() => {
  if (!isSawView.value || !sawGroupMaterial.value) return null

  // Rebuild group structure from the already-sorted displayItems
  const result: MaterialGroupData[] = []
  let currentKey: string | null = null
  let currentGroup: MaterialGroupData | null = null

  for (const item of displayItems.value) {
    const key = item.MaterialGroupName ?? '__none__'
    if (key !== currentKey) {
      currentKey = key
      currentGroup = {
        material: key,
        label: _materialGroupLabel(key),
        hasHot: false,
        items: [],
      }
      result.push(currentGroup)
    }
    currentGroup!.items.push(item)
    if (item.IsHot) currentGroup!.hasHot = true
  }

  return result
})

// Total displayed count
const displayCount = computed(() => displayItems.value.length)

onMounted(async () => {
  if (targetWcs.value.length === 0) {
    router.replace({ name: 'terminal-dashboard' })
    return
  }
  await loadQueue()
})

async function fetchForWcs(wcs: string[]): Promise<MachinePlanItem[]> {
  const results = await Promise.all(wcs.map(wc => getMachinePlanDnd(wc)))
  if (!isGroup.value) {
    // Single WC: backend vrací planned v správném pořadí (hot → DnD positioned → auto)
    return results.flatMap(r => r.planned)
  }
  // Group view: merge planned ze všech WC — sort se řeší v displayItems
  return results.flatMap(r => r.planned)
}

async function loadQueue() {
  loading.value = true
  try {
    plannedItems.value = await fetchForWcs(targetWcs.value)
    applyStoreTierOverrides()
  } finally {
    loading.value = false
  }
}

async function doRefresh() {
  refreshing.value = true
  try {
    plannedItems.value = await fetchForWcs(targetWcs.value)
    applyStoreTierOverrides()
  } finally {
    refreshing.value = false
  }
}

function goToJob(job: string, oper: string) {
  operator.touchActivity()
  router.push({ name: 'terminal-job-detail', params: { job, oper } })
}

/** Apply a single tier override to all items matching the job key */
function applyTierToItems(jobUpper: string, tier: PriorityTier) {
  let changed = false
  for (const item of plannedItems.value) {
    if (item.Job.toUpperCase() === jobUpper) {
      item.Tier = tier
      item.IsHot = tier === 'hot'
      item.Priority = tier === 'hot' ? 5 : tier === 'urgent' ? 20 : 100
      changed = true
    }
  }
  return changed
}

/** Apply all pending tier overrides from the store (e.g. received while on another page) */
function applyStoreTierOverrides() {
  const overrides = operator.tierOverrides
  let changed = false
  for (const [jobUpper, tier] of Object.entries(overrides)) {
    if (applyTierToItems(jobUpper, tier)) changed = true
  }
  if (changed) {
    plannedItems.value = [...plannedItems.value]
  }
}

// SSE — tier change → aktualizovat položky in-place + re-sort hot nahoru
onSseEvent('tier_change', (data) => {
  const msg = data as { job: string; suffix?: string; tier: PriorityTier }
  if (applyTierToItems(msg.job.toUpperCase(), msg.tier)) {
    plannedItems.value = [...plannedItems.value]
  }
})
</script>

<template>
  <div :class="['queue', { 'queue--drawings': viewMode === 'drawings' && !loading && plannedItems.length > 0 }]">
    <!-- Header -->
    <div class="queue-header">
      <div class="queue-info">
        <h2 class="queue-title">Fronta práce</h2>
        <span class="queue-wc">{{ headerLabel }}</span>
        <span v-if="isGroup" class="queue-group-tag">{{ targetWcs.length }} WC</span>
        <span class="queue-count">{{ displayCount }} operací</span>
      </div>
      <div class="queue-actions">
        <!-- SAW filter toggles -->
        <template v-if="isSawView">
          <button :class="['saw-btn', { active: sawFilterMill }]" @click="toggleMill">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
            Frézy
          </button>
          <button :class="['saw-btn', { active: sawFilterLathe }]" @click="toggleLathe">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
            </svg>
            Soustruhy
          </button>
          <button :class="['saw-btn', { active: sawGroupMaterial }]" @click="toggleMaterial">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            </svg>
            Materiál
          </button>
        </template>

        <!-- View mode toggle -->
        <div class="view-toggle">
          <button
            :class="['toggle-btn', { active: viewMode === 'cards' }]"
            title="Karty"
            @click="viewMode = 'cards'"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </button>
          <button
            :class="['toggle-btn', { active: viewMode === 'drawings' }]"
            title="Výkresy"
            @click="viewMode = 'drawings'"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </button>
        </div>

        <button
          :class="['refresh-btn', { spin: refreshing }]"
          :disabled="refreshing"
          @click="doRefresh"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="queue-loading">Načítám frontu...</div>

    <!-- Empty -->
    <div v-else-if="displayItems.length === 0" class="queue-empty">
      <template v-if="plannedItems.length > 0 && (sawFilterMill || sawFilterLathe)">
        Žádné operace pro vybraný filtr
      </template>
      <template v-else>
        Fronta je prázdná
      </template>
    </div>

    <!-- Drawings mode -->
    <QueueDrawingBrowser
      v-else-if="viewMode === 'drawings'"
      :items="displayItems"
      class="queue-drawings"
      @go-to-job="goToJob"
    />

    <!-- Cards mode — grouped by material -->
    <div v-else-if="materialGroups" class="queue-list">
      <div v-for="group in materialGroups" :key="group.material" class="mat-group">
        <div class="mat-group-header">
          <span class="mat-group-label">{{ group.label }}</span>
          <span class="mat-group-count">{{ group.items.length }}</span>
          <span v-if="group.hasHot" class="mat-group-hot">HOT</span>
        </div>
        <JobCard
          v-for="item in group.items"
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
          :next-wc="item.NextWc"
          :primary-material="item.PrimaryMaterial"
          :iso-group="item.IsoGroup"
          :show-saw-extras="true"
          @click="goToJob(item.Job, item.OperNum)"
        />
      </div>
    </div>

    <!-- Cards mode — flat (default) -->
    <div v-else class="queue-list">
      <JobCard
        v-for="item in displayItems"
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
        :next-wc="item.NextWc"
        :primary-material="item.PrimaryMaterial"
        :iso-group="item.IsoGroup"
        :show-saw-extras="isSawView"
        @click="goToJob(item.Job, item.OperNum)"
      />
    </div>
  </div>
</template>

<style scoped>
.queue {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.queue--drawings {
  height: 100%;
  overflow: hidden;
}

.queue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.queue-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.queue-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}

.queue-wc {
  font-size: 13px;
  font-weight: 500;
  color: var(--red, #e53935);
  border: 1px solid rgba(229, 57, 53, 0.3);
  border-radius: 4px;
  padding: 1px 6px;
}

.queue-group-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--t3);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 1px 5px;
}

.queue-count {
  font-size: 12px;
  color: var(--t4);
}

.refresh-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  color: var(--t3);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.refresh-btn:active {
  background: rgba(255, 255, 255, 0.04);
}
.refresh-btn.spin svg {
  animation: spin 800ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.queue-loading, .queue-empty {
  color: var(--t4);
  font-size: 14px;
  text-align: center;
  padding: 40px 0;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Actions row */
.queue-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* View mode toggle */
.view-toggle {
  display: flex;
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  overflow: hidden;
}
.toggle-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--t4);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 100ms, color 100ms;
}
.toggle-btn + .toggle-btn {
  border-left: 1px solid var(--b2);
}
.toggle-btn.active {
  color: var(--t1);
  background: rgba(255, 255, 255, 0.06);
}
.toggle-btn:active {
  background: rgba(255, 255, 255, 0.04);
}

/* Drawings mode — fill available space, remove padding */
.queue-drawings {
  flex: 1;
  min-height: 0;
  margin: -12px -16px -16px;
}

/* SAW filter toggles (inline in header) */
.saw-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--t3);
  background: none;
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 100ms, color 100ms, border-color 100ms;
}
.saw-btn:active {
  background: rgba(255, 255, 255, 0.04);
}
.saw-btn.active {
  color: var(--t1);
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--t3);
}

/* Material groups */
.mat-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mat-group + .mat-group {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--b2);
}
.mat-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.mat-group-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--t2);
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.mat-group-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--t4);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 1px 5px;
  flex-shrink: 0;
}
.mat-group-hot {
  font-size: 10px;
  font-weight: 700;
  color: var(--red, #ef5350);
  background: color-mix(in srgb, var(--red, #ef5350) 15%, transparent);
  border-radius: 3px;
  padding: 1px 5px;
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
