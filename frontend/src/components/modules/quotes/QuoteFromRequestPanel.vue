<script setup lang="ts">
/**
 * QuoteFromRequestPanel - Coordinator (<290 LOC)
 */

import { computed, reactive } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { useWindowsStore } from '@/stores/windows'
import { Check, ArrowLeft } from 'lucide-vue-next'
import QuoteFileUploadSection from './QuoteFileUploadSection.vue'
import QuoteSummarySection from './QuoteSummarySection.vue'
import QuoteCustomerSection from './QuoteCustomerSection.vue'
import QuoteItemsSection from './QuoteItemsSection.vue'
import QuoteMetadataSection from './QuoteMetadataSection.vue'
import type { QuoteFromRequestCreate } from '@/types/quote'
import { ICON_SIZE } from '@/config/design'

const quotesStore = useQuotesStore()
const windowsStore = useWindowsStore()

const review = computed(() => quotesStore.aiReview)

const formData = reactive({
  customer: { company_name: '', ico: '', contact_person: '', email: '', phone: '' },
  title: '',
  customer_request_number: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: '',
  editableItems: [] as Array<{
    article_number: string
    drawing_number: string | null
    name: string
    quantity: number
    notes: string | null
    part_id: number | null
    part_exists: boolean
    batch_match: {
      batch_id: number | null
      batch_quantity: number | null
      status: 'exact' | 'lower' | 'missing'
      unit_price: number
      line_total: number
      warnings: string[]
    } | null
    stepFile: File | null
    pdfFile: File | null
  }>
})

const isFormValid = computed(() => {
  return formData.title.trim() !== '' && formData.customer.company_name.trim() !== ''
})

async function uploadPDF(file: File) {
  const result = await quotesStore.parseQuoteRequestPDF(file)

  formData.customer.company_name = result.customer.company_name
  formData.customer.ico = result.customer.ico || ''
  formData.customer.contact_person = result.customer.contact_person || ''
  formData.customer.email = result.customer.email || ''
  formData.customer.phone = result.customer.phone || ''
  formData.customer_request_number = result.customer_request_number || ''
  formData.valid_until = result.valid_until || ''
  formData.notes = result.notes || ''

  const today = new Date().toLocaleDateString('cs-CZ')
  formData.title = `Poptávka ${result.customer.company_name} - ${today}`

  formData.editableItems = result.items.map(item => ({
    article_number: item.article_number,
    drawing_number: item.drawing_number,
    name: item.name,
    quantity: item.quantity,
    notes: item.notes,
    part_id: item.part_id,
    part_exists: item.part_exists,
    batch_match: item.batch_match,
    stepFile: null,
    pdfFile: null
  }))
}

function handleBack() {
  quotesStore.clearAiReview()
}

function handleItemFileAdd(index: number, file: File, fileType: 'step' | 'pdf') {
  const item = formData.editableItems[index]
  if (!item) return

  if (fileType === 'step') {
    item.stepFile = file
  } else {
    item.pdfFile = file
  }
}

function handleItemFileRemove(index: number, fileType: 'step' | 'pdf') {
  const item = formData.editableItems[index]
  if (!item) return

  if (fileType === 'step') {
    item.stepFile = null
  } else {
    item.pdfFile = null
  }
}

async function handleConfirm() {
  const currentReview = review.value
  if (!currentReview || !isFormValid.value) return

  const data: QuoteFromRequestCreate = {
    title: formData.title,
    customer_request_number: formData.customer_request_number || null,
    valid_until: formData.valid_until || null,
    notes: formData.notes || null,
    discount_percent: formData.discount_percent,
    tax_percent: formData.tax_percent,
    items: formData.editableItems.map((item) => ({
      part_id: item.part_exists ? item.part_id : null,
      article_number: item.article_number,
      drawing_number: item.drawing_number,
      name: item.name,
      quantity: item.quantity,
      notes: item.notes
    }))
  }

  if (currentReview.customer.partner_exists) {
    data.partner_id = currentReview.customer.partner_id
  } else {
    data.partner_data = {
      company_name: formData.customer.company_name,
      contact_person: formData.customer.contact_person || null,
      email: formData.customer.email || null,
      phone: formData.customer.phone || null,
      ico: formData.customer.ico || null,
      dic: null,
      is_customer: true,
      is_supplier: false
    }
  }

  await quotesStore.createQuoteFromParsedRequest(data)
  windowsStore.closeWindow('quote-from-request')
}
</script>

<template>
  <div class="panel">
    <div v-if="quotesStore.aiParsing" class="loading">
      <div class="spinner"></div>
      <p>AI analyzuje PDF...</p>
      <p class="hint">Trvá cca 10-30 sekund podle velikosti PDF</p>
    </div>

    <QuoteFileUploadSection v-if="!review && !quotesStore.aiParsing" @upload="uploadPDF" />

    <div v-if="review && !quotesStore.loading" class="review">
      <QuoteSummarySection :summary="review.summary" />

      <QuoteCustomerSection
        :customer="formData.customer"
        :review-customer="review.customer"
        @update:customer="formData.customer = $event"
      />

      <QuoteItemsSection
        :items="formData.editableItems"
        @file-add="handleItemFileAdd"
        @file-remove="handleItemFileRemove"
      />

      <QuoteMetadataSection
        :metadata="{
          title: formData.title,
          customer_request_number: formData.customer_request_number,
          valid_until: formData.valid_until,
          discount_percent: formData.discount_percent,
          tax_percent: formData.tax_percent,
          notes: formData.notes
        }"
        @update:metadata="Object.assign(formData, $event)"
      />

      <div class="actions">
        <button class="action-button" @click="handleBack">
          <ArrowLeft :size="ICON_SIZE.SMALL" />
          Nahrát jiné PDF
        </button>
        <button class="action-button action-primary" :disabled="!isFormValid || quotesStore.loading" @click="handleConfirm">
          <Check :size="ICON_SIZE.SMALL" />
          Vytvořit nabídku
        </button>
      </div>
    </div>

    <div v-if="quotesStore.loading" class="loading">
      <div class="spinner"></div>
      <p>Vytvářím nabídku...</p>
    </div>
  </div>
</template>

<style scoped>
.panel {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-4);
  background: var(--bg-base);
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: var(--space-8);
  gap: var(--space-3);
  color: var(--text-body);
}

.loading p {
  margin: 0;
  font-size: var(--text-base);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--palette-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.review {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 1200px;
  margin: 0 auto;
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-4);
}

.action-button {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-raised);
  color: var(--text-body);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.15s;
}

.action-button:hover {
  background: var(--state-hover);
}

.action-primary {
  background: var(--palette-primary);
  color: white;
  border-color: var(--palette-primary);
}

.action-primary:hover {
  background: var(--palette-primary-hover);
}

.action-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
