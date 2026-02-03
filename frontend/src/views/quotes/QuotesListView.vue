<template>
  <div class="quotes-view">
    <!-- Page header -->
    <header class="page-header">
      <h1>Nabídky</h1>
      <div class="header-actions">
        <button class="btn" @click="handleCreateFromRequest">
          <Sparkles :size="16" />
          Z poptávky (AI)
        </button>
        <button class="btn btn-primary" @click="handleCreate">+ Nová nabídka</button>
      </div>
    </header>

    <!-- Tabs: Koncepty | Odeslané | Schválené | Odmítnuté -->
    <FormTabs v-model="activeTab" :tabs="tabs">
      <!-- Tab 0: Koncepty (DRAFT) -->
      <template #tab-0>
        <div class="tab-content">
          <DataTable
            :data="draftQuotes"
            :columns="columns"
            :loading="quotesStore.loading"
            empty-text="Žádné koncepty nabídek"
            row-key="quote_number"
            @row-click="handleRowClick"
          >
            <!-- Status badge -->
            <template #cell-status="{ value }">
              <span :class="['status-badge', `status-${value}`]">
                {{ getStatusLabel(value as QuoteStatus) }}
              </span>
            </template>

            <!-- Partner (if exists) -->
            <template #cell-partner="{ row }">
              {{ row.partner_id ? `Partner #${row.partner_id}` : '-' }}
            </template>

            <!-- Custom actions column -->
            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon"
                  title="Upravit"
                  @click.stop="handleEdit(row as unknown as Quote)"
                >
                  <Edit :size="15" />
                </button>
                <button
                  class="btn-icon btn-primary"
                  title="Odeslat"
                  @click.stop="handleSend(row as unknown as Quote)"
                >
                  <Send :size="15" />
                </button>
                <button
                  class="btn-icon"
                  title="Duplikovat"
                  @click.stop="handleClone(row as unknown as Quote)"
                >
                  <Copy :size="15" />
                </button>
                <button
                  class="btn-icon btn-danger"
                  title="Smazat"
                  @click.stop="handleDelete(row as unknown as Quote)"
                >
                  <Trash2 :size="15" />
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>

      <!-- Tab 1: Odeslané (SENT) -->
      <template #tab-1>
        <div class="tab-content">
          <DataTable
            :data="sentQuotes"
            :columns="columns"
            :loading="quotesStore.loading"
            empty-text="Žádné odeslané nabídky"
            row-key="quote_number"
            @row-click="handleRowClick"
          >
            <template #cell-status="{ value }">
              <span :class="['status-badge', `status-${value}`]">
                {{ getStatusLabel(value as QuoteStatus) }}
              </span>
            </template>

            <template #cell-partner="{ row }">
              {{ row.partner_id ? `Partner #${row.partner_id}` : '-' }}
            </template>

            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon btn-success"
                  title="Schválit"
                  @click.stop="handleApprove(row as unknown as Quote)"
                >
                  <CheckCircle :size="15" />
                </button>
                <button
                  class="btn-icon btn-danger"
                  title="Odmítnout"
                  @click.stop="handleReject(row as unknown as Quote)"
                >
                  <XCircle :size="15" />
                </button>
                <button
                  class="btn-icon"
                  title="Duplikovat"
                  @click.stop="handleClone(row as unknown as Quote)"
                >
                  <Copy :size="15" />
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>

      <!-- Tab 2: Schválené (APPROVED) -->
      <template #tab-2>
        <div class="tab-content">
          <DataTable
            :data="approvedQuotes"
            :columns="columns"
            :loading="quotesStore.loading"
            empty-text="Žádné schválené nabídky"
            row-key="quote_number"
            @row-click="handleRowClick"
          >
            <template #cell-status="{ value }">
              <span :class="['status-badge', `status-${value}`]">
                {{ getStatusLabel(value as QuoteStatus) }}
              </span>
            </template>

            <template #cell-partner="{ row }">
              {{ row.partner_id ? `Partner #${row.partner_id}` : '-' }}
            </template>

            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon"
                  title="Duplikovat"
                  @click.stop="handleClone(row as unknown as Quote)"
                >
                  <Copy :size="15" />
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>

      <!-- Tab 3: Odmítnuté (REJECTED) -->
      <template #tab-3>
        <div class="tab-content">
          <DataTable
            :data="rejectedQuotes"
            :columns="columns"
            :loading="quotesStore.loading"
            empty-text="Žádné odmítnuté nabídky"
            row-key="quote_number"
            @row-click="handleRowClick"
          >
            <template #cell-status="{ value }">
              <span :class="['status-badge', `status-${value}`]">
                {{ getStatusLabel(value as QuoteStatus) }}
              </span>
            </template>

            <template #cell-partner="{ row }">
              {{ row.partner_id ? `Partner #${row.partner_id}` : '-' }}
            </template>

            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon"
                  title="Duplikovat"
                  @click.stop="handleClone(row as unknown as Quote)"
                >
                  <Copy :size="15" />
                </button>
                <button
                  class="btn-icon btn-danger"
                  title="Smazat"
                  @click.stop="handleDelete(row as unknown as Quote)"
                >
                  <Trash2 :size="15" />
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>
    </FormTabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuotesStore } from '@/stores/quotes'
