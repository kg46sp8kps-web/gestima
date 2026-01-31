<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartnersStore } from '@/stores/partners'
import type { Quote, QuoteStatus, QuoteCreate } from '@/types/quote'
import { Plus, ClipboardList, FileEdit, Send, CheckCircle, XCircle } from 'lucide-vue-next'
import type { Component } from 'vue'

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
const partnersStore = usePartnersStore()
const searchQuery = ref('')
const activeTab = ref<QuoteStatus | 'all'>('all')
const showCreateForm = ref(false)

const newQuote = reactive<QuoteCreate>({
  title: '',
  description: '',
  partner_id: null,
  valid_until: null,
  discount_percent: 0,
  tax_percent: 21
})

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
  newQuote.title = ''
  newQuote.description = ''
  newQuote.partner_id = null
  newQuote.valid_until = null
  newQuote.discount_percent = 0
  newQuote.tax_percent = 21
  showCreateForm.value = true
}

async function createQuote() {
  try {
    const quote = await quotesStore.createQuote({
      title: newQuote.title,
      description: newQuote.description || undefined,
      partner_id: newQuote.partner_id,
      valid_until: newQuote.valid_until,
      discount_percent: newQuote.discount_percent,
      tax_percent: newQuote.tax_percent
    })
    showCreateForm.value = false
    // Auto-select newly created quote
    selectQuote(quote)
  } catch (error) {
    // Error handled in store
  }
}

// Load partners for dropdown
partnersStore.fetchPartners()

function setTab(tab: QuoteStatus | 'all') {
  activeTab.value = tab
}

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

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK',
    minimumFractionDigits: 2
  }).format(value)
}
</script>

<template>
  <div class="quote-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Nabídky</h3>
      <button @click="handleCreate" class="btn-create">
        <Plus :size="14" :stroke-width="2" />
        Nová
      </button>
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
        <ClipboardList :size="48" :stroke-width="1.5" />
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
            <component :is="getStatusBadge(quote.status).icon" :size="14" :stroke-width="2" />
          </span>
        </div>
        <span class="quote-title">{{ quote.title }}</span>
        <div class="quote-meta">
          <span class="quote-total">{{ formatCurrency(quote.total) }}</span>
        </div>
      </div>
    </div>

    <!-- Create Quote Modal -->
    <Teleport to="body">
      <div v-if="showCreateForm" class="modal-overlay" @click.self="showCreateForm = false">
        <div class="modal-content">
          <h3>Nová nabídka</h3>
          <form @submit.prevent="createQuote" class="create-form">
            <div class="form-group">
              <label>Název <span class="required">*</span></label>
              <input
                v-model="newQuote.title"
                type="text"
                class="form-input"
                required
                maxlength="200"
                placeholder="Název nabídky"
              />
            </div>

            <div class="form-group">
              <label>Popis</label>
              <textarea
                v-model="newQuote.description"
                class="form-textarea"
                rows="3"
                maxlength="1000"
                placeholder="Popis nabídky"
              ></textarea>
            </div>

            <div class="form-group">
              <label>Partner</label>
              <select
                v-model="newQuote.partner_id"
                class="form-input"
              >
                <option :value="null">-- Bez partnera --</option>
                <option
                  v-for="partner in partnersStore.customers"
                  :key="partner.id"
                  :value="partner.id"
                >
                  {{ partner.company_name }} ({{ partner.partner_number }})
                </option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Platnost do</label>
                <input
                  v-model="newQuote.valid_until"
                  type="date"
                  class="form-input"
                />
              </div>
              <div class="form-group">
                <label>Sleva (%)</label>
                <input
                  v-model.number="newQuote.discount_percent"
                  type="number"
                  class="form-input"
                  min="0"
                  max="100"
                  step="0.01"
                  v-select-on-focus
                />
              </div>
              <div class="form-group">
                <label>DPH (%)</label>
                <input
                  v-model.number="newQuote.tax_percent"
                  type="number"
                  class="form-input"
                  min="0"
                  max="100"
                  step="0.01"
                  v-select-on-focus
                />
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showCreateForm = false">
                Zrušit
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="isLoading || !newQuote.title"
              >
                {{ isLoading ? 'Vytvářím...' : 'Vytvořit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.quote-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.list-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-create {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--palette-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-create:hover {
  background: var(--palette-primary-hover);
}

.filter-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-default);
  overflow-x: auto;
  scrollbar-width: thin;
}

.tab-button {
  flex: 1;
  padding: var(--space-2);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
}

.tab-button:hover {
  color: var(--text-body);
  background: var(--state-hover);
}

.tab-button.active {
  color: var(--palette-primary);
  border-bottom-color: var(--palette-primary);
}

.search-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.search-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.loading-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--palette-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-list .empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.empty-list p {
  font-size: var(--text-sm);
}

.quotes-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.quote-item {
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  background: var(--bg-surface);
}

.quote-item:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.quote-item.active {
  background: var(--state-selected);
  border-color: var(--palette-primary);
}

.quote-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.quote-number {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--palette-primary);
}

.status-badge {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-badge.status-gray {
  color: var(--text-secondary);
}

.status-badge.status-blue {
  color: var(--color-info);
}

.status-badge.status-green {
  color: var(--color-success);
}

.status-badge.status-red {
  color: var(--color-danger);
}

.quote-title {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-body);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quote-meta {
  display: flex;
  justify-content: flex-end;
}

.quote-total {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  max-width: 600px;
  width: 90%;
  border: 1px solid var(--border-default);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-group label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.required {
  color: var(--palette-danger);
}

.form-input,
.form-textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-body);
  font-family: inherit;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.btn-primary,
.btn-secondary {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary {
  background: var(--palette-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--palette-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}
</style>
