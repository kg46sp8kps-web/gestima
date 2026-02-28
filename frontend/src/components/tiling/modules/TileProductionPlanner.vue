<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useProductionPlannerStore } from '@/stores/productionPlanner'
import Spinner from '@/components/ui/Spinner.vue'
import type { PlannerVpRow, PlannerOperation, PriorityTier, WcLane, WcLaneOp } from '@/types/production-planner'

const store = useProductionPlannerStore()
const searchQuery = ref('')
const editingPriority = ref<string | null>(null)
const priorityInput = ref(100)
const scrollRef = ref<HTMLElement | null>(null)
const viewMode = ref<'queue' | 'vp' | 'wc'>('queue')

// Zoom: px per day — from overview (2) to hourly detail (720 = 30px/h)
const ZOOM_STEPS = [2, 4, 8, 16, 32, 64, 120, 240, 480, 720] as const
const zoomIdx = ref(3) // start at 16 px/d
const zoomLevel = computed(() => ZOOM_STEPS[zoomIdx.value]!)

const ZOOM_LABELS: Record<number, string> = {
  2: '2 px/d',
  4: '4 px/d',
  8: '8 px/d',
  16: '16 px/d',
  32: '32 px/d',
  64: '64 px/d',
  120: '5 px/h',
  240: '10 px/h',
  480: '20 px/h',
  720: '30 px/h',
}

onMounted(() => {
  if (!store.vps.length) store.fetchData()
})

// Filtered VPs
const filteredVps = computed(() => {
  const q = searchQuery.value.trim().toUpperCase()
  if (!q) return store.vps
  return store.vps.filter(
    (vp) =>
      vp.job.toUpperCase().includes(q) ||
      (vp.item?.toUpperCase().includes(q)) ||
      (vp.description?.toUpperCase().includes(q)) ||
      (vp.co_num?.toUpperCase().includes(q)),
  )
})

// Filtered WC lanes
const filteredWcLanes = computed(() => {
  const q = searchQuery.value.trim().toUpperCase()
  if (!q) return store.wcLanes
  return store.wcLanes
    .map((lane) => ({
      ...lane,
      ops: lane.ops.filter(
        (op) =>
          op.job.toUpperCase().includes(q) ||
          (op.item?.toUpperCase().includes(q)) ||
          (op.description?.toUpperCase().includes(q)) ||
          lane.wc.toUpperCase().includes(q),
      ),
    }))
    .filter((lane) => lane.ops.length > 0)
})

// Timeline helpers
const minDate = computed(() => store.timeRange.min_date ? new Date(store.timeRange.min_date) : new Date())
const maxDate = computed(() => store.timeRange.max_date ? new Date(store.timeRange.max_date) : new Date())
const totalDays = computed(() => Math.max(1, Math.ceil((maxDate.value.getTime() - minDate.value.getTime()) / 86400000)))
const timelineWidth = computed(() => totalDays.value * zoomLevel.value)

// Today marker
const todayOffset = computed(() => {
  const diff = (new Date().getTime() - minDate.value.getTime()) / 86400000
  return Math.round(diff * zoomLevel.value)
})

// Date header ticks — adaptive: months → weeks → days → 6h → 1h
const dateTicks = computed(() => {
  const ticks: { label: string; left: number; major: boolean }[] = []
  const z = zoomLevel.value

  if (z >= 240) {
    const msPerHour = 3600000
    const totalHours = totalDays.value * 24
    const step = z >= 480 ? 1 : z >= 240 ? 2 : 4
    for (let h = 0; h <= totalHours; h += step) {
      const d = new Date(minDate.value.getTime() + h * msPerHour)
      const isMidnight = d.getHours() === 0
      ticks.push({
        label: isMidnight
          ? `${d.getDate()}.${d.getMonth() + 1}.`
          : `${d.getHours()}:00`,
        left: Math.round((h / 24) * z),
        major: isMidnight,
      })
    }
  } else if (z >= 64) {
    const msPerHour = 3600000
    const totalHours = totalDays.value * 24
    const step = z >= 120 ? 6 : 12
    for (let h = 0; h <= totalHours; h += step) {
      const d = new Date(minDate.value.getTime() + h * msPerHour)
      const isMidnight = d.getHours() === 0
      ticks.push({
        label: isMidnight
          ? `${d.getDate()}.${d.getMonth() + 1}.`
          : `${d.getHours()}:00`,
        left: Math.round((h / 24) * z),
        major: isMidnight,
      })
    }
  } else if (z >= 16) {
    for (let i = 0; i <= totalDays.value; i++) {
      const d = new Date(minDate.value.getTime() + i * 86400000)
      const isMonday = d.getDay() === 1
      ticks.push({
        label: `${d.getDate()}.${d.getMonth() + 1}.`,
        left: i * z,
        major: isMonday,
      })
    }
  } else if (z >= 4) {
    const step = z <= 4 ? 7 : 3
    for (let i = 0; i <= totalDays.value; i += step) {
      const d = new Date(minDate.value.getTime() + i * 86400000)
      ticks.push({
        label: `${d.getDate()}.${d.getMonth() + 1}.`,
        left: i * z,
        major: d.getDate() === 1,
      })
    }
  } else {
    const step = 14
    for (let i = 0; i <= totalDays.value; i += step) {
      const d = new Date(minDate.value.getTime() + i * 86400000)
      ticks.push({
        label: `${d.getDate()}.${d.getMonth() + 1}.`,
        left: i * z,
        major: d.getDate() <= step,
      })
    }
  }

  return ticks
})

