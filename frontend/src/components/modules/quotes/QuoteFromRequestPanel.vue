<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { useWindowsStore } from '@/stores/windows'
import Input from '@/components/ui/Input.vue'
import {
  FileUp,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  XCircle,
  Info,
  BarChart3,
  User,
  Package,
  FileText,
  Check,
  ArrowLeft
} from 'lucide-vue-next'
import type { QuoteRequestReview, QuoteFromRequestCreate } from '@/types/quote'

// Stores
const quotesStore = useQuotesStore()
const windowsStore = useWindowsStore()

// State - use store review instead of local ref
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// Computed - get review from store
const review = computed(() => quotesStore.aiReview)

const formData = reactive({
  customer: {
    company_name: '',
    ico: '',
    contact_person: '',
    email: '',
    phone: ''
  },
  title: '',
  customer_request_number: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: '',
  editableItems: [] as Array<{
    article_number: string
    name: string
    quantity: number
    notes: string | null
    // References to original item
    part_id: number | null
    part_exists: boolean
    batch_match: any
  }>
})

// Computed
const isFormValid = computed(() => {
  return formData.title.trim() !== '' && formData.customer.company_name.trim() !== ''
})

// Methods
function triggerFileSelect() {
  fileInput.value?.click()
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) {
      await uploadPDF(file)
    }
  }
}

async function handleDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') {
      await uploadPDF(file)
    } else if (file) {
      alert('Pouze PDF soubory jsou podporovány')
    }
  }
}

async function uploadPDF(file: File) {
  // Validate file size (10 MB)
  if (file.size > 10 * 1024 * 1024) {
    alert('PDF je příliš velké. Maximum je 10 MB.')
    return
  }

  try {
    const result = await quotesStore.parseQuoteRequestPDF(file)
    // result is already stored in quotesStore.aiReview

    // Pre-fill form
    formData.customer.company_name = result.customer.company_name
    formData.customer.ico = result.customer.ico || ''
    formData.customer.contact_person = result.customer.contact_person || ''
    formData.customer.email = result.customer.email || ''
    formData.customer.phone = result.customer.phone || ''
    formData.customer_request_number = result.customer_request_number || ''
    formData.valid_until = result.valid_until || ''
    formData.notes = result.notes || ''

    // Auto-generate title
    const today = new Date().toLocaleDateString('cs-CZ')
    formData.title = `Poptávka ${result.customer.company_name} - ${today}`

    // Initialize editable items from AI result
    formData.editableItems = result.items.map(item => ({
      article_number: item.article_number,
      name: item.name,
      quantity: item.quantity,
      notes: item.notes,
      part_id: item.part_id,
      part_exists: item.part_exists,
      batch_match: item.batch_match
    }))
  } catch (error) {
    console.error('Upload failed:', error)
  }
}

function handleDragEnter() {
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleBack() {
  quotesStore.clearAiReview()
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
      name: item.name,
      quantity: item.quantity,
      notes: item.notes
    }))
  }

  // Partner
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

  try {
    const newQuote = await quotesStore.createQuoteFromParsedRequest(data)
    // Close this window
    windowsStore.closeWindow('quote-from-request')
    // Optionally open the detail window
    // windowsStore.openWindow('quote-detail', `Nabídka ${newQuote.quote_number}`, { quoteId: newQuote.id })
  } catch (error) {
    console.error('Failed to create quote:', error)
  }
}

function getBatchStatusIcon(status: string) {
  switch (status) {
    case 'exact':
      return CheckCircle2
    case 'lower':
      return AlertTriangle
    case 'missing':
      return XCircle
    default:
      return AlertCircle
  }
}

function getBatchStatusColor(status: string) {
  switch (status) {
    case 'exact':
      return 'success'
    case 'lower':
      return 'warning'
    case 'missing':
      return 'danger'
    default:
      return 'info'
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK'
  }).format(value)
}
</script>

