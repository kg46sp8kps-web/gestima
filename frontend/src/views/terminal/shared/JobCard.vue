<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  job: string
  suffix?: string
  operNum: string
  wc?: string | null
  item?: string | null
  description?: string | null
  qtyReleased?: number | null
  qtyComplete?: number | null
  dueDate?: string | null
  orderDueDate?: string | null
  state?: string | null
  jobStat?: string | null
  tier?: 'hot' | 'urgent' | 'normal' | null
  isHot?: boolean
  running?: boolean
  elapsed?: string
  nextWc?: string | null
  primaryMaterial?: string | null
  isoGroup?: string | null
  showSawExtras?: boolean
}>()

defineEmits<{ click: [] }>()

const progress = computed(() => {
  if (!props.qtyReleased || props.qtyReleased <= 0) return 0
  return Math.min(100, Math.round(((props.qtyComplete ?? 0) / props.qtyReleased) * 100))
})

// Effective due date: prefer OrderDueDate (CO termín) over OpDatumSp
const effectiveDueDate = computed(() => props.orderDueDate ?? props.dueDate)

function parseDate(d: string): Date | null {
  if (d.length >= 8 && /^\d{8}/.test(d)) {
    return new Date(
      parseInt(d.slice(0, 4)),
      parseInt(d.slice(4, 6)) - 1,
      parseInt(d.slice(6, 8)),
    )
  }
  const dt = new Date(d)
  return isNaN(dt.getTime()) ? null : dt
}

const urgency = computed<'ok' | 'today' | 'overdue'>(() => {
  if (!effectiveDueDate.value) return 'ok'
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const due = parseDate(effectiveDueDate.value)
  if (!due) return 'ok'
  const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())
  if (dueDay < today) return 'overdue'
  if (dueDay.getTime() === today.getTime()) return 'today'
  return 'ok'
})

const urgencyLevel = computed(() => {
  // Tier overrides date-based urgency
  if (props.isHot || props.tier === 'hot') return 'hot'
  if (props.tier === 'urgent') return 'urgent'
  switch (urgency.value) {
    case 'overdue': return 'overdue'
    case 'today': return 'today'
    default: return 'ok'
  }
})

const tierClass = computed(() => {
  if (props.isHot || props.tier === 'hot') return 'hot'
  if (props.tier === 'urgent') return 'urgent'
  return ''
})

function statBadgeClass(stat: string): string {
  switch (stat) {
    case 'R': return 'jcard-stat jcard-stat--r'
    case 'F': return 'jcard-stat jcard-stat--f'
    case 'S': return 'jcard-stat jcard-stat--s'
    case 'W': return 'jcard-stat jcard-stat--w'
    default: return 'jcard-stat'
  }
}

