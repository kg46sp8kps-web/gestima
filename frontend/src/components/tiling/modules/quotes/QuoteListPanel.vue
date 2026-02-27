<script setup lang="ts">
import { ref, computed } from 'vue'
import { BotIcon, PlusIcon } from 'lucide-vue-next'
import * as quotesApi from '@/api/quotes'
import type { QuoteListItem } from '@/types/quote'
import { useUiStore } from '@/stores/ui'
import { useQuotesListStore } from '@/stores/quotesList'
import { formatCurrency, formatDate } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE_SM } from '@/config/design'

const emit = defineEmits<{
  select: [quoteNumber: string | null]
  'new-quote': []
  loaded: [items: QuoteListItem[]]
}>()

interface Props {
  selectedQuoteNumber: string | null
}

const props = defineProps<Props>()

const ui = useUiStore()
const quotesStore = useQuotesListStore()
const items = ref<QuoteListItem[]>([])
const loading = ref(false)
const error = ref(false)
const searchQuery = ref('')
const statusFilter = ref<'all' | 'draft' | 'sent' | 'approved' | 'rejected'>('all')

const STATUS_LABELS: Record<string, string> = {
  draft:    'Rozpracovaná',
  sent:     'Odeslaná',
  approved: 'Schválená',
  rejected: 'Zamítnutá',
}

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let result = statusFilter.value === 'all'
    ? items.value
    : items.value.filter(it => it.status === statusFilter.value)
  if (q) {
    result = result.filter(it =>
      it.quote_number.toLowerCase().includes(q) ||
      it.title.toLowerCase().includes(q),
    )
  }
  return result
})

const counts = computed(() => ({
  all:      items.value.length,
  draft:    items.value.filter(it => it.status === 'draft').length,
  sent:     items.value.filter(it => it.status === 'sent').length,
  approved: items.value.filter(it => it.status === 'approved').length,
  rejected: items.value.filter(it => it.status === 'rejected').length,
}))

function statusDotClass(status: string): string {
  if (status === 'approved') return 'badge-dot-ok'
  if (status === 'rejected') return 'badge-dot-error'
  if (status === 'sent') return 'badge-dot-warn'
  return 'badge-dot-neutral'
}

function onRowClick(q: QuoteListItem) {
  emit('select', props.selectedQuoteNumber === q.quote_number ? null : q.quote_number)
}

function onAiClick() {
  ui.showInfo('AI Import z PDF — brzy dostupný')
}

async function load(force = false) {
  if (quotesStore.loaded && !force) {
    items.value = quotesStore.items
    emit('loaded', items.value)
    return
  }
  loading.value = true
  error.value = false
  try {
    const data = await quotesApi.getAll()
    items.value = data
    quotesStore.setItems(data)
    emit('loaded', items.value)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

defineExpose({ load })
</script>

<template>
  <div class="wquo-list">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Toolbar -->
      <div class="toolbar">
        <Input
          v-model="searchQuery"
          bare
          type="text"
          placeholder="Hledat nabídku…"
          testid="quote-search-input"
          class="toolbar-search"
        />
        <span class="toolbar-count">{{ filtered.length }} / {{ items.length }}</span>
        <button
          class="icon-btn"
          title="Nová nabídka"
          data-testid="quote-new-btn"
          @click="emit('new-quote')"
        >
          <PlusIcon :size="ICON_SIZE_SM" />
        </button>
        <button
          class="icon-btn icon-btn-ai"
          title="Import z PDF"
          data-testid="quote-ai-btn"
          @click="onAiClick"
        >
          <BotIcon :size="ICON_SIZE_SM" />
        </button>
      </div>

      <!-- Status filter tabs -->
      <div class="tab-bar">
        <button
          v-for="s in (['all', 'draft', 'sent', 'approved', 'rejected'] as const)"
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
        <span class="mod-label">{{ searchQuery ? 'Žádné výsledky' : 'Žádné nabídky' }}</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:82px">Číslo</th>
              <th>Název</th>
              <th style="width:88px">Status</th>
              <th style="width:88px">Termín</th>
              <th class="col-currency" style="width:96px">Celkem</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="q in filtered"
              :key="q.id"
              :class="{ selected: q.quote_number === selectedQuoteNumber }"
              :data-testid="`quote-row-${q.id}`"
              @click="onRowClick(q)"
            >
              <td class="t4">{{ q.quote_number }}</td>
              <td class="title-cell">{{ q.title || '—' }}</td>
              <td>
                <span class="badge">
                  <span :class="['badge-dot', statusDotClass(q.status)]" />
                  {{ STATUS_LABELS[q.status] }}
                </span>
              </td>
              <td class="t4">{{ formatDate(q.offer_deadline) }}</td>
              <td class="col-currency">{{ formatCurrency(q.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wquo-list {
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
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Toolbar ─── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.toolbar-search { flex: 1; }
.toolbar-count {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
  padding: 0 2px;
}
.icon-btn-ai { color: var(--t3); }
.icon-btn-ai:hover { color: var(--t1); }

/* ─── Status filter tabs ─── */
.tab-bar {
  display: flex;
  gap: 1px;
  padding: 4px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  overflow-x: auto;
}
.ptab {
  padding: 3px 7px;
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  font-family: var(--font);
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
.tab-count { font-size: var(--fss); color: var(--t4); }
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
tr.selected { background: var(--b1); }
tr { cursor: pointer; }
</style>
