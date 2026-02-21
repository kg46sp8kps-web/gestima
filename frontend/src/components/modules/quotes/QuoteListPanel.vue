<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { useWindowsStore } from '@/stores/windows'
import type { Quote, QuoteStatus } from '@/types/quote'
import { Plus, ClipboardList, FileEdit, Send, CheckCircle, XCircle, Sparkles } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { Component } from 'vue'
import { formatCurrency } from '@/utils/formatters'
import QuoteCreateModal from './QuoteCreateModal.vue'

interface Props {
  selectedQuote?: Quote | null
}

const props = withDefaults(defineProps<Props>(), {
  selectedQuote: null
})

const emit = defineEmits<{
  'select-quote': [quote: Quote]
  'create-new': []
}>()

const quotesStore = useQuotesStore()
const windowsStore = useWindowsStore()
const searchQuery = ref('')
const activeTab = ref<QuoteStatus | 'all'>('all')
const showCreateForm = ref(false)

const filteredQuotes = computed(() => {
  let list: Quote[] = []

  // Filter by tab
  switch (activeTab.value) {
    case 'draft':
      list = quotesStore.draftQuotes
      break
    case 'sent':
      list = quotesStore.sentQuotes
      break
    case 'approved':
      list = quotesStore.approvedQuotes
      break
    case 'rejected':
      list = quotesStore.rejectedQuotes
      break
    default:
      list = [...quotesStore.quotes]
  }

  // Sort by quote_number descending (newest first)
  list.sort((a, b) => b.quote_number.localeCompare(a.quote_number))

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(q =>
      q.quote_number.toLowerCase().includes(query) ||
      q.title.toLowerCase().includes(query) ||
      q.description?.toLowerCase().includes(query)
    )
  }

  return list
})

const isLoading = computed(() => quotesStore.loading)
const hasQuotes = computed(() => filteredQuotes.value.length > 0)

function selectQuote(quote: Quote) {
  emit('select-quote', quote)
}

function handleCreate() {
  showCreateForm.value = true
}

function handleCreateFromRequest() {
  windowsStore.openWindow('quote-from-request', 'Nová nabídka z PDF (AI)')
}

function setTab(tab: QuoteStatus | 'all') {
  activeTab.value = tab
}

onUnmounted(() => {
  searchQuery.value = ''
  activeTab.value = 'all'
})

function getStatusBadge(status: QuoteStatus): { icon: Component; label: string; color: string } {
  switch (status) {
    case 'draft':
      return { icon: FileEdit, label: 'Koncept', color: 'gray' }
    case 'sent':
      return { icon: Send, label: 'Odesláno', color: 'blue' }
    case 'approved':
      return { icon: CheckCircle, label: 'Schváleno', color: 'green' }
    case 'rejected':
      return { icon: XCircle, label: 'Odmítnuto', color: 'red' }
  }
}

</script>

<template>
  <div class="quote-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Nabídky</h3>
      <div class="icon-toolbar">
        <button @click="handleCreateFromRequest" class="icon-btn icon-btn-sm" title="Z poptávky (AI)">
          <Sparkles :size="ICON_SIZE.STANDARD" />
        </button>
        <button @click="handleCreate" class="icon-btn icon-btn-sm" title="Nová nabídka">
          <Plus :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        :class="{ active: activeTab === 'all' }"
        @click="setTab('all')"
        class="tab-button"
      >
        Všechny
      </button>
      <button
        :class="{ active: activeTab === 'draft' }"
        @click="setTab('draft')"
        class="tab-button"
      >
        Koncepty
      </button>
      <button
        :class="{ active: activeTab === 'sent' }"
        @click="setTab('sent')"
        class="tab-button"
      >
        Odeslané
      </button>
      <button
        :class="{ active: activeTab === 'approved' }"
        @click="setTab('approved')"
        class="tab-button"
      >
        Schválené
      </button>
      <button
        :class="{ active: activeTab === 'rejected' }"
        @click="setTab('rejected')"
        class="tab-button"
      >
        Odmítnuté
      </button>
    </div>

    <!-- Search Bar -->
    <input
      v-model="searchQuery"
      v-select-on-focus
      type="text"
      placeholder="Filtrovat nabídky..."
      class="search-input"
    />

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-list">
      <div class="spinner"></div>
      <p>Načítám nabídky...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasQuotes" class="empty-list">
      <div class="empty-icon">
        <ClipboardList :size="ICON_SIZE.HERO" :stroke-width="1.5" />
      </div>
      <p>Žádné nabídky</p>
    </div>

    <!-- Quotes List -->
    <div v-else class="quotes-list">
      <div
        v-for="quote in filteredQuotes"
        :key="quote.id"
        @click="selectQuote(quote)"
        :class="{ active: selectedQuote?.id === quote.id }"
        class="quote-item"
      >
        <div class="quote-header">
          <span class="quote-number">{{ quote.quote_number }}</span>
          <span
            class="status-badge"
            :class="`status-${getStatusBadge(quote.status).color}`"
          >
            <component :is="getStatusBadge(quote.status).icon" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
          </span>
        </div>
        <span class="quote-title">{{ quote.title }}</span>
        <div class="quote-meta">
          <span class="quote-total">{{ formatCurrency(quote.total) }}</span>
        </div>
      </div>
    </div>

    <QuoteCreateModal
      :show="showCreateForm"
      @close="showCreateForm = false"
      @created="(q) => { showCreateForm = false; selectQuote(q) }"
    />
  </div>
</template>

<style scoped>
.quote-list-panel { display: flex; flex-direction: column; gap: var(--space-3); height: 100%; overflow: hidden; }
.list-header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.list-header h3 { margin: 0; font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); }

.filter-tabs { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--border-default); overflow-x: auto; scrollbar-width: thin; }

.loading-list { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-8); color: var(--text-secondary); }

.quotes-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-1); }
.quote-item {
  padding: var(--space-2); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); cursor: pointer;
  transition: var(--transition-fast); background: var(--bg-surface);
}
.quote-item:hover { background: var(--state-hover); border-color: var(--border-strong); }
.quote-item.active { background: var(--state-selected); border-color: var(--palette-primary); }

.quote-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.quote-number { font-size: var(--text-xs); font-weight: var(--font-semibold); color: var(--palette-primary); }
.status-badge { display: flex; align-items: center; justify-content: center; color: var(--_badge-color, var(--text-secondary)); }
.status-gray { --_badge-color: var(--text-secondary); }
.status-blue { --_badge-color: var(--color-info); }
.status-green { --_badge-color: var(--color-success); }
.status-red { --_badge-color: var(--color-danger); }
.quote-title { display: block; font-size: var(--text-sm); color: var(--text-body); font-weight: var(--font-medium); margin-bottom: var(--space-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.quote-meta { display: flex; justify-content: flex-end; }
.quote-total { font-size: var(--text-xs); font-weight: var(--font-semibold); color: var(--text-secondary); }
</style>