function dateToX(dateStr: string | null): number {
  if (!dateStr) return 0
  const d = new Date(dateStr)
  const diff = (d.getTime() - minDate.value.getTime()) / 86400000
  return Math.round(diff * zoomLevel.value)
}

function opBarLeft(op: PlannerOperation): number {
  return dateToX(op.sched_start ?? op.start_date)
}

function opBarWidth(op: PlannerOperation): number {
  const start = op.sched_start ?? op.start_date
  const end = op.sched_end ?? op.end_date
  if (!start || !end) return Math.max(zoomLevel.value, 16)
  const w = dateToX(end) - dateToX(start)
  return Math.max(w, 4)
}

function wcOpBarLeft(op: WcLaneOp): number {
  return dateToX(op.sched_start)
}

function wcOpBarWidth(op: WcLaneOp): number {
  if (!op.sched_start || !op.sched_end) return Math.max(zoomLevel.value, 16)
  const w = dateToX(op.sched_end) - dateToX(op.sched_start)
  return Math.max(w, 4)
}

function opBarClass(status: string, wc: string | null): string {
  if (wc?.startsWith('KOO')) return 'bar-coop'
  return `bar-${status}`
}

function vpKey(vp: PlannerVpRow): string {
  return `${vp.job}|${vp.suffix}`
}

function formatDuration(op: PlannerOperation | WcLaneOp): string {
  const d = op.duration_hrs
  if (!d) return ''
  if (d < 1) return `${Math.round(d * 60)}m`
  return `${d.toFixed(1)}h`
}

function formatNorm(op: PlannerOperation | WcLaneOp): string {
  const parts: string[] = []
  if (op.setup_hrs) parts.push(`S:${Math.round(op.setup_hrs * 60)}m`)
  if (op.pcs_per_hour && op.pcs_per_hour > 0) {
    const minPer = 60 / op.pcs_per_hour
    parts.push(`${minPer.toFixed(1)}m/ks`)
  }
  return parts.join(' ')
}

function zoomIn() {
  if (zoomIdx.value < ZOOM_STEPS.length - 1) {
    zoomAroundCenter(zoomIdx.value + 1)
  }
}

function zoomOut() {
  if (zoomIdx.value > 0) {
    zoomAroundCenter(zoomIdx.value - 1)
  }
}

function zoomAroundCenter(newIdx: number) {
  const el = scrollRef.value
  if (!el) { zoomIdx.value = newIdx; return }
  const centerX = el.scrollLeft + el.clientWidth / 2 - 260
  const centerDay = centerX / zoomLevel.value
  zoomIdx.value = newIdx
  nextTick(() => {
    const newCenterX = centerDay * zoomLevel.value
    el.scrollLeft = newCenterX - el.clientWidth / 2 + 260
  })
}

function onWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    if (e.deltaY < 0) zoomIn()
    else zoomOut()
  }
}

function scrollToToday() {
  const el = scrollRef.value
  if (!el) return
  el.scrollLeft = todayOffset.value - el.clientWidth / 3
}

function startEditPriority(vp: PlannerVpRow) {
  editingPriority.value = vpKey(vp)
  priorityInput.value = vp.priority
}

