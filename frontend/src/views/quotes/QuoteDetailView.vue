<script setup lang="ts">
/**
 * Quote Detail View
 * Zobrazení a editace nabídky s položkami
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuotesStore } from '@/stores/quotes'
import { useUiStore } from '@/stores/ui'
import FormTabs from '@/components/ui/FormTabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import type { QuoteUpdate, QuoteItemCreate, QuoteItemUpdate, QuoteItem } from '@/types/quote'
import { FileText, Package, Camera, Send, CheckCircle, XCircle, Copy, Trash2, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm } from '@/composables/useDialog'

const route = useRoute()
const router = useRouter()
const quotesStore = useQuotesStore()
const uiStore = useUiStore()

// Tab state
const activeTab = ref(0)

const tabs = [
  { label: 'Základní info', icon: 'FileText' },
  { label: 'Položky', icon: 'Package' },
  { label: 'Snapshot', icon: 'Camera' }
]

// Form state (Tab 0 - Základní info)
const form = ref({
  partner_id: null as number | null,
  title: '',
  description: '',
  valid_until: null as string | null,
  discount_percent: 0,
  tax_percent: 21,
  version: 0
})

// Add item form state (Tab 1)
const addItemForm = ref({
  part_id: null as number | null,
  quantity: 1,
  unit_price: 0,
  notes: ''
})

const showAddItemForm = ref(false)
const saving = ref(false)

// Computed
const quote = computed(() => quotesStore.currentQuote)
const isLoading = computed(() => quotesStore.loading)
const isDraft = computed(() => quote.value?.status === 'draft')
const canEdit = computed(() => isDraft.value)

const items = computed(() => quote.value?.items || [])

// DataTable columns for quote items
const itemColumns = [
  { key: 'seq', label: '#', width: '60px' },
  { key: 'part_number', label: 'Číslo dílu', width: '150px' },
  { key: 'part_name', label: 'Název dílu' },
  { key: 'quantity', label: 'Množství', width: '100px', format: 'number' as const },
  { key: 'unit_price', label: 'Jedn. cena', width: '120px', format: 'currency' as const },
  { key: 'line_total', label: 'Celkem', width: '120px', format: 'currency' as const }
]

// Methods
async function loadQuote() {
  const quoteNumber = route.params.quoteNumber as string
  if (!quoteNumber) {
    uiStore.showError('Quote number missing')
    router.push({ name: 'quotes-list' })
    return
  }

  try {
    await quotesStore.fetchQuote(quoteNumber)

    // Populate form with quote data
    if (quote.value) {
      form.value = {
        partner_id: quote.value.partner_id,
        title: quote.value.title,
        description: quote.value.description,
        valid_until: quote.value.valid_until,
        discount_percent: quote.value.discount_percent,
        tax_percent: quote.value.tax_percent,
        version: quote.value.version
      }
    }
  } catch (error) {
    router.push({ name: 'quotes-list' })
  }
}

async function handleSave() {
  if (!quote.value || !canEdit.value) {
    uiStore.showError('Nelze editovat odeslanou nabídku')
    return
  }

  saving.value = true
  try {
    const updateData: QuoteUpdate = {
      ...form.value,
      version: quote.value.version
    }
    await quotesStore.updateQuote(quote.value.quote_number, updateData)
    await loadQuote() // Reload to get updated version
  } catch (error) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

async function handleSend() {
  if (!quote.value) return

  const confirmed = await confirm({
    title: 'Odeslat nabídku?',
    message: `Opravdu chcete odeslat nabídku "${quote.value.title}"?`,
    type: 'warning',
    confirmText: 'Odeslat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.sendQuote(quote.value.quote_number)
    await loadQuote()
  } catch (error) {
    // Error handled by store
  }
}

async function handleApprove() {
  if (!quote.value) return

  const confirmed = await confirm({
    title: 'Schválit nabídku?',
    message: `Opravdu chcete schválit nabídku "${quote.value.title}"?`,
    type: 'info',
    confirmText: 'Schválit',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.approveQuote(quote.value.quote_number)
    await loadQuote()
  } catch (error) {
    // Error handled by store
  }
}

async function handleReject() {
  if (!quote.value) return

  const confirmed = await confirm({
    title: 'Odmítnout nabídku?',
    message: `Opravdu chcete odmítnout nabídku "${quote.value.title}"?`,
    type: 'warning',
    confirmText: 'Odmítnout',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.rejectQuote(quote.value.quote_number)
    await loadQuote()
  } catch (error) {
    // Error handled by store
  }
}

async function handleClone() {
  if (!quote.value) return

  try {
    const newQuote = await quotesStore.cloneQuote(quote.value.quote_number)
    router.push({
      name: 'quote-detail',
      params: { quoteNumber: newQuote.quote_number }
    })
  } catch (error) {
    // Error handled by store
  }
}

// Quote Items actions
function handleAddItemToggle() {
  showAddItemForm.value = !showAddItemForm.value
  if (!showAddItemForm.value) {
    // Reset form
    addItemForm.value = {
      part_id: null,
      quantity: 1,
      unit_price: 0,
      notes: ''
    }
  }
}

async function handleAddItem() {
  if (!quote.value || !addItemForm.value.part_id) {
    uiStore.showError('Vyplňte díl')
    return
  }

  try {
    const createData: QuoteItemCreate = {
      part_id: addItemForm.value.part_id,
      quantity: addItemForm.value.quantity,
      notes: addItemForm.value.notes || undefined
    }
    await quotesStore.addQuoteItem(quote.value.quote_number, createData)
    handleAddItemToggle() // Close form
  } catch (error) {
    // Error handled by store
  }
}

async function handleDeleteItem(item: QuoteItem) {
  const confirmed = await confirm({
    title: 'Smazat položku?',
    message: `Opravdu chcete smazat položku "${item.part_name}"?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.deleteQuoteItem(item.id)
  } catch (error) {
    // Error handled by store
  }
}

function goBack() {
  router.push({ name: 'quotes-list' })
}

onMounted(() => {
  loadQuote()
})
</script>

<template>
  <div class="quote-detail-view">
    <!-- Loading state -->
    <div v-if="isLoading && !quote" class="loading-container">
      <p>Načítání nabídky...</p>
    </div>

    <!-- Quote loaded -->
    <div v-else-if="quote" class="detail-content">
      <!-- Page header -->
      <header class="page-header">
        <button class="btn-back" @click="goBack">← Zpět</button>
        <div class="header-content">
          <h1 class="page-title">{{ quote.quote_number }}: {{ quote.title }}</h1>
          <div class="header-meta">
            <span :class="['status-badge', `status-${quote.status}`]">
              {{ quote.status }}
            </span>
            <span v-if="quote.partner" class="partner-info">
              {{ quote.partner.company_name }}
            </span>
          </div>
        </div>
        <div class="header-actions">
          <!-- Workflow buttons -->
          <button
            v-if="isDraft"
            class="btn btn-primary"
            :disabled="isLoading"
            @click="handleSend"
          >
            <Send :size="ICON_SIZE.STANDARD" />
            Odeslat
          </button>
          <button
            v-if="quote.status === 'sent'"
            class="btn btn-success"
            :disabled="isLoading"
            @click="handleApprove"
          >
            <CheckCircle :size="ICON_SIZE.STANDARD" />
            Schválit
          </button>
          <button
            v-if="quote.status === 'sent'"
            class="btn btn-danger"
            :disabled="isLoading"
            @click="handleReject"
          >
            <XCircle :size="ICON_SIZE.STANDARD" />
            Odmítnout
          </button>
          <button class="btn" :disabled="isLoading" @click="handleClone">
            <Copy :size="ICON_SIZE.STANDARD" />
            Duplikovat
          </button>
        </div>
      </header>

      <!-- Totals summary -->
      <div class="totals-summary">
        <div class="total-item">
          <span class="total-label">Mezisoučet:</span>
          <span class="total-value">{{ quote.subtotal.toFixed(2) }} {{ quote.currency }}</span>
        </div>
        <div class="total-item">
          <span class="total-label">Sleva ({{ quote.discount_percent }}%):</span>
          <span class="total-value">-{{ quote.discount_amount.toFixed(2) }} {{ quote.currency }}</span>
        </div>
        <div class="total-item">
          <span class="total-label">DPH ({{ quote.tax_percent }}%):</span>
          <span class="total-value">{{ quote.tax_amount.toFixed(2) }} {{ quote.currency }}</span>
        </div>
        <div class="total-item total-final">
          <span class="total-label">Celkem:</span>
          <span class="total-value">{{ quote.total.toFixed(2) }} {{ quote.currency }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <FormTabs v-model="activeTab" :tabs="tabs">
        <!-- Tab 0: Základní info -->
        <template #tab-0>
          <div class="tab-content">
            <form class="edit-form" @submit.prevent="handleSave">
              <div class="form-card">
                <h2 class="card-title">Základní údaje</h2>

                <div class="form-group">
                  <label>Partner ID</label>
                  <input
                    v-model.number="form.partner_id"
                    type="number"
                    :disabled="!canEdit"
                    v-select-on-focus
                  />
                  <small>ID partnera (zákazníka)</small>
                </div>

                <div class="form-group">
                  <label>Název nabídky *</label>
                  <input
                    v-model="form.title"
                    required
                    maxlength="500"
                    :disabled="!canEdit"
                  />
                </div>

                <div class="form-group">
                  <label>Popis</label>
                  <textarea
                    v-model="form.description"
                    rows="4"
                    maxlength="2000"
                    :disabled="!canEdit"
                  ></textarea>
                </div>

                <div class="form-group">
                  <label>Platnost do</label>
                  <input
                    v-model="form.valid_until"
                    type="date"
                    :disabled="!canEdit"
                  />
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>Sleva (%)</label>
                    <input
                      v-model.number="form.discount_percent"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      :disabled="!canEdit"
                      v-select-on-focus
                    />
                  </div>

                  <div class="form-group">
                    <label>DPH (%)</label>
                    <input
                      v-model.number="form.tax_percent"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      :disabled="!canEdit"
                      v-select-on-focus
                    />
                  </div>
                </div>

                <div v-if="canEdit" class="form-actions">
                  <button type="submit" class="btn btn-primary" :disabled="saving">
                    {{ saving ? 'Ukládám...' : 'Uložit změny' }}
                  </button>
                </div>

                <div v-else class="edit-lock-warning">
                  <AlertTriangle :size="ICON_SIZE.STANDARD" />
                  Nelze editovat odeslanou nabídku
                </div>
              </div>
            </form>
          </div>
        </template>

        <!-- Tab 1: Položky -->
        <template #tab-1>
          <div class="tab-content">
            <div class="items-section">
              <div class="items-header">
                <h2>Položky nabídky</h2>
                <button
                  v-if="canEdit"
                  class="btn btn-primary"
                  @click="handleAddItemToggle"
                >
                  {{ showAddItemForm ? 'Zrušit' : '+ Přidat položku' }}
                </button>
              </div>

              <!-- Add item form -->
              <div v-if="showAddItemForm" class="add-item-form">
                <h3>Nová položka</h3>
                <div class="form-row">
                  <div class="form-group">
                    <label>ID dílu *</label>
                    <input
                      v-model.number="addItemForm.part_id"
                      type="number"
                      required
                      v-select-on-focus
                    />
                    <small>TODO: Autocomplete na díly</small>
                  </div>

                  <div class="form-group">
                    <label>Množství *</label>
                    <input
                      v-model.number="addItemForm.quantity"
                      type="number"
                      min="1"
                      required
                      v-select-on-focus
                    />
                  </div>

                  <div class="form-group">
                    <label>Jedn. cena</label>
                    <input
                      v-model.number="addItemForm.unit_price"
                      type="number"
                      step="0.01"
                      v-select-on-focus
                    />
                    <small>Volitelné - auto z frozen batch</small>
                  </div>
                </div>

                <div class="form-group">
                  <label>Poznámky</label>
                  <textarea v-model="addItemForm.notes" rows="2"></textarea>
                </div>

                <div class="form-actions">
                  <button
                    class="btn btn-primary"
                    :disabled="!addItemForm.part_id"
                    @click="handleAddItem"
                  >
                    Přidat
                  </button>
                  <button class="btn" @click="handleAddItemToggle">Zrušit</button>
                </div>
              </div>

              <!-- Items table -->
              <DataTable
                :data="items"
                :columns="itemColumns"
                :loading="isLoading"
                empty-text="Žádné položky"
                row-key="id"
              >
                <template #actions="{ row }">
                  <div class="row-actions">
                    <button
                      v-if="canEdit"
                      class="icon-btn icon-btn-danger"
                      title="Smazat"
                      @click.stop="handleDeleteItem(row as unknown as QuoteItem)"
                    >
                      <Trash2 :size="ICON_SIZE.STANDARD" />
                    </button>
                  </div>
                </template>
              </DataTable>
            </div>
          </div>
        </template>

        <!-- Tab 2: Snapshot -->
        <template #tab-2>
          <div class="tab-content">
            <div class="snapshot-section">
              <h2>Snapshot data</h2>
              <pre class="snapshot-json">{{ JSON.stringify(quote, null, 2) }}</pre>
            </div>
          </div>
        </template>
      </FormTabs>
    </div>
  </div>
</template>

<style scoped>
.quote-detail-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.detail-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.btn-back {
  padding: var(--spacing-sm) var(--spacing-md);
  background: none;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: var(--text-xl);
}

.btn-back:hover {
  background-color: var(--color-gray-50);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: var(--text-5xl);
  font-weight: 600;
}

.header-meta {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.header-actions {
  display: flex;
  gap: var(--spacing-sm);
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

/* Totals summary */
.totals-summary {
  display: flex;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  background-color: var(--color-gray-50);
  border-bottom: 1px solid var(--border-color);
}

