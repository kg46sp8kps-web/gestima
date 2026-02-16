<template>
  <div class="quote-from-request-view">
    <!-- Page header -->
    <header class="page-header">
      <h1>Nová nabídka z poptávky (AI)</h1>
      <div class="header-actions">
        <button class="btn" @click="handleCancel">Zrušit</button>
      </div>
    </header>

    <!-- Step 1: Upload PDF -->
    <div v-if="!review" class="upload-section">
      <div
        class="upload-dropzone"
        :class="{ 'is-dragging': isDragging, 'is-uploading': quotesStore.aiParsing }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div v-if="!quotesStore.aiParsing" class="upload-content">
          <FileUp :size="ICON_SIZE.HERO" class="upload-icon" />
          <h2>Nahrajte PDF poptávky</h2>
          <p>Přetáhněte soubor sem nebo klikněte pro výběr</p>
          <p class="upload-hint">Max 10 MB | AI parsování: 10×/hod</p>
          <input
            ref="fileInput"
            type="file"
            accept="application/pdf"
            hidden
            @change="handleFileSelect"
          />
          <button class="btn btn-primary" @click="triggerFileSelect">Vybrat PDF</button>
        </div>

        <div v-else class="upload-loading">
          <div class="spinner"></div>
          <p>AI analyzuje PDF...</p>
          <p class="upload-hint">Trvá cca 10-30 sekund</p>
        </div>
      </div>

      <!-- Info panel -->
      <div class="info-panel">
        <h3><Info :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Jak to funguje?</h3>
        <ul>
          <li>Nahraje se PDF s poptávkou (obsahuje zákazníka + díly + množství)</li>
          <li>AI Vision extrahuje: firma, IČO, kontakt, díly, počty kusů</li>
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
        <h2><BarChart3 :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Přehled poptávky</h2>
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
            <span class="summary-label">Existující díly:</span>
            <span class="summary-value">{{ review.summary.matched_parts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Nové díly:</span>
            <span class="summary-value">{{ review.summary.new_parts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Chybějící kalkulace:</span>
            <span class="summary-value error">{{ review.summary.missing_batches }}</span>
          </div>
        </div>
      </div>

      <!-- Customer section -->
      <div class="customer-section">
        <h2><User :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Zákazník</h2>
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
              <label>Kontakt</label>
              <Input v-model="formData.customer.contact_person" placeholder="Jan Novák" />
            </div>
            <div class="form-field">
              <label>Email</label>
              <Input v-model="formData.customer.email" placeholder="jan@firma.cz" />
            </div>
            <div class="form-field">
              <label>Telefon</label>
              <Input v-model="formData.customer.phone" placeholder="+420 123 456 789" />
            </div>
          </div>

          <!-- Partner match result -->
          <div
            v-if="review.customer.partner_exists"
            class="match-result success"
          >
            <CheckCircle2 :size="ICON_SIZE.SMALL" />
            <span
              >Nalezen existující zákazník:
              <strong>{{ review.customer.partner_number }}</strong> (shoda:
              {{ Math.round(review.customer.match_confidence * 100) }}%)</span
            >
          </div>
          <div v-else class="match-result info">
            <AlertCircle :size="ICON_SIZE.SMALL" />
            <span>Zákazník bude vytvořen jako nový partner</span>
          </div>
        </div>
      </div>

      <!-- Items table -->
      <div class="items-section">
        <h2><Package :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Položky nabídky</h2>
        <div class="items-table-wrapper">
          <table class="items-table">
            <thead>
              <tr>
                <th>Číslo výkresu</th>
                <th>Název</th>
                <th>Množství</th>
                <th>Dávka</th>
                <th>Cena/ks</th>
                <th>Celkem</th>
                <th>Poznámka</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, index) in review.items"
                :key="index"
                :class="{ 'new-part': !item.part_exists }"
              >
                <td>
                  <strong>{{ item.article_number }}</strong>
                  <span v-if="!item.part_exists" class="badge badge-new">NOVÝ</span>
                </td>
                <td>{{ item.name }}</td>
                <td class="number">{{ item.quantity }} ks</td>
                <td>
                  <span
                    v-if="item.batch_match"
                    :class="['batch-badge', `batch-${item.batch_match.status}`]"
                  >
                    <CheckCircle2 v-if="item.batch_match.status === 'exact'" :size="ICON_SIZE.SMALL" />
                    <AlertTriangle v-else-if="item.batch_match.status === 'lower'" :size="ICON_SIZE.SMALL" />
                    <XCircle v-else :size="ICON_SIZE.SMALL" />
                    {{ item.batch_match.batch_quantity }} ks
                  </span>
                  <span v-else class="batch-badge batch-missing">
                    <XCircle :size="ICON_SIZE.SMALL" />
                    Chybí
                  </span>
                </td>
                <td class="number">
                  {{
                    item.batch_match
                      ? formatPrice(item.batch_match.unit_price)
                      : '-'
                  }}
                </td>
                <td class="number">
                  {{
                    item.batch_match
                      ? formatPrice(item.batch_match.line_total)
                      : '-'
                  }}
                </td>
                <td class="notes">
                  <div v-if="item.batch_match?.warnings.length" class="warnings">
                    <div
                      v-for="(warning, wIdx) in item.batch_match.warnings"
                      :key="wIdx"
                      class="warning"
                    >
                      {{ warning }}
                    </div>
                  </div>
                  <span v-if="item.notes" class="item-note">{{ item.notes }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Legend -->
        <div class="batch-legend">
          <h4>Legenda dávek:</h4>
          <div class="legend-items">
            <div class="legend-item">
              <CheckCircle2 :size="ICON_SIZE.SMALL" class="exact" />
              <span><strong>Exact:</strong> Přesná shoda (ideální)</span>
            </div>
            <div class="legend-item">
              <AlertTriangle :size="ICON_SIZE.SMALL" class="lower" />
              <span
                ><strong>Lower:</strong> Nižší dávka (vyšší cena/ks, bezpečnější odhad)</span
              >
            </div>
            <div class="legend-item">
              <XCircle :size="ICON_SIZE.SMALL" class="missing" />
              <span><strong>Missing:</strong> Chybí kalkulace (nutno doplnit později)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quote metadata -->
      <div class="metadata-section">
        <h2><FileText :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Detaily nabídky</h2>
        <div class="form-row">
          <div class="form-field">
            <label>Název nabídky *</label>
            <Input v-model="formData.title" placeholder="Poptávka Q1/2026" />
          </div>
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
          <ArrowLeft :size="ICON_SIZE.SMALL" />
          Nahrát jiné PDF
        </button>
        <button
          class="btn btn-primary"
          :disabled="!isFormValid || quotesStore.loading"
          @click="handleConfirm"
        >
          <Check :size="ICON_SIZE.SMALL" />
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuotesStore } from '@/stores/quotes'
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
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

// Stores
const quotesStore = useQuotesStore()
const router = useRouter()

// State
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const review = ref<QuoteRequestReview | null>(null)

// Form data (editable)
const formData = ref({
  customer: {
    company_name: '',
    contact_person: '',
    email: '',
    phone: '',
    ico: ''
  },
  title: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: ''
})

// Computed
const isFormValid = computed(() => {
  return formData.value.customer.company_name.trim() !== '' && formData.value.title.trim() !== ''
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
      await alert({
        title: 'Nepodporovaný formát',
        message: 'Pouze PDF soubory jsou podporovány',
        type: 'warning'
      })
    }
  }
}

async function uploadPDF(file: File) {
  // Validate file size (10 MB)
  if (file.size > 10 * 1024 * 1024) {
    await alert({
      title: 'Soubor je příliš velký',
      message: 'PDF je příliš velké. Maximum je 10 MB.',
      type: 'warning'
    })
    return
  }

  try {
    const result = await quotesStore.parseQuoteRequestPDF(file)
    review.value = result

    // Pre-fill form with extracted data
    formData.value.customer = {
      company_name: result.customer.company_name,
      contact_person: result.customer.contact_person || '',
      email: result.customer.email || '',
      phone: result.customer.phone || '',
      ico: result.customer.ico || ''
    }

    // Pre-fill quote title
    formData.value.title = `Poptávka ${result.customer.company_name}`

    // Pre-fill valid_until if extracted
    if (result.valid_until) {
      formData.value.valid_until = result.valid_until
    }

    // Pre-fill notes if extracted
    if (result.notes) {
      formData.value.notes = result.notes
    }
  } catch (error) {
    console.error('Failed to parse PDF:', error)
  }
}

function handleBack() {
  review.value = null
  quotesStore.clearAiReview()
}

async function handleConfirm() {
  if (!review.value) return

  // Build request payload
  const payload: QuoteFromRequestCreate = {
    // Customer (existing or new)
    partner_id: review.value.customer.partner_id,
    partner_data: review.value.customer.partner_exists
      ? undefined
      : {
          company_name: formData.value.customer.company_name,
          contact_person: formData.value.customer.contact_person || null,
          email: formData.value.customer.email || null,
          phone: formData.value.customer.phone || null,
          ico: formData.value.customer.ico || null,
          dic: null,
          is_customer: true,
          is_supplier: false
        },

    // Quote fields
    title: formData.value.title,
    valid_until: formData.value.valid_until || null,
    notes: formData.value.notes || null,
    discount_percent: formData.value.discount_percent,
    tax_percent: formData.value.tax_percent,

    // Items
    items: review.value.items.map((item) => ({
      part_id: item.part_id,
      article_number: item.article_number,
      name: item.name,
      quantity: item.quantity,
      notes: item.notes
    }))
  }

  try {
    const newQuote = await quotesStore.createQuoteFromParsedRequest(payload)
    // Navigate to quote detail
    router.push(`/quotes/${newQuote.quote_number}`)
  } catch (error) {
    console.error('Failed to create quote:', error)
  }
}

function handleCancel() {
  router.push('/quotes')
}

function formatPrice(value: number): string {
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK',
    minimumFractionDigits: 2
  }).format(value)
}