<template>
  <div class="quote-from-request-panel">
    <!-- Loading State (during AI parsing) -->
    <div v-if="quotesStore.aiParsing" class="loading-section">
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Claude AI Sonnet 4.5 analyzuje PDF...</p>
        <p class="upload-hint">Trvá cca 10-30 sekund podle velikosti PDF</p>
      </div>
    </div>

    <!-- Step 1: Upload PDF -->
    <div v-if="!review && !quotesStore.aiParsing" class="upload-section">
      <div
        class="upload-dropzone"
        :class="{ dragging: isDragging }"
        @click="triggerFileSelect"
        @drop.prevent="handleDrop"
        @dragover.prevent
        @dragenter.prevent="handleDragEnter"
        @dragleave.prevent="handleDragLeave"
      >
        <FileUp :size="48" class="upload-icon" />
        <h2>Nahrajte PDF poptávky</h2>
        <p>Klikněte nebo přetáhněte PDF sem</p>
        <p class="upload-hint">Maximum 10 MB</p>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf"
        @change="handleFileSelect"
        style="display: none"
      />

      <!-- Info panel -->
      <div class="info-panel">
        <h3><Info :size="20" style="display: inline; margin-right: 8px;" /> Jak to funguje?</h3>
        <ul>
          <li>Nahraje se PDF s poptávkou (obsahuje zákazníka + díly + množství)</li>
          <li>Claude AI Sonnet 4.5 extrahuje: firma, IČO, kontakt, díly, počty kusů</li>
          <li>Systém hledá existující zákazníky a díly v databázi</li>
          <li>Automaticky přiřadí ceny z vhodných zamražených dávek</li>
          <li>Vy zkontrolujete, upravíte a potvrdíte → vytvoří se nabídka</li>
        </ul>
        <p class="info-note">
          <strong>Bezpečnost:</strong> AI pouze navrhuje, vy máte finální kontrolu. Ceny jsou
          konzervativní (raději vyšší než nižší).
        </p>
      </div>
    </div>

    <!-- Step 2: Review extracted data -->
    <div v-if="review && !quotesStore.loading" class="review-section">
      <!-- Summary stats -->
      <div class="summary-panel">
        <h2><BarChart3 :size="20" style="display: inline; margin-right: 8px;" /> Přehled poptávky</h2>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-label">Celkem položek:</span>
            <span class="summary-value">{{ review.summary.total_items }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Unikátní díly:</span>
            <span class="summary-value">{{ review.summary.unique_parts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Díly v DB:</span>
            <span class="summary-value success">{{ review.summary.matched_parts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Nové díly:</span>
            <span class="summary-value warning">{{ review.summary.new_parts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Chybějící kalkulace:</span>
            <span class="summary-value error">{{ review.summary.missing_batches }}</span>
          </div>
        </div>
      </div>

      <!-- Customer section -->
      <div class="customer-section">
        <h2><User :size="20" style="display: inline; margin-right: 8px;" /> Zákazník</h2>
        <div class="customer-info">
          <div class="form-row">
            <div class="form-field">
              <label>Firma</label>
              <Input v-model="formData.customer.company_name" placeholder="Název firmy" />
            </div>
            <div class="form-field">
              <label>IČO</label>
              <Input v-model="formData.customer.ico" placeholder="12345678" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-field">
              <label>Kontaktní osoba</label>
              <Input v-model="formData.customer.contact_person" placeholder="Jméno Příjmení" />
            </div>
            <div class="form-field">
              <label>Email</label>
              <Input v-model="formData.customer.email" type="email" placeholder="email@example.com" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-field">
              <label>Telefon</label>
              <Input v-model="formData.customer.phone" placeholder="+420 123 456 789" />
            </div>
          </div>

          <div v-if="review.customer.partner_exists" class="match-result success">
            <CheckCircle2 :size="16" />
            <span>Zákazník nalezen: {{ review.customer.partner_number }}</span>
          </div>
          <div v-else class="match-result warning">
            <AlertCircle :size="16" />
            <span>Zákazník bude vytvořen jako nový partner</span>
          </div>
        </div>
      </div>

      <!-- Items table -->
      <div class="items-section">
        <h2><Package :size="20" style="display: inline; margin-right: 8px;" /> Položky nabídky</h2>
        <div class="items-table-wrapper">
          <table class="items-table">
            <thead>
              <tr>
                <th>Artikl / Part Number</th>
                <th>Název</th>
                <th>Množství</th>
                <th>Dávka</th>
                <th>Cena/ks</th>
                <th>Celkem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in formData.editableItems" :key="idx" class="item-row">
                <td @click.stop>
                  <Input
                    v-model="item.article_number"
                    placeholder="Artikl / Part Number"
                    mono
                    class="table-input"
                  />
                  <span v-if="!item.part_exists" class="badge badge-new">Nový</span>
                </td>
                <td @click.stop>
                  <Input
                    v-model="item.name"
                    placeholder="Název dílu"
                    class="table-input"
                  />
                </td>
                <td class="text-right" @click.stop>
                  <div class="quantity-field">
                    <Input
                      v-model.number="item.quantity"
                      type="number"
                      mono
                      class="table-input quantity-input"
                    />
                    <span class="quantity-unit">ks</span>
                  </div>
                </td>
                <td>
                  <div v-if="item.batch_match" class="batch-status">
                    <component
                      :is="getBatchStatusIcon(item.batch_match.status)"
                      :size="16"
                      :class="`status-${getBatchStatusColor(item.batch_match.status)}`"
                    />
                    <span class="batch-text">
                      {{ item.batch_match.status === 'exact' ? 'Přesná' : '' }}
                      {{ item.batch_match.status === 'lower' ? 'Nižší' : '' }}
                      {{ item.batch_match.status === 'missing' ? 'Chybí' : '' }}
                      <span v-if="item.batch_match.batch_quantity">
                        ({{ item.batch_match.batch_quantity }} ks)
                      </span>
                    </span>
                  </div>
                  <div v-else class="batch-status">
                    <XCircle :size="16" class="status-danger" />
                    <span class="batch-text">Chybí</span>
                  </div>
                </td>
                <td class="text-right">
                  {{ item.batch_match ? formatCurrency(item.batch_match.unit_price) : '-' }}
                </td>
                <td class="text-right">
                  <strong>
                    {{ item.batch_match ? formatCurrency(item.batch_match.line_total) : '-' }}
                  </strong>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Batch legend -->
          <div class="batch-legend">
            <h4>Legenda dávek:</h4>
            <div class="legend-items">
              <span><CheckCircle2 :size="14" class="status-success" /> <strong>Exact:</strong> Přesně stejná dávka (best price)</span>
              <span><AlertTriangle :size="14" class="status-warning" /> <strong>Lower:</strong> Nejbližší nižší (konzervativní cena)</span>
              <span><XCircle :size="14" class="status-danger" /> <strong>Missing:</strong> Chybí kalkulace (nutno doplnit později)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quote metadata -->
      <div class="metadata-section">
        <h2><FileText :size="20" style="display: inline; margin-right: 8px;" /> Detaily nabídky</h2>
        <div class="form-row">
          <div class="form-field">
            <label>Název nabídky *</label>
            <Input v-model="formData.title" placeholder="Poptávka Q1/2026" />
          </div>
          <div class="form-field">
            <label>Číslo poptávky zákazníka</label>
            <Input v-model="formData.customer_request_number" placeholder="P20971, RFQ-2026-001..." />
          </div>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>Platnost do</label>
            <input
              v-model="formData.valid_until"
              type="date"
              class="form-input"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>Sleva (%)</label>
            <Input v-model.number="formData.discount_percent" type="number" step="0.01" />
          </div>
          <div class="form-field">
            <label>DPH (%)</label>
            <Input v-model.number="formData.tax_percent" type="number" step="0.01" />
          </div>
        </div>

        <div class="form-field">
          <label>Poznámky</label>
          <textarea
            v-model="formData.notes"
            class="form-textarea"
            rows="3"
            placeholder="Termín dodání, speciální podmínky..."
          ></textarea>
        </div>
      </div>

      <!-- Actions -->
      <div class="actions-section">
        <button class="btn" @click="handleBack">
          <ArrowLeft :size="16" />
          Nahrát jiné PDF
        </button>
        <button
          class="btn btn-primary"
          :disabled="!isFormValid || quotesStore.loading"
          @click="handleConfirm"
        >
          <Check :size="16" />
          Vytvořit nabídku
        </button>
      </div>
    </div>

    <!-- Loading state (creating quote) -->
    <div v-if="quotesStore.loading" class="creating-quote">
      <div class="spinner"></div>
      <p>Vytvářím nabídku...</p>
    </div>
  </div>
</template>

<style scoped>
.quote-from-request-panel {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-4);
  background: var(--bg-base);
}

/* Upload section */
.upload-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 800px;
  margin: 0 auto;
}

.upload-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12);
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  cursor: pointer;
  transition: all 0.2s;
}

.upload-dropzone:hover {
  border-color: var(--palette-primary);
  background: var(--state-hover);
}

.upload-dropzone.dragging {
  border-color: var(--palette-primary);
  background: var(--palette-primary-faint);
}

.upload-icon {
  color: var(--palette-primary);
}

.upload-dropzone h2 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.upload-dropzone p {
  margin: 0;
  color: var(--text-secondary);
}

.upload-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: var(--space-8);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-body);
}

.loading-state p {
  color: var(--text-body);
  font-size: var(--text-base);
  margin: 0;
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
  to {
    transform: rotate(360deg);
  }
}

.info-panel {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.info-panel h3 {
  margin: 0 0 var(--space-3) 0;
  color: var(--text-primary);
  font-size: var(--text-base);
}

.info-panel ul {
  margin: 0 0 var(--space-3) 0;
  padding-left: var(--space-5);
  color: var(--text-body);
}

.info-panel li {
  margin-bottom: var(--space-1);
}

.info-note {
  margin: 0;
  padding: var(--space-2);
  background: var(--palette-warning-faint);
  border-left: 3px solid var(--palette-warning);
  font-size: var(--text-sm);
  color: var(--text-body);
}

/* Review section */
.review-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 1200px;
  margin: 0 auto;
}

.summary-panel,
.customer-section,
.items-section,
.metadata-section {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.summary-panel h2,
.customer-section h2,
.items-section h2,
.metadata-section h2 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.summary-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.summary-value {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.summary-value.success {
  color: var(--color-success);
}

.summary-value.warning {
  color: var(--palette-warning);
}

.summary-value.error {
  color: var(--color-danger);
}

/* Customer section */
.customer-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-3);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-field label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--palette-neutral-300);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--space-3);
  background: var(--palette-neutral-800);
  border: 1px solid var(--palette-neutral-600);
  border-radius: var(--radius-sm);
  color: var(--palette-neutral-50);
  font-family: inherit;
  font-size: var(--font-size-base);
}

