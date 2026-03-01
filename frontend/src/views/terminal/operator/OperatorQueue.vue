<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'
import { getMachinePlanDnd } from '@/api/machinePlanDnd'
import type { MachinePlanItem } from '@/types/workshop'
import JobCard from '../shared/JobCard.vue'

const router = useRouter()
const operator = useOperatorStore()

const loading = ref(false)
const refreshing = ref(false)
const plannedItems = ref<MachinePlanItem[]>([])

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

onMounted(async () => {
  if (targetWcs.value.length === 0) {
    router.replace({ name: 'terminal-dashboard' })
    return
  }
  await loadQueue()
})

async function fetchForWcs(wcs: string[]): Promise<MachinePlanItem[]> {
  const results = await Promise.all(wcs.map(wc => getMachinePlanDnd(wc)))
  // For group view: include both planned and unassigned items from all WCs
  // For single WC: only planned (preserves DnD order)
  const all = isGroup.value
    ? results.flatMap(r => [...r.planned, ...r.unassigned])
    : results.flatMap(r => r.planned)
  // Sort by OpDatumSt ascending
  all.sort((a, b) => {
    const da = a.OpDatumSt ?? ''
    const db = b.OpDatumSt ?? ''
    return da < db ? -1 : da > db ? 1 : 0
  })
  return all
}

async function loadQueue() {
  loading.value = true
  try {
    plannedItems.value = await fetchForWcs(targetWcs.value)
  } finally {
    loading.value = false
  }
}

async function doRefresh() {
  refreshing.value = true
  try {
    plannedItems.value = await fetchForWcs(targetWcs.value)
  } finally {
    refreshing.value = false
  }
}

function goToJob(job: string, oper: string) {
  operator.touchActivity()
  router.push({ name: 'terminal-job-detail', params: { job, oper } })
}
</script>

<template>
  <div class="queue">
    <!-- Header -->
    <div class="queue-header">
      <div class="queue-info">
        <h2 class="queue-title">Fronta práce</h2>
        <span class="queue-wc">{{ headerLabel }}</span>
        <span v-if="isGroup" class="queue-group-tag">{{ targetWcs.length }} WC</span>
        <span class="queue-count">{{ plannedItems.length }} operací</span>
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

    <!-- Loading -->
    <div v-if="loading" class="queue-loading">Načítám frontu...</div>

    <!-- Empty -->
    <div v-else-if="plannedItems.length === 0" class="queue-empty">
      Fronta je prázdná
    </div>

    <!-- Queue list — identical data and order as DnD planned section -->
    <div v-else class="queue-list">
      <JobCard
        v-for="item in plannedItems"
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
</style>
