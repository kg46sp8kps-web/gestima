<script setup lang="ts">
/**
 * Quote Header Component
 * Displays quote info summary, totals, and workflow buttons
 */
import { computed } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import type { QuoteWithItems, QuoteStatus } from '@/types/quote'
import { Edit, FileText, Send, CheckCircle, XCircle, Copy, Trash2 } from 'lucide-vue-next'

interface Props {
  quote: QuoteWithItems | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'updated': []
  'deleted': []
}>()

const quotesStore = useQuotesStore()

const statusBadge = computed(() => {
  if (!props.quote) return null

  switch (props.quote.status) {
    case 'draft':
      return { icon: Edit, label: 'Koncept', class: 'status-draft' }
    case 'sent':
      return { icon: Send, label: 'Odesláno', class: 'status-sent' }
    case 'approved':
      return { icon: CheckCircle, label: 'Schváleno', class: 'status-approved' }
    case 'rejected':
      return { icon: XCircle, label: 'Odmítnuto', class: 'status-rejected' }
  }
})

const showSendButton = computed(() => props.quote?.status === 'draft')
const showApproveButton = computed(() => props.quote?.status === 'sent')
const showRejectButton = computed(() => props.quote?.status === 'sent')
const showCloneButton = computed(() => props.quote !== null)
const showDeleteButton = computed(() =>
  props.quote?.status === 'draft' || props.quote?.status === 'rejected'
)

async function handleSend() {
  if (!props.quote) return
  try {
    await quotesStore.sendQuote(props.quote.quote_number)
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

async function handleApprove() {
  if (!props.quote) return
  try {
    await quotesStore.approveQuote(props.quote.quote_number)
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

async function handleReject() {
  if (!props.quote) return
  try {
    await quotesStore.rejectQuote(props.quote.quote_number)
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

async function handleClone() {
  if (!props.quote) return
  try {
    await quotesStore.cloneQuote(props.quote.quote_number)
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

async function handleDelete() {
  if (!props.quote) return
  if (!confirm(`Opravdu smazat nabídku ${props.quote.quote_number}?`)) return

  try {
    await quotesStore.deleteQuote(props.quote.quote_number)
    emit('deleted')
  } catch (error) {
    // Error handled in store
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
  <div class="quote-header">
    <!-- Quote Info -->
    <div v-if="quote" class="quote-info">
      <div class="quote-main">
        <h2>{{ quote.title }}</h2>
        <div class="quote-badges">
          <span class="quote-number-badge">{{ quote.quote_number }}</span>
          <span v-if="statusBadge" :class="['status-badge', statusBadge.class]">
            <component :is="statusBadge.icon" :size="14" />
            {{ statusBadge.label }}
          </span>
        </div>
      </div>

      <!-- Partner Info -->
      <div v-if="quote.partner" class="partner-info">
        <span class="partner-label">Partner:</span>
        <span class="partner-name">{{ quote.partner.company_name }}</span>
        <span class="partner-number">({{ quote.partner.partner_number }})</span>
      </div>

      <!-- Totals Summary -->
      <div class="totals-summary">
        <div class="total-item">
          <span class="total-label">Mezisoučet:</span>
          <span class="total-value">{{ formatCurrency(quote.subtotal) }}</span>
        </div>
        <div v-if="quote.discount_amount > 0" class="total-item">
          <span class="total-label">Sleva ({{ quote.discount_percent }}%):</span>
          <span class="total-value discount">-{{ formatCurrency(quote.discount_amount) }}</span>
        </div>
        <div class="total-item">
          <span class="total-label">DPH ({{ quote.tax_percent }}%):</span>
          <span class="total-value">{{ formatCurrency(quote.tax_amount) }}</span>
        </div>
        <div class="total-item total-main">
          <span class="total-label">CELKEM:</span>
          <span class="total-value">{{ formatCurrency(quote.total) }}</span>
        </div>
      </div>

      <!-- Workflow Buttons -->
      <div class="workflow-buttons">
        <button
          v-if="showSendButton"
          @click="handleSend"
          class="btn-workflow btn-send"
          :disabled="quotesStore.loading"
        >
          <Send :size="16" />
          Odeslat
        </button>
        <button
          v-if="showApproveButton"
          @click="handleApprove"
          class="btn-workflow btn-approve"
          :disabled="quotesStore.loading"
        >
          <CheckCircle :size="16" />
          Schválit
        </button>
        <button
          v-if="showRejectButton"
          @click="handleReject"
          class="btn-workflow btn-reject"
          :disabled="quotesStore.loading"
        >
          <XCircle :size="16" />
          Odmítnout
        </button>
        <button
          v-if="showCloneButton"
          @click="handleClone"
          class="btn-workflow btn-clone"
          :disabled="quotesStore.loading"
        >
          <Copy :size="16" />
          Duplikovat
        </button>
        <button
          v-if="showDeleteButton"
          @click="handleDelete"
          class="btn-workflow btn-delete"
          :disabled="quotesStore.loading"
        >
          <Trash2 :size="16" />
          Smazat
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <span class="empty-text">Vyberte nabídku ze seznamu</span>
    </div>
  </div>
</template>

<style scoped>
.quote-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
  border-bottom: 2px solid var(--border-color);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.quote-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.quote-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.quote-main h2 {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  flex: 1;
}

.quote-badges {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.quote-number-badge {
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.status-badge.status-draft {
  background: var(--bg-muted, #6b7280);
  color: white;
}

.status-badge.status-sent {
  background: var(--palette-info, #3b82f6);
  color: white;
}

.status-badge.status-approved {
  background: var(--palette-success, #10b981);
  color: white;
}

.status-badge.status-rejected {
  background: var(--palette-danger, #ef4444);
  color: white;
}

.partner-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.partner-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.partner-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.partner-number {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.totals-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-raised);
  border-radius: var(--radius-lg);
  border: 2px solid var(--border-color);
}

.total-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.total-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.total-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.total-value.discount {
  color: var(--palette-success, #10b981);
}

.total-item.total-main {
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-default);
  margin-top: var(--space-1);
}

.total-item.total-main .total-label,
.total-item.total-main .total-value {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.workflow-buttons {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.btn-workflow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--duration-normal);
}

.btn-workflow:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-send {
  background: var(--color-info);
  color: white;
}

.btn-send:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-approve {
  background: var(--color-success);
  color: white;
}

.btn-approve:hover:not(:disabled) {
  background: #047857;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-reject {
  background: var(--color-danger);
  color: white;
}

.btn-reject:hover:not(:disabled) {
  background: #dc2626;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-clone {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 2px solid var(--border-color);
}

.btn-clone:hover:not(:disabled) {
  border-color: var(--color-primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-delete {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-danger);
  border: 1px solid var(--color-danger);
}

.btn-delete:hover:not(:disabled) {
  background: var(--color-danger);
  color: white;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>
