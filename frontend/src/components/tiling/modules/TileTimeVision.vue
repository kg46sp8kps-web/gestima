<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as timeVisionApi from '@/api/time-vision'
import type { TimeVisionListItem } from '@/types/admin-user'
import type { ContextGroup } from '@/types/workspace'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<TimeVisionListItem[]>([])
const loading = ref(false)
const error = ref(false)

function statusDot(status: string): string {
  if (status === 'verified') return 'ok'
  if (status === 'estimated' || status === 'calibrated') return 'brand'
  return 'neutral'
}

function accuracyPct(item: TimeVisionListItem): string {
  const est = item.estimated_time_min
  const act = item.actual_time_min
  if (est == null || act == null || est === 0) return '—'
  const pct = Math.abs(act - est) / est * 100
  return pct.toFixed(1) + ' %'
}

function accuracyClass(item: TimeVisionListItem): string {
  const est = item.estimated_time_min
  const act = item.actual_time_min
  if (est == null || act == null || est === 0) return ''
  const pct = Math.abs(act - est) / est * 100
  if (pct < 10) return 'acc-ok'
  if (pct < 25) return 'acc-warn'
  return 'acc-err'
}

async function load() {
  loading.value = true
  error.value = false
  try {
    items.value = await timeVisionApi.listEstimations(100)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wtv">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!items.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádné estimace</span>
    </div>

    <!-- Data -->
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th>Soubor / díl</th>
            <th style="width:60px">Status</th>
            <th class="r" style="width:64px">Odhad min</th>
            <th class="r" style="width:64px">Skut. min</th>
            <th class="r" style="width:56px">Přesnost</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="item.id"
            :data-testid="`tv-row-${item.id}`"
          >
            <td>
              <div class="tv-name">{{ item.pdf_filename }}</div>
              <div v-if="item.part_id" class="tv-sub t4">Díl #{{ item.part_id }}</div>
            </td>
            <td>
              <span class="badge">
                <span :class="['badge-dot', statusDot(item.status)]" />
                {{ item.status }}
              </span>
            </td>
            <td class="r">
              {{ item.estimated_time_min != null ? formatNumber(item.estimated_time_min, 1) : '—' }}
            </td>
            <td class="r">
              {{ item.actual_time_min != null ? formatNumber(item.actual_time_min, 1) : '—' }}
            </td>
            <td :class="['r', accuracyClass(item)]">{{ accuracyPct(item) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.wtv {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.t4 { color: var(--t4); }
.r { text-align: right; }

.tv-name { font-weight: 500; color: var(--t1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; }
.tv-sub { font-size: var(--fsm); margin-top: 1px; }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-size: var(--fsm);
  font-weight: 500;
  border-radius: 99px;
  background: var(--b1);
  color: var(--t2);
}
.badge-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  flex-shrink: 0;
}
.badge-dot.ok { background: var(--ok); }
.badge-dot.brand { background: var(--t3); }
.badge-dot.neutral { background: var(--t4); }

.acc-ok   { color: var(--ok); }
.acc-warn { color: var(--warn); }
.acc-err  { color: var(--err); }
</style>