// Load review from store if user refreshes page
onMounted(() => {
  if (quotesStore.aiReview) {
    review.value = quotesStore.aiReview
  }
})
</script>

<style scoped>
.quote-from-request-view {
  padding: var(--space-6);
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.page-header h1 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: var(--space-2);
}

/* Upload section */
.upload-section {
  display: grid;
  gap: var(--space-6);
}

.upload-dropzone {
  border: 2px dashed var(--text-muted);
  border-radius: var(--radius-md);
  padding: var(--space-12);
  text-align: center;
  background: var(--bg-subtle);
  transition: all 0.2s;
  cursor: pointer;
}

.upload-dropzone:hover {
  border-color: var(--text-secondary);
  background: var(--border-default);
}

.upload-dropzone.is-dragging {
  border-color: var(--palette-accent-red);
  background: var(--border-default);
}

.upload-dropzone.is-uploading {
  pointer-events: none;
}

.upload-content,
.upload-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.upload-icon {
  color: var(--text-secondary);
}

.upload-content h2 {
  font-size: var(--text-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.upload-content p {
  color: var(--text-secondary);
}

.upload-hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--text-muted);
  border-top-color: var(--palette-accent-red);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.info-panel {
  background: var(--bg-subtle);
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-md);
  padding: var(--space-6);
}

