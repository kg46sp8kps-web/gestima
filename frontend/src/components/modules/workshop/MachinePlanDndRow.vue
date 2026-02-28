<script setup lang="ts">
import { GripVertical, Flame, Zap, Snowflake } from 'lucide-vue-next'
import { formatDate } from '@/utils/formatters'
import { ICON_SIZE_SM } from '@/config/design'
import type { MachinePlanItem } from '@/types/workshop'

interface Props {
  item: MachinePlanItem
  active?: boolean
  mode: 'planned' | 'unassigned'
}

defineProps<Props>()
defineEmits<{
  select: [item: MachinePlanItem]
  'cycle-tier': [item: MachinePlanItem]
}>()

function jobLabel(item: MachinePlanItem): string {
  const suffix = item.Suffix && item.Suffix !== '0' ? `/${item.Suffix}` : ''
  return `${item.Job}${suffix}`
}

function formatQty(item: MachinePlanItem): string {
  const complete = item.QtyComplete ?? 0
  const released = item.JobQtyReleased ?? 0
  return `${complete}/${released}`
}

function formatDueDate(item: MachinePlanItem): string {
  if (!item.OrderDueDate) return '—'
  return formatDate(item.OrderDueDate)
}

function statBadgeClass(stat: string): string {
  switch (stat) {
    case 'R': return 'stat-badge stat-badge--r'
    case 'F': return 'stat-badge stat-badge--f'
    case 'S': return 'stat-badge stat-badge--s'
    case 'W': return 'stat-badge stat-badge--w'
    default: return 'stat-badge'
  }
}
</script>

<template>
  <div
    :class="[
      'mpd-row',
      `mpd-row--${mode}`,
      { 'mpd-row--active': active, 'mpd-row--hot': item.IsHot, 'mpd-row--urgent': item.Tier === 'urgent', 'mpd-row--frozen': item.Tier === 'frozen' },
    ]"
    @click="$emit('select', item)"
  >
    <!-- Tier toggle -->
    <button
      class="mpd-row__tier"
      :class="{
        'mpd-row__tier--hot': item.IsHot,
        'mpd-row__tier--urgent': item.Tier === 'urgent',
        'mpd-row__tier--frozen': item.Tier === 'frozen',
      }"
      :title="`Tier: ${item.Tier ?? 'normal'} — klikni pro změnu`"
      @click.stop="$emit('cycle-tier', item)"
    >
      <Flame v-if="item.IsHot" :size="14" />
      <Zap v-else-if="item.Tier === 'urgent'" :size="14" />
      <Snowflake v-else-if="item.Tier === 'frozen'" :size="14" />
      <span v-else class="mpd-row__tier-dash">&mdash;</span>
    </button>

    <!-- Drag handle (only in planned mode) -->
    <div v-if="mode === 'planned'" class="mpd-row__grip drag-handle">
      <GripVertical :size="ICON_SIZE_SM" />
    </div>

    <div class="mpd-row__body">
      <div class="mpd-row__main">
        <span class="mpd-row__job">{{ jobLabel(item) }}</span>
        <span class="mpd-row__oper">Op {{ item.OperNum }}</span>
        <span :class="statBadgeClass(item.JobStat ?? 'R')">{{ item.JobStat ?? 'R' }}</span>
      </div>
      <div class="mpd-row__detail">
        <span class="mpd-row__item">{{ item.DerJobItem ?? '—' }}</span>
        <span class="mpd-row__desc">{{ item.JobDescription ?? '—' }}</span>
      </div>
      <div class="mpd-row__meta">
        <span class="mpd-row__qty">{{ formatQty(item) }} ks</span>
        <span class="mpd-row__due" :title="item.CoNum ? `Zakázka ${item.CoNum}` : undefined">
          {{ formatDueDate(item) }}
        </span>
      </div>
    </div>

  </div>
</template>

<style scoped>
.mpd-row {
  display: flex;
  align-items: stretch;
  padding: 5px 6px;
  border-bottom: 1px solid var(--b0, rgba(255,255,255,0.04));
  cursor: pointer;
  transition: background 0.1s;
  gap: 4px;
}
.mpd-row:hover {
  background: var(--hover, rgba(255,255,255,0.04));
}
.mpd-row--active {
  background: var(--active, rgba(255,255,255,0.08)) !important;
  border-left: 3px solid var(--green, #4caf50);
  padding-left: 3px;
}
.mpd-row--unassigned {
  opacity: 0.6;
}
.mpd-row--hot {
  border-left: 3px solid var(--red, #ef5350);
  padding-left: 3px;
  background: color-mix(in srgb, var(--red, #ef5350) 6%, transparent);
}
.mpd-row--urgent {
  border-left: 3px solid var(--amber, #ff9800);
  padding-left: 3px;
}
.mpd-row--frozen {
  border-left: 3px solid var(--cyan, #00bcd4);
  padding-left: 3px;
  background: color-mix(in srgb, var(--cyan, #00bcd4) 4%, transparent);
}
.mpd-row__tier {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 22px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--t4);
  transition: color 0.15s;
}
.mpd-row__tier:hover {
  color: var(--t2);
}
.mpd-row__tier--hot {
  color: var(--red, #ef5350);
  animation: pulse-hot 1.5s ease-in-out infinite;
}
.mpd-row__tier--hot:hover {
  color: var(--red, #ef5350);
}
.mpd-row__tier--urgent {
  color: var(--amber, #ff9800);
}
.mpd-row__tier--urgent:hover {
  color: var(--amber, #ff9800);
}
.mpd-row__tier--frozen {
  color: var(--cyan, #00bcd4);
}
.mpd-row__tier--frozen:hover {
  color: var(--cyan, #00bcd4);
}
.mpd-row__tier-dash {
  font-size: 12px;
  line-height: 1;
}
@keyframes pulse-hot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.mpd-row__grip {
  display: flex;
  align-items: center;
  color: var(--t4);
  cursor: grab;
  flex-shrink: 0;
  padding: 0 2px;
}
.mpd-row__grip:active { cursor: grabbing; }

.mpd-row__body {
  flex: 1;
  min-width: 0;
}

.mpd-row__main {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mpd-row__job {
  font-weight: 700;
  font-size: var(--fs);
  color: var(--t1);
}
.mpd-row__oper {
  font-size: var(--fsm);
  color: var(--t3);
}

.mpd-row__detail {
  display: flex;
  gap: 8px;
  margin-top: 1px;
}
.mpd-row__item {
  font-size: var(--fsm);
  color: var(--t2);
  font-weight: 500;
}
.mpd-row__desc {
  font-size: var(--fsm);
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.mpd-row__meta {
  display: flex;
  gap: 10px;
  margin-top: 1px;
}
.mpd-row__qty {
  font-size: var(--fsm);
  color: var(--t2);
  font-variant-numeric: tabular-nums;
}
.mpd-row__due {
  font-size: var(--fsm);
  color: var(--t3);
  font-variant-numeric: tabular-nums;
}
.mpd-row--hot .mpd-row__due {
  color: var(--red, #ef5350);
  font-weight: 600;
}
.mpd-row--urgent .mpd-row__due {
  color: var(--amber, #ff9800);
}

/* Status badges */
.stat-badge {
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
</style>