import FormTabs from '@/components/ui/FormTabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import type { Quote, QuoteStatus } from '@/types/quote'
import { FileEdit, Send, CheckCircle, XCircle, Edit, Copy, Trash2, Sparkles } from 'lucide-vue-next'
import { confirm } from '@/composables/useDialog'

const router = useRouter()
const quotesStore = useQuotesStore()

// Tab state
const activeTab = ref(0)

const tabs = [
  { label: 'Koncepty', icon: 'FileEdit' },
  { label: 'Odeslané', icon: 'Send' },
  { label: 'Schválené', icon: 'CheckCircle' },
  { label: 'Odmítnuté', icon: 'XCircle' }
]

// Computed data (filtered by status)
const draftQuotes = computed(() => quotesStore.draftQuotes)
const sentQuotes = computed(() => quotesStore.sentQuotes)
const approvedQuotes = computed(() => quotesStore.approvedQuotes)
const rejectedQuotes = computed(() => quotesStore.rejectedQuotes)

// DataTable columns
const columns = [
  { key: 'quote_number', label: 'Číslo', width: '120px', sortable: true },
  { key: 'partner', label: 'Partner', width: '150px' },
  { key: 'title', label: 'Název', sortable: true },
  { key: 'total', label: 'Celkem', width: '120px', format: 'currency' as const, sortable: true },
  { key: 'status', label: 'Stav', width: '120px' },
  { key: 'created_at', label: 'Vytvořeno', width: '150px', format: 'date' as const, sortable: true }
]

// Status label mapping
function getStatusLabel(status: QuoteStatus): string {
  const labels: Record<QuoteStatus, string> = {
    draft: 'Koncept',
    sent: 'Odesláno',
    approved: 'Schváleno',
    rejected: 'Odmítnuto'
  }
  return labels[status] || status
}

// Actions
function handleCreate() {
  // TODO: Open create modal or navigate to create view
  router.push({ name: 'quote-create' })
}

function handleCreateFromRequest() {
  router.push({ name: 'quote-new-from-request' })
}

function handleRowClick(row: Record<string, unknown>) {
  const quote = row as unknown as Quote
  router.push({
    name: 'quote-detail',
    params: { quoteNumber: quote.quote_number }
  })
}

function handleEdit(quote: Quote) {
  router.push({
    name: 'quote-detail',
    params: { quoteNumber: quote.quote_number }
  })
}

async function handleSend(quote: Quote) {
  const confirmed = await confirm({
    title: 'Odeslat nabídku?',
    message: `Opravdu chcete odeslat nabídku "${quote.title}"?`,
    type: 'warning',
    confirmText: 'Odeslat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.sendQuote(quote.quote_number)
    await quotesStore.fetchQuotes()
  } catch (error) {
    // Error handled by store
  }
}

async function handleApprove(quote: Quote) {
  const confirmed = await confirm({
    title: 'Schválit nabídku?',
    message: `Opravdu chcete schválit nabídku "${quote.title}"?`,
    type: 'info',
    confirmText: 'Schválit',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.approveQuote(quote.quote_number)
    await quotesStore.fetchQuotes()
  } catch (error) {
    // Error handled by store
  }
}

async function handleReject(quote: Quote) {
  const confirmed = await confirm({
    title: 'Odmítnout nabídku?',
    message: `Opravdu chcete odmítnout nabídku "${quote.title}"?`,
    type: 'warning',
    confirmText: 'Odmítnout',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.rejectQuote(quote.quote_number)
    await quotesStore.fetchQuotes()
  } catch (error) {
    // Error handled by store
  }
}

async function handleClone(quote: Quote) {
  try {
    const newQuote = await quotesStore.cloneQuote(quote.quote_number)
    router.push({
      name: 'quote-detail',
      params: { quoteNumber: newQuote.quote_number }
    })
  } catch (error) {
    // Error handled by store
  }
}

async function handleDelete(quote: Quote) {
  const confirmed = await confirm({
    title: 'Smazat nabídku?',
    message: `Opravdu chcete smazat nabídku "${quote.title}"?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.deleteQuote(quote.quote_number)
  } catch (error) {
    // Error handled by store
  }
}

// Lifecycle
onMounted(() => {
  quotesStore.fetchQuotes()
})
</script>

<style scoped>
.quotes-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.page-header h1 {
  margin: 0;
  font-size: var(--text-5xl);
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.tab-content {
  padding: var(--spacing-lg);
}

.row-actions {
  display: flex;
  gap: var(--spacing-xs);
}

/* Status badges */
.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--text-xl);
  font-weight: 500;
}

.status-draft {
  background-color: var(--color-gray-100);
  color: var(--color-gray-700);
}

.status-sent {
  background-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

.status-approved {
  background-color: var(--color-success-100);
  color: var(--color-success-700);
}

.status-rejected {
  background-color: var(--color-danger-100);
  color: var(--color-danger-700);
}
</style>