.form-textarea {
  resize: vertical;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--palette-neutral-400);
}

.match-result {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.match-result.success {
  background: var(--palette-success-faint);
  color: var(--color-success);
}

.match-result.warning {
  background: var(--palette-warning-faint);
  color: var(--palette-warning);
}

/* Items table */
.items-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.items-table {
  width: 100%;
  border-collapse: collapse;
}

.items-table th,
.items-table td {
  padding: var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.items-table th {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  background: var(--bg-raised);
}

.items-table td {
  font-size: var(--text-sm);
  color: var(--text-body);
  vertical-align: middle;
}

.item-row {
  transition: background var(--transition-fast);
}

.item-row:hover {
  background: var(--state-hover);
}

.text-right {
  text-align: right;
}

/* Inline editing fields */
.table-input {
  font-size: var(--text-sm);
}

.table-input :deep(.input) {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  min-height: 32px;
}

.quantity-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  justify-content: flex-end;
}

.quantity-input {
  max-width: 80px;
}

.quantity-input :deep(.input) {
  text-align: right;
}

.quantity-unit {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.article-number {
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
  color: var(--palette-primary);
}

.badge {
  display: inline-block;
  padding: 2px 6px;
  margin-left: var(--space-1);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.badge-new {
  background: var(--palette-warning-faint);
  color: var(--palette-warning);
}

.batch-status {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.batch-text {
  font-size: var(--text-sm);
}

.status-success {
  color: var(--color-success);
}

.status-warning {
  color: var(--palette-warning);
}

.status-danger {
  color: var(--color-danger);
}

.status-info {
  color: var(--color-info);
}

.batch-legend {
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
}

.batch-legend h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
}

.legend-items span {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* Actions */
.actions-section {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-4);
}

.btn {
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

.btn:hover {
  background: var(--state-hover);
}

.btn-primary {
  background: var(--palette-primary);
  color: white;
  border-color: var(--palette-primary);
}

.btn-primary:hover {
  background: var(--palette-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.creating-quote {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-8);
}
</style>
