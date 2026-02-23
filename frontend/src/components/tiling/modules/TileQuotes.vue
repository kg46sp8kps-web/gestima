<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as quotesApi from '@/api/quotes'
import type { QuoteListItem } from '@/types/quote'
import type { ContextGroup } from '@/types/workspace'
import { formatCurrency, formatDate } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<QuoteListItem[]>([])
const loading = ref(false)
const error = ref(false)
const statusFilter = ref<'all' | 'DRAFT' | 'SENT' | 'APPROVED' | 'REJECTED'>('all')

const STATUS_LABELS: Record<string, string> = {
  DRAFT:    'Rozpracovaná',
  SENT:     'Odeslaná',
  APPROVED: 'Schválená',
  REJECTED: 'Zamítnutá',
}

const filtered = computed(() =>
  statusFilter.value === 'all'
    ? items.value
    : items.value.filter(q => q.status === statusFilter.value),
)

const counts = computed(() => ({
  all:      items.value.length,
  DRAFT:    items.value.filter(q => q.status === 'DRAFT').length,
  SENT:     items.value.filter(q => q.status === 'SENT').length,
  APPROVED: items.value.filter(q => q.status === 'APPROVED').length,
  REJECTED: items.value.filter(q => q.status === 'REJECTED').length,
}))

async function load() {
  loading.value = true
  error.value = false
  try {
    items.value = await quotesApi.getAll()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wquo">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data (incl. empty) -->
    <template v-else>
      <!-- Status filter tabs -->
      <div class="tab-bar">
        <button
          v-for="s in (['all', 'DRAFT', 'SENT', 'APPROVED', 'REJECTED'] as const)"
          :key="s"
          :class="['ptab', { on: statusFilter === s }]"
          :data-testid="`quote-filter-${s}`"
          @click="statusFilter = s"
        >
          {{ s === 'all' ? 'Vše' : STATUS_LABELS[s] }}
          <span class="tab-count">{{ counts[s] }}</span>
        </button>
      </div>

      <!-- Empty state -->
      <div v-if="!filtered.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">Žádné nabídky</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:82px">Číslo</th>
              <th>Název</th>
              <th style="width:88px">Status</th>
              <th class="r" style="width:90px">Celkem</th>
              <th style="width:88px">Termín</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="q in filtered"
              :key="q.id"
              :data-testid="`quote-row-${q.id}`"
            >
              <td class="t4">{{ q.quote_number }}</td>
              <td class="title-cell">{{ q.title }}</td>
              <td>
                <span :class="['status-badge', `s-${q.status.toLowerCase()}`]">
                  {{ STATUS_LABELS[q.status] }}
                </span>
              </td>
              <td class="r">{{ formatCurrency(q.total) }}</td>
              <td class="t4">{{ formatDate(q.offer_deadline) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wquo {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Placeholder ─── */
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

/* ─── Status filter tabs ─── */
.tab-bar {
  display: flex;
  gap: 1px;
  padding: 4px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  overflow-x: auto;
}
.ptab { padding: 3px 7px; font-size: var(--fsx); font-weight: 500; color: var(--t4); background: transparent; border: none; border-radius: var(--rs); cursor: pointer; font-family: var(--font); display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
.tab-count {
  font-size: var(--fss);
  color: var(--t4);
}
.ptab.on .tab-count { color: var(--t3); }

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Table ─── */

.t4 { color: var(--t4); }
.title-cell {
  max-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ─── Status badge ─── */
.status-badge {
  display: inline-block;
  font-size: var(--fss);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 1px 5px;
  border-radius: var(--rs);
  background: var(--b1);
  color: var(--t4);
}
.status-badge.s-draft    { background: var(--b1);       color: var(--t3); }
.status-badge.s-sent     { background: var(--b2);       color: var(--t2); }
.status-badge.s-approved { background: var(--green-10); color: var(--green); }
.status-badge.s-rejected { background: rgba(255,255,255,0.04); color: var(--err); }
</style>