.info-panel h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-4);
}

.info-panel ul {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-4) 0;
}

.info-panel li {
  color: var(--text-body);
  padding: var(--space-2) 0;
}

.info-note {
  display: block;
  padding: var(--space-3);
  background: var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-body);
  font-size: var(--text-sm);
}

/* Review section */
.review-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.summary-panel,
.customer-section,
.items-section,
.metadata-section {
  background: var(--bg-subtle);
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-md);
  padding: var(--space-6);
}

.summary-panel h2,
.customer-section h2,
.items-section h2,
.metadata-section h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-4);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--border-default);
  border-radius: var(--radius-sm);
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.summary-value.error {
  color: var(--palette-error-400);
}

/* Customer section */
.customer-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-4);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field label {
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-body);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--space-3);
  background: var(--border-default);
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: inherit;
  font-size: var(--text-base);
}

.form-textarea {
  resize: vertical;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--text-secondary);
}

.match-result {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.match-result.success {
  background: rgba(34, 197, 94, 0.1);
  color: var(--palette-success-300);
  border: 1px solid var(--palette-success-700);
}

.match-result.info {
  background: rgba(59, 130, 246, 0.1);
  color: var(--palette-info-300);
  border: 1px solid var(--palette-info-700);
}

/* Items table */
.items-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-sm);
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.items-table thead {
  background: var(--border-default);
}

.items-table th {
  padding: var(--space-3);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  color: var(--text-body);
  border-bottom: 1px solid var(--text-muted);
}

.items-table td {
  padding: var(--space-3);
  color: var(--text-body);
  border-bottom: 1px solid var(--border-default);
}

.items-table tbody tr:hover {
  background: var(--bg-raised);
}

.items-table tbody tr.new-part {
  background: rgba(59, 130, 246, 0.05);
}

.items-table .number {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.badge {
  display: inline-block;
  padding: var(--space-0\.5) var(--space-2);
  border-radius: var(--radius-xs);
  font-size: var(--text-2xs);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  margin-left: var(--space-2);
}

.badge-new {
  background: var(--palette-info-900);
  color: var(--palette-info-300);
  border: 1px solid var(--palette-info-700);
}

.batch-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
}

.batch-badge.batch-exact {
  background: rgba(34, 197, 94, 0.1);
  color: var(--palette-success-300);
  border: 1px solid var(--palette-success-700);
}

.batch-badge.batch-lower {
  background: rgba(251, 191, 36, 0.1);
  color: var(--palette-warning-300);
  border: 1px solid var(--palette-warning-700);
}

.batch-badge.batch-missing {
  background: rgba(239, 68, 68, 0.1);
  color: var(--palette-error-300);
  border: 1px solid var(--palette-error-700);
}

.notes {
  max-width: 300px;
}

.warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.warning {
  font-size: var(--text-xs);
  color: var(--palette-warning-300);
}

.item-note {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-style: italic;
}

/* Batch legend */
.batch-legend {
  margin-top: var(--space-4);
  padding: var(--space-4);
  background: var(--border-default);
  border-radius: var(--radius-sm);
}

.batch-legend h4 {
  font-size: var(--text-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-body);
  margin-bottom: var(--space-3);
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-body);
}

.legend-item svg.exact {
  color: var(--palette-success-300);
}

.legend-item svg.lower {
  color: var(--palette-warning-300);
}

.legend-item svg.missing {
  color: var(--palette-error-300);
}

/* Actions */
.actions-section {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-6);
}

/* Creating quote loading */
.creating-quote {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-12);
}

.creating-quote p {
  font-size: var(--text-lg);
  color: var(--text-body);
}
</style>