.total-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.total-label {
  font-size: var(--text-xl);
  color: var(--color-gray-600);
}

.total-value {
  font-size: var(--text-3xl);
  font-weight: 600;
}

.total-final .total-value {
  font-size: var(--text-5xl);
  color: var(--color-primary);
}

/* Tab content */
.tab-content {
  padding: var(--spacing-lg);
  overflow-y: auto;
}

/* Form */
.edit-form {
  max-width: 800px;
}

.form-card {
  background-color: var(--color-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.card-title {
  margin: 0 0 var(--spacing-lg) 0;
  font-size: var(--text-4xl);
  font-weight: 600;
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
  font-size: var(--text-xl);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: var(--text-xl);
}

.form-group input:disabled,
.form-group textarea:disabled {
  background-color: var(--color-gray-100);
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: var(--text-base);
  color: var(--color-gray-600);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.form-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
}

.edit-lock-warning {
  padding: var(--spacing-md);
  background-color: var(--color-warning-100);
  color: var(--color-warning-700);
  border-radius: var(--border-radius);
  margin-top: var(--spacing-lg);
}

/* Items section */
.items-section {
  max-width: 1200px;
}

.items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.items-header h2 {
  margin: 0;
  font-size: var(--text-4xl);
  font-weight: 600;
}

.add-item-form {
  background-color: var(--color-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.add-item-form h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--text-2xl);
  font-weight: 600;
}

.row-actions {
  display: flex;
  gap: var(--spacing-xs);
}

/* Snapshot section */
.snapshot-section {
  max-width: 1200px;
}

.snapshot-section h2 {
  margin: 0 0 var(--spacing-lg) 0;
  font-size: var(--text-4xl);
  font-weight: 600;
}

.snapshot-json {
  background-color: var(--color-gray-50);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  font-size: var(--text-base);
  overflow-x: auto;
}
</style>