function formatDate(d: string | null | undefined): string {
  if (!d) return ''
  // Handle YYYYMMDD
  if (d.length >= 8 && /^\d{8}/.test(d)) {
    return `${d.slice(6, 8)}.${d.slice(4, 6)}.${d.slice(0, 4)}`
  }
  // ISO date
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return d
  return dt.toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div :class="['jcard', { running, 'jcard--hot': tierClass === 'hot', 'jcard--urgent': tierClass === 'urgent', 'jcard--has-iso': showSawExtras && isoGroup }]" @click="$emit('click')">
    <!-- ISO group corner ribbon (SAW) -->
    <div v-if="showSawExtras && isoGroup" :class="['jcard-iso', `jcard-iso--${isoGroup.toLowerCase()}`]">
      <span class="jcard-iso-strip">{{ isoGroup }}</span>
    </div>

    <!-- Content: info + optional WC aside -->
    <div :class="['jcard-content', { 'jcard-content--aside': showSawExtras && nextWc }]">
      <div class="jcard-info">
        <div class="jcard-top">
          <div class="jcard-id">
            <!-- Tier icon -->
            <span v-if="tierClass === 'hot'" class="jcard-tier jcard-tier--hot" title="Hot">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 23c-3.6 0-7-2.4-7-7 0-3.3 2.3-5.8 4-7.5.5-.5 1.5-.2 1.5.5v2.2c0 .4.5.6.8.3C13.4 9.5 15 6.5 15 4c0-.7.8-1 1.3-.5C18.7 6 21 9.5 21 13c0 5.5-4 10-9 10z"/></svg>
            </span>
            <span v-else-if="tierClass === 'urgent'" class="jcard-tier jcard-tier--urgent" title="Urgent">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </span>
            <strong>{{ job }}</strong>
            <span class="jcard-oper">/ Op {{ operNum }}</span>
            <span v-if="jobStat" :class="statBadgeClass(jobStat)">{{ jobStat }}</span>
            <span v-if="wc && !showSawExtras" class="jcard-wc">{{ wc }}</span>
          </div>
          <span v-if="running && elapsed" class="jcard-timer">{{ elapsed }}</span>
          <span v-else-if="effectiveDueDate" :class="['jcard-due', `jcard-due--${urgencyLevel}`]">
            {{ formatDate(effectiveDueDate) }}
          </span>
        </div>

        <div v-if="item || description" class="jcard-desc">
          <span v-if="item" class="jcard-item">{{ item }}</span>
          <span v-if="description">{{ description }}</span>
        </div>

        <!-- SAW material tag -->
        <div v-if="showSawExtras && primaryMaterial" class="jcard-saw">
          <span class="jcard-saw-tag">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
            {{ primaryMaterial }}
          </span>
        </div>
      </div>

      <!-- WC aside (SAW) -->
      <div v-if="showSawExtras && nextWc" class="jcard-wc-aside">
        <span class="jcard-wc-card">{{ wc }}</span>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" class="jcard-wc-arrow"><polyline points="6 9 12 15 18 9"/></svg>
        <span class="jcard-wc-card jcard-wc-card--next">{{ nextWc }}</span>
      </div>
    </div>

    <!-- Progress bar (full width) -->
    <div v-if="qtyReleased" class="jcard-progress">
      <div class="jcard-bar">
        <div
          :class="['jcard-bar-fill', `jcard-bar-fill--${urgencyLevel}`]"
          :style="{ width: progress + '%' }"
        />
      </div>
      <span class="jcard-qty">{{ qtyComplete ?? 0 }} / {{ qtyReleased }} ks</span>
    </div>

    <div v-if="state" class="jcard-state">{{ state }}</div>
  </div>
</template>

<style scoped>
.jcard {
  position: relative;
  min-height: 88px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  padding: 14px 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: background 100ms, border-color 100ms;
  -webkit-tap-highlight-color: transparent;
  overflow: hidden;
}
.jcard--has-iso {
  padding-left: 28px;
}
/* Content wrapper: column by default, row when WC aside present */
.jcard-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.jcard-content--aside {
  flex-direction: row;
  align-items: stretch;
  gap: 0;
}
.jcard-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.jcard:active {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--t4);
}
.jcard.running {
  border-color: rgba(76, 175, 80, 0.3);
  background: rgba(76, 175, 80, 0.05);
}
.jcard--hot {
  border-left: 4px solid var(--red, #ef5350);
  background: color-mix(in srgb, var(--red, #ef5350) 6%, transparent);
}
.jcard--urgent {
  border-left: 4px solid var(--amber, #ff9800);
}

.jcard-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.jcard-id {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
  color: var(--t1);
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
.jcard-oper { color: var(--t3); }
.jcard-wc {
  color: var(--t4);
  font-size: 12px;
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 0 5px;
  margin-left: 4px;
}

.jcard-timer {
  font-size: 15px;
  font-weight: 600;
  color: var(--ok);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.jcard-due {
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}
.jcard-due--ok { color: var(--ok); }
.jcard-due--today { color: var(--warn); }
.jcard-due--overdue { color: var(--red); }
.jcard-due--hot { color: var(--red); font-weight: 600; }
.jcard-due--urgent { color: var(--amber); font-weight: 600; }

.jcard-desc {
  font-size: 13px;
  color: var(--t3);
  display: flex;
  gap: 6px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.jcard-item {
  color: var(--t2);
  font-weight: 500;
}

.jcard-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}
.jcard-bar {
  flex: 1;
  height: 4px;
  background: var(--b1);
  border-radius: 2px;
  overflow: hidden;
}
.jcard-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 300ms ease;
}
.jcard-bar-fill--ok { background: var(--ok); }
.jcard-bar-fill--today { background: var(--warn); }
.jcard-bar-fill--overdue { background: var(--red); }
.jcard-bar-fill--hot { background: var(--red); }
.jcard-bar-fill--urgent { background: var(--amber); }
.jcard-qty {
  font-size: 12px;
  color: var(--t3);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.jcard-state {
  font-size: 11px;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ISO group corner ribbon */
.jcard-iso {
  position: absolute;
  top: -1px;
  left: -1px;
  width: 36px;
  height: 36px;
  overflow: hidden;
  pointer-events: none;
  z-index: 1;
}
.jcard-iso-strip {
  position: absolute;
  top: 10px;
  left: -18px;
  width: 72px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: var(--t1, #fff);
  transform: rotate(-45deg);
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.jcard-iso--p .jcard-iso-strip { background: var(--blue, #2563eb); }
.jcard-iso--m .jcard-iso-strip { background: var(--amber, #ca8a04); }
.jcard-iso--k .jcard-iso-strip { background: var(--red, #dc2626); }
.jcard-iso--n .jcard-iso-strip { background: var(--green, #16a34a); }
.jcard-iso--s .jcard-iso-strip { background: var(--orange, #ea580c); }
.jcard-iso--h .jcard-iso-strip { background: var(--t4, #525252); }

/* SAW extras */
.jcard-saw {
  display: flex;
  align-items: center;
  gap: 8px;
}
/* WC side panel — spans full card height */
.jcard-wc-side {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding-left: 12px;
  margin-left: 4px;
  border-left: 1px solid var(--b2);
  flex-shrink: 0;
}
.jcard-wc-card {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--t2);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--b2);
  border-radius: 6px;
  min-width: 48px;
  text-align: center;
}
.jcard-wc-card--next {
  color: var(--t3);
  background: rgba(255, 255, 255, 0.03);
}
.jcard-wc-arrow {
  color: var(--t4);
  flex-shrink: 0;
}
.jcard-saw-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--t4);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 1px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 50%;
}

/* Tier icons */
.jcard-tier {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.jcard-tier--hot {
  color: var(--red, #ef5350);
  animation: pulse-hot 1.5s ease-in-out infinite;
}
.jcard-tier--urgent {
  color: var(--amber, #ff9800);
}
@keyframes pulse-hot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Status badges */
.jcard-stat {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 3px;
  line-height: 1;
}
.jcard-stat--r {
  background: color-mix(in srgb, var(--green, #4caf50) 20%, transparent);
  color: var(--green, #4caf50);
}
.jcard-stat--f {
  background: color-mix(in srgb, var(--amber, #ff9800) 20%, transparent);
  color: var(--amber, #ff9800);
}
.jcard-stat--s {
  background: color-mix(in srgb, var(--blue, #2196f3) 20%, transparent);
  color: var(--blue, #2196f3);
}
.jcard-stat--w {
  background: color-mix(in srgb, var(--t4) 20%, transparent);
  color: var(--t4);
}

/* Hot/urgent due date color is now handled by .jcard-due--hot / .jcard-due--urgent classes */
</style>