function commitPriority(vp: PlannerVpRow) {
  editingPriority.value = null
  if (priorityInput.value !== vp.priority && priorityInput.value >= 1 && priorityInput.value <= 9999) {
    store.setPriority(vp.job, vp.suffix, priorityInput.value)
  }
}

function toggleFire(vp: PlannerVpRow) {
  store.cycleTier(vp.job, vp.suffix)
}

// --- Queue helpers ---

function tierIcon(tier: PriorityTier | undefined): string {
  if (tier === 'hot') return '\u{1F525}'
  if (tier === 'urgent') return '\u26A1'
  return '\u2014'
}

function queueRowClass(vp: PlannerVpRow): Record<string, boolean> {
  const allDone = vp.operations.every((o) => o.status === 'done')
  return {
    'q-row-hot': vp.tier === 'hot',
    'q-row-urgent': vp.tier === 'urgent',
    'q-row-done': allDone,
  }
}

function opsProgress(vp: PlannerVpRow): string {
  return `${vp.ops_done ?? 0}/${vp.ops_total ?? vp.operations.length}`
}

function delayLabel(vp: PlannerVpRow): string {
  if (!vp.co_due_date) return '\u2014'
  if (vp.is_delayed && vp.delay_days != null) return `+${vp.delay_days}d`
  return 'OK'
}

function formatCoDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return `${d.getDate()}.${d.getMonth() + 1}.`
}

function vpSchedRange(vp: PlannerVpRow): { start: string; end: string } {
  let minStart: string | null = null
  let maxEnd: string | null = null
  for (const op of vp.operations) {
    const ss = op.sched_start
    const se = op.sched_end
    if (ss && (!minStart || ss < minStart)) minStart = ss
    if (se && (!maxEnd || se > maxEnd)) maxEnd = se
  }
  return {
    start: minStart ? formatSchedDt(minStart) : '\u2014',
    end: maxEnd ? formatSchedDt(maxEnd) : '\u2014',
  }
}

