<script setup lang="ts">
/**
 * Quote Header Component
 * Displays quote info summary, totals, and workflow buttons
 */
import { computed } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import type { QuoteWithItems, QuoteStatus } from '@/types/quote'
import { Edit, FileText, Send, CheckCircle, XCircle, Copy, Trash2 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm } from '@/composables/useDialog'
import { formatCurrency } from '@/utils/formatters'

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

  const confirmed = await confirm({
    title: 'Smazat nabídku?',
    message: `Opravdu chcete smazat nabídku ${props.quote.quote_number}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesStore.deleteQuote(props.quote.quote_number)
    emit('deleted')
  } catch (error) {
    // Error handled in store
  }
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
            <component :is="statusBadge.icon" :size="ICON_SIZE.STANDARD" />
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
          title="Odeslat"
        >
          <Send :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          v-if="showApproveButton"
          @click="handleApprove"
          class="btn-workflow btn-approve"
          :disabled="quotesStore.loading"
          title="Schválit"
        >
          <CheckCircle :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          v-if="showRejectButton"
          @click="handleReject"
          class="btn-workflow btn-reject"
          :disabled="quotesStore.loading"
          title="Odmítnout"
        >
          <XCircle :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          v-if="showCloneButton"
          @click="handleClone"
          class="btn-workflow btn-clone"
          :disabled="quotesStore.loading"
          title="Duplikovat"
        >
          <Copy :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          v-if="showDeleteButton"
          @click="handleDelete"
          class="btn-workflow btn-delete"
          :disabled="quotesStore.loading"
          title="Smazat"
        >
          <Trash2 :size="ICON_SIZE.STANDARD" />
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
  display: flex; flex-direction: column; gap: 12px;
  padding: 16px; border-bottom: 2px solid var(--b2);
  background: var(--surface); flex-shrink: 0;
}
.quote-info { display: flex; flex-direction: column; gap: var(--pad); }
.quote-main { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--pad); flex-wrap: wrap; }
.quote-main h2 { margin: 0; font-size: 16px; font-weight: 700; color: var(--t1); flex: 1; }
.quote-badges { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.quote-number-badge {
  padding: 6px var(--pad); background: transparent;
  color: var(--t1); border: 1px solid var(--b2);
  border-radius: var(--r); font-size: var(--fs); font-weight: 600;
}

/* Status badges — single base + CSS custom properties per variant */
.status-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px var(--pad); border-radius: var(--r);
  font-size: var(--fs); font-weight: 600;
  background: var(--_badge-bg); color: white;
}
.status-draft    { --_badge-bg: var(--surface); }
.status-sent     { --_badge-bg: var(--t3); }
.status-approved { --_badge-bg: var(--ok); }
.status-rejected { --_badge-bg: var(--err); }

.partner-info {
  display: flex; align-items: center; gap: 6px;
  padding: var(--pad); background: var(--raised);
  border-radius: 8px; border: 1px solid var(--b2);
}
.partner-label  { font-size: var(--fs); color: var(--t3); font-weight: 500; }
.partner-name   { font-size: var(--fs); color: var(--t1); font-weight: 600; }
.partner-number { font-size: var(--fs); color: var(--t3); }

.totals-summary {
  display: flex; flex-direction: column; gap: 6px;
  padding: 12px; background: var(--raised);
  border-radius: 8px; border: 2px solid var(--b2);
}
.total-item { display: flex; justify-content: space-between; align-items: center; }
.total-label { font-size: var(--fs); color: var(--t3); }
.total-value { font-size: var(--fs); color: var(--t1); font-weight: 600; }
.total-value.discount { color: var(--ok); }
.total-item.total-main { padding-top: 6px; border-top: 1px solid var(--b2); margin-top: 4px; }
.total-item.total-main .total-label,
.total-item.total-main .total-value { font-size: var(--fs); font-weight: 600; }

.workflow-buttons {
  display: flex; gap: var(--pad); align-items: center; justify-content: flex-end;
  padding-top: 6px; border-top: 1px solid var(--b2);
}

/* Workflow buttons — single base + CSS custom properties per variant */
.btn-workflow {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; padding: 0; background: transparent; border: none;
  border-radius: var(--rs); cursor: pointer; transition: all 100ms;
  color: var(--_wf-color, var(--t3));
}
.btn-workflow:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-workflow:hover:not(:disabled) { color: var(--_wf-hover, var(--_wf-color, var(--t3))); transform: scale(1.15); }
.btn-send    { --_wf-color: var(--t3);    --_wf-hover: var(--t3); }
.btn-approve { --_wf-color: var(--ok); --_wf-hover: var(--ok); }
.btn-reject  { --_wf-color: var(--err);  --_wf-hover: var(--err); }
.btn-clone   { --_wf-hover: var(--red); }
.btn-delete  { --_wf-hover: var(--err); }

.empty-text  { font-size: var(--fs); color: var(--t3); }
</style>