function formatSchedDt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = d.getDate()
  const month = d.getMonth() + 1
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${day}.${month}. ${hh}:${mm}`
}

function deadlineBadge(vp: PlannerVpRow): string {
  if (!vp.co_due_date) return ''
  if (vp.is_delayed) return `+${vp.delay_days}d`
  return 'OK'
}

function formatQty(vp: PlannerVpRow): string {
  const c = vp.qty_complete ?? 0
  const r = vp.qty_released ?? 0
  return `${c}/${r} ks`
}
</script>

<template>
  <div class="pp">
    <!-- Toolbar -->
    <div class="pp-toolbar">
      <button class="pp-btn" :disabled="store.loading" @click="store.fetchData()">Refresh</button>
      <!-- View mode toggle -->
      <div class="pp-view-toggle">
        <button
          class="pp-btn pp-btn-toggle"
          :class="{ active: viewMode === 'queue' }"
          @click="viewMode = 'queue'"
        >Fronta</button>
        <button
          class="pp-btn pp-btn-toggle"
          :class="{ active: viewMode === 'vp' }"
          @click="viewMode = 'vp'"
        >VP Gantt</button>
        <button
          class="pp-btn pp-btn-toggle"
          :class="{ active: viewMode === 'wc' }"
          @click="viewMode = 'wc'"
        >WC Gantt</button>
      </div>
      <input
        v-model="searchQuery"
        type="text"
        class="pp-search"
        placeholder="Hledat..."
      />
      <template v-if="viewMode !== 'queue'">
        <button class="pp-btn" @click="scrollToToday">Dnes</button>
        <div class="pp-zoom">
          <button class="pp-btn pp-btn-sm" :disabled="zoomIdx <= 0" @click="zoomOut">-</button>
          <input
            type="range"
            class="pp-zoom-slider"
            :min="0"
            :max="ZOOM_STEPS.length - 1"
            :value="zoomIdx"
            @input="zoomAroundCenter(Number(($event.target as HTMLInputElement).value))"
          />
          <button class="pp-btn pp-btn-sm" :disabled="zoomIdx >= ZOOM_STEPS.length - 1" @click="zoomIn">+</button>
          <span class="pp-zoom-label">{{ ZOOM_LABELS[zoomLevel] ?? zoomLevel + 'px/d' }}</span>
        </div>
        <div class="pp-legend">
          <span class="pp-legend-item"><span class="pp-legend-dot dot-done"></span>Hotovo</span>
          <span class="pp-legend-item"><span class="pp-legend-dot dot-wip"></span>Rozprac.</span>
          <span class="pp-legend-item"><span class="pp-legend-dot dot-idle"></span>Idle</span>
          <span class="pp-legend-item"><span class="pp-legend-dot dot-coop"></span>KOO</span>
        </div>
      </template>
      <Spinner v-if="store.loading" size="sm" />
    </div>

    <!-- Queue view -->
    <div v-if="viewMode === 'queue'" class="pp-queue-wrap">
      <table class="pp-queue">
        <thead>
          <tr>
            <th class="q-num">#</th>
            <th class="q-tier">Tier</th>
            <th>VP</th>
            <th>Pol.</th>
            <th>Popis</th>
            <th>Zak.</th>
            <th>Termin CO</th>
            <th>Postup</th>
            <th>Zpozd.</th>
            <th>Sched start</th>
            <th>Sched end</th>
            <th>Prio</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(vp, idx) in filteredVps"
            :key="vpKey(vp)"
            :class="queueRowClass(vp)"
          >
            <td class="q-num">{{ idx + 1 }}</td>
            <td class="q-tier-cell">
              <button
                class="q-tier-btn"
                :title="`Tier: ${vp.tier ?? 'normal'} — klikni pro změnu`"
                @click="store.cycleTier(vp.job, vp.suffix)"
              >{{ tierIcon(vp.tier) }}</button>
            </td>
            <td class="q-job">{{ vp.job }}/{{ vp.suffix }}</td>
            <td class="q-item">{{ vp.item ?? '' }}</td>
            <td class="q-desc">{{ vp.description ?? '' }}</td>
            <td class="q-cust">{{ vp.customer_name ?? '' }}</td>
            <td>{{ formatCoDate(vp.co_due_date) }}</td>
            <td>{{ opsProgress(vp) }}</td>
            <td :class="{ 'q-late': vp.is_delayed }">{{ delayLabel(vp) }}</td>
            <td>{{ vpSchedRange(vp).start }}</td>
            <td>{{ vpSchedRange(vp).end }}</td>
            <td>
              <template v-if="editingPriority === vpKey(vp)">
                <input
                  v-model.number="priorityInput"
                  type="number"
                  min="1"
                  max="9999"
                  class="pp-prio-input"
                  @blur="commitPriority(vp)"
                  @keydown.enter="commitPriority(vp)"
                  @keydown.escape="editingPriority = null"
                />
              </template>
              <template v-else>
                <span class="pp-prio" @click="startEditPriority(vp)">{{ vp.priority }}</span>
              </template>
            </td>
          </tr>
          <tr v-if="!filteredVps.length && !store.loading">
            <td colspan="12" class="pp-empty">
              {{ searchQuery ? 'Nic nenalezeno' : 'Zadna VP data' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Gantt area -->
    <div v-else class="pp-gantt" @wheel="onWheel">
      <div ref="scrollRef" class="pp-scroll">
        <table class="pp-table" :style="{ '--tl-w': timelineWidth + 'px' }">
          <thead>
            <tr>
              <th class="pp-info-col pp-header-cell">{{ viewMode === 'vp' ? 'VP' : 'WC' }}</th>
              <th class="pp-tl-col pp-header-cell">
                <div class="pp-tl-header" :style="{ width: timelineWidth + 'px' }">
                  <div
                    v-for="tick in dateTicks"
                    :key="tick.left"
                    class="pp-tick"
                    :class="{ major: tick.major }"
                    :style="{ left: tick.left + 'px' }"
                  >
                    {{ tick.label }}
                  </div>
                  <div class="pp-today" :style="{ left: todayOffset + 'px' }" />
                </div>
              </th>
            </tr>
          </thead>

          <!-- ============ VP View ============ -->
          <tbody v-if="viewMode === 'vp'">
            <tr v-for="vp in filteredVps" :key="vpKey(vp)" :class="{ 'pp-row-hot': vp.tier === 'hot', 'pp-row-urgent': vp.tier === 'urgent', 'pp-row-done': vp.operations.every(o => o.status === 'done') }">
              <!-- VP info cell -->
              <td class="pp-info-col pp-info-cell">
                <div class="pp-vp-info">
                  <button
                    class="pp-fire"
                    :class="{ active: vp.tier === 'hot' || vp.tier === 'urgent' }"
                    :title="`Tier: ${vp.tier ?? 'normal'} — klikni pro změnu`"
                    @click="toggleFire(vp)"
                  >
                    <span v-if="vp.tier === 'hot'" class="fire-pulse">&#x1F525;</span>
                    <span v-else-if="vp.tier === 'urgent'">&#x26A1;</span>
                    <span v-else>&#x1F525;</span>
                  </button>
                  <div class="pp-vp-details">
                    <div class="pp-vp-job">{{ vp.job }}/{{ vp.suffix }}</div>
                    <div class="pp-vp-item" :title="vp.description ?? ''">{{ vp.item ?? '' }} {{ vp.description ?? '' }}</div>
                    <div class="pp-vp-meta">
                      <template v-if="editingPriority === vpKey(vp)">
                        <input
                          v-model.number="priorityInput"
                          type="number"
                          min="1"
                          max="9999"
                          class="pp-prio-input"
                          @blur="commitPriority(vp)"
                          @keydown.enter="commitPriority(vp)"
                          @keydown.escape="editingPriority = null"
                        />
                      </template>
                      <template v-else>
                        <span class="pp-prio" @click="startEditPriority(vp)">P:{{ vp.priority }}</span>
                      </template>
                      <span v-if="vp.customer_name" class="pp-cust">{{ vp.customer_name }}</span>
                      <span v-if="vp.co_num" class="pp-co">{{ vp.co_num }}</span>
                    </div>
                    <div class="pp-vp-bottom">
                      <span class="pp-qty">{{ formatQty(vp) }}</span>
                      <span
                        v-if="vp.co_due_date"
                        class="pp-deadline"
                        :class="{ late: vp.is_delayed, ok: !vp.is_delayed }"
                      >
                        DL:{{ vp.co_due_date?.slice(5) }} {{ deadlineBadge(vp) }}
                      </span>
                    </div>
                  </div>
                </div>
              </td>
              <!-- Timeline cell -->
              <td class="pp-tl-col pp-tl-cell">
                <div class="pp-tl-row" :style="{ width: timelineWidth + 'px' }">
                  <div
                    v-for="op in vp.operations"
                    :key="op.oper_num"
                    class="pp-bar"
                    :class="opBarClass(op.status, op.wc)"
                    :style="{
                      left: opBarLeft(op) + 'px',
                      width: opBarWidth(op) + 'px',
                    }"
                    :title="`${op.oper_num} ${op.wc ?? ''} (${op.status}) ${formatDuration(op)} ${formatNorm(op)}`"
                  >
                    <span class="pp-bar-label">{{ op.wc ?? op.oper_num }}</span>
                  </div>
                  <!-- CO deadline marker -->
                  <div
                    v-if="vp.co_due_date"
                    class="pp-dl-marker"
                    :class="{ late: vp.is_delayed }"
                    :style="{ left: dateToX(vp.co_due_date) + 'px' }"
                    :title="'Deadline: ' + vp.co_due_date"
                  >
                    <span class="pp-dl-label">DL</span>
                  </div>
                  <!-- Today marker -->
                  <div class="pp-today" :style="{ left: todayOffset + 'px' }" />
                </div>
              </td>
            </tr>
            <tr v-if="!filteredVps.length && !store.loading">
              <td colspan="2" class="pp-empty">
                {{ searchQuery ? 'Nic nenalezeno' : 'Žádná VP data' }}
              </td>
            </tr>
          </tbody>

          <!-- ============ WC View ============ -->
          <tbody v-else>
            <tr v-for="lane in filteredWcLanes" :key="lane.wc">
              <!-- WC info cell -->
              <td class="pp-info-col pp-info-cell">
                <div class="pp-wc-info">
                  <div class="pp-wc-code">{{ lane.wc }}</div>
                  <div class="pp-wc-count">{{ lane.ops.length }} ops</div>
                </div>
              </td>
              <!-- Timeline cell -->
              <td class="pp-tl-col pp-tl-cell">
                <div class="pp-tl-row" :style="{ width: timelineWidth + 'px' }">
                  <div
                    v-for="op in lane.ops"
                    :key="`${op.job}-${op.suffix}-${op.oper_num}`"
                    class="pp-bar"
                    :class="[opBarClass(op.status, lane.wc), { 'bar-hot': op.is_hot }]"
                    :style="{
                      left: wcOpBarLeft(op) + 'px',
                      width: wcOpBarWidth(op) + 'px',
                    }"
                    :title="`${op.job}/${op.suffix} OP${op.oper_num} ${op.status} ${formatDuration(op)} ${formatNorm(op)}`"
                  >
                    <span class="pp-bar-label">{{ op.job.slice(-4) }}/{{ op.oper_num }}</span>
                  </div>
                  <!-- Today marker -->
                  <div class="pp-today" :style="{ left: todayOffset + 'px' }" />
                </div>
              </td>
            </tr>
            <tr v-if="!filteredWcLanes.length && !store.loading">
              <td colspan="2" class="pp-empty">
                {{ searchQuery ? 'Nic nenalezeno' : 'Žádná WC data' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pp {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-size: var(--fsm, 12px);
}

/* Toolbar */
.pp-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.pp-btn {
  padding: 3px 10px;
  border: 1px solid var(--b2);
  border-radius: 4px;
  background: var(--surface);
  color: var(--t1);
  cursor: pointer;
  font-size: var(--fsm);
}
.pp-btn:hover { background: var(--b1); }
.pp-btn-sm { padding: 2px 6px; min-width: 24px; }

/* View toggle */
.pp-view-toggle {
  display: flex;
  gap: 0;
}
.pp-btn-toggle {
  border-radius: 0;
  border-right-width: 0;
}
.pp-btn-toggle:first-child { border-radius: 4px 0 0 4px; }
.pp-btn-toggle:last-child { border-radius: 0 4px 4px 0; border-right-width: 1px; }
.pp-btn-toggle.active {
  background: var(--chart-machining);
  color: var(--t-inv, #fff);
  border-color: var(--chart-machining);
}

.pp-search {
  flex: 1;
  max-width: 200px;
  padding: 3px 8px;
  border: 1px solid var(--b2);
  border-radius: 4px;
  background: var(--surface);
  color: var(--t1);
  font-size: var(--fsm);
}
.pp-zoom {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}
.pp-zoom-slider {
  width: 100px;
  height: 14px;
  accent-color: var(--chart-machining);
  cursor: pointer;
}
.pp-zoom-label {
  color: var(--t4);
  font-size: 10px;
  min-width: 52px;
  text-align: center;
  white-space: nowrap;
}

/* Legend */
.pp-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: var(--t3);
}
.pp-legend-item {
  display: flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.pp-legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}
.dot-done { background: var(--ok); opacity: 0.6; }
.dot-wip { background: var(--chart-machining); }
.dot-idle { background: var(--t4); opacity: 0.7; }
.dot-coop { background: var(--chart-cooperation); }

/* Gantt scroll area */
.pp-gantt {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
.pp-scroll {
  width: 100%;
  height: 100%;
  overflow: auto;
}

/* Table layout */
.pp-table {
  border-collapse: collapse;
  table-layout: fixed;
}
.pp-info-col {
  width: 260px;
  min-width: 260px;
  max-width: 260px;
  position: sticky;
  left: 0;
  z-index: 3;
  background: var(--surface);
}
.pp-tl-col {
  width: var(--tl-w);
  min-width: var(--tl-w);
}

/* Sticky header */
.pp-header-cell {
  position: sticky;
  top: 0;
  z-index: 4;
  background: var(--surface);
  border-bottom: 1px solid var(--b1);
  padding: 0;
  height: 28px;
}
.pp-info-col.pp-header-cell {
  z-index: 5;
}

/* Timeline header */
.pp-tl-header {
  position: relative;
  height: 28px;
}
.pp-tick {
  position: absolute;
  top: 10px;
  font-size: 9px;
  color: var(--t4);
  white-space: nowrap;
  transform: translateX(-50%);
  opacity: 0.7;
}
.pp-tick.major {
  font-weight: 700;
  font-size: 10px;
  color: var(--t2);
  opacity: 1;
}
.pp-tick::after {
  content: '';
  position: absolute;
  top: -2px;
  left: 50%;
  width: 1px;
  height: 6px;
  background: var(--b2);
}
.pp-tick.major::after {
  height: 10px;
  background: var(--t4);
}

/* VP info cell */
.pp-info-cell {
  padding: 4px 6px;
  border-bottom: 1px solid var(--b1);
  border-right: 1px solid var(--b1);
  height: 48px;
  vertical-align: top;
}
.pp-vp-info {
  display: flex;
  gap: 4px;
  height: 100%;
}
.pp-fire {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  opacity: 0.3;
  flex-shrink: 0;
  width: 20px;
  line-height: 1;
}
.pp-fire.active { opacity: 1; }
.fire-pulse {
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.pp-vp-details {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.pp-vp-job {
  font-weight: 700;
  font-size: 11px;
  color: var(--t1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pp-vp-item {
  font-size: 10px;
  color: var(--t3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pp-vp-meta {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 10px;
}
.pp-prio {
  color: var(--t2);
  cursor: pointer;
  padding: 0 2px;
  border-radius: 2px;
}
.pp-prio:hover { background: var(--b1); }
.pp-prio-input {
  width: 48px;
  padding: 0 2px;
  border: 1px solid var(--b2);
  border-radius: 2px;
  font-size: 10px;
  background: var(--surface);
  color: var(--t1);
}
.pp-cust, .pp-co {
  color: var(--t4);
  font-size: 10px;
}
.pp-vp-bottom {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 10px;
}
.pp-qty { color: var(--t3); }
.pp-deadline {
  font-weight: 600;
  border-radius: 2px;
  padding: 0 3px;
}
.pp-deadline.ok { color: var(--ok); }
.pp-deadline.late { color: var(--red); background: rgba(229, 57, 53, 0.1); }

/* WC info cell */
.pp-wc-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  gap: 2px;
}
.pp-wc-code {
  font-weight: 700;
  font-size: 12px;
  color: var(--t1);
}
.pp-wc-count {
  font-size: 10px;
  color: var(--t4);
}

/* Timeline cell */
.pp-tl-cell {
  padding: 0;
  border-bottom: 1px solid var(--b1);
  height: 48px;
  vertical-align: middle;
}
.pp-tl-row {
  position: relative;
  height: 48px;
}

/* Operation bars */
.pp-bar {
  position: absolute;
  top: 8px;
  height: 14px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  overflow: hidden;
  cursor: default;
}
.pp-bar-label {
  font-size: 9px;
  padding: 0 3px;
  color: var(--t-inv, #fff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Bar colors */
.bar-done {
  background: var(--ok);
  opacity: 0.6;
}
.bar-in_progress {
  background: var(--chart-machining);
}
.bar-idle {
  background: var(--t4);
  opacity: 0.7;
}
.bar-coop {
  background: var(--chart-cooperation);
}
.bar-hot {
  box-shadow: 0 0 0 1px rgba(229, 57, 53, 0.6);
}

/* CO Deadline marker */
.pp-dl-marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  border-left: 2px dashed var(--ok);
  opacity: 0.8;
}
.pp-dl-marker.late {
  border-left-color: var(--red);
}
.pp-dl-label {
  position: absolute;
  top: -1px;
  left: 3px;
  font-size: 8px;
  font-weight: 700;
  color: var(--t4);
  white-space: nowrap;
}

/* Today marker */
.pp-today {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--red);
  z-index: 2;
}

/* Row states */
.pp-row-hot .pp-info-cell {
  background: rgba(229, 57, 53, 0.06);
}
.pp-row-urgent .pp-info-cell {
  background: rgba(255, 193, 7, 0.08);
}
.pp-row-done {
  opacity: 0.4;
}

/* Empty state */
.pp-empty {
  text-align: center;
  color: var(--t4);
  padding: 24px;
}

/* ============ Queue View ============ */
.pp-queue-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.pp-queue {
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
}
.pp-queue th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface);
  color: var(--t3);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 1px solid var(--b2);
  padding: 5px 6px;
  text-align: left;
  white-space: nowrap;
}
.pp-queue td {
  padding: 4px 6px;
  border-bottom: 1px solid var(--b1);
  font-size: var(--fsm, 12px);
  color: var(--t2);
  white-space: nowrap;
}
.pp-queue tbody tr:hover {
  background: var(--surface);
}
.q-num {
  text-align: right;
  color: var(--t4);
  font-size: 10px;
  width: 28px;
}
.q-tier { width: 36px; text-align: center; }
.q-tier-cell { text-align: center; }
.q-tier-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
  line-height: 1;
}
.q-job {
  font-weight: 700;
  font-size: 11px;
  color: var(--t1);
}
.q-item {
  font-family: var(--mono, monospace);
  font-size: 11px;
}
.q-desc {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--t3);
}
.q-cust {
  color: var(--t3);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.q-late { color: var(--red); font-weight: 600; }

/* Queue row states */
.q-row-hot td { background: rgba(229, 57, 53, 0.07); }
.q-row-urgent td { background: rgba(255, 193, 7, 0.07); }
.q-row-done { opacity: 0.4; }
</style>
