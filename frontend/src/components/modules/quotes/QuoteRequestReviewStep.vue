<script setup lang="ts">
// QuoteRequestReviewStep — Step 2 of V2 wizard. Review/edit AI-parsed data before creating quote.
import { computed, reactive, watch } from 'vue'
import type { QuoteRequestReviewV2, QuoteFromRequestCreateV2, EstimationData } from '@/types/quote'
import QuoteSummarySection from './QuoteSummarySection.vue'
import QuoteCustomerSection from './QuoteCustomerSection.vue'
import QuoteMetadataSection from './QuoteMetadataSection.vue'
import { Check, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  review: QuoteRequestReviewV2
  drawingFiles: File[]
}>()

const emit = defineEmits<{
  'back': []
  'confirm': [data: QuoteFromRequestCreateV2, drawingFiles: File[]]
}>()

interface EditableItemV2 {
  article_number: string
  drawing_number: string | null
  name: string
  quantity: number
  notes: string | null
  part_id: number | null
  part_exists: boolean
  drawing_index: number | null
  estimation: EstimationData | null
  batch_match: { status: string; unit_price: number; line_total: number; warnings: string[] } | null
}

const formData = reactive({
  customer: { company_name: '', ico: '', contact_person: '', email: '', phone: '' },
  title: '',
  customer_request_number: '',
  request_date: '',
  offer_deadline: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: ''
})

const editableItems = reactive<EditableItemV2[]>([])

watch(() => props.review, (r) => {
  if (!r) return
  formData.customer.company_name = r.customer.company_name
  formData.customer.ico = r.customer.ico || ''
  formData.customer.contact_person = r.customer.contact_person || ''
  formData.customer.email = r.customer.email || ''
  formData.customer.phone = r.customer.phone || ''
  formData.customer_request_number = r.customer_request_number || ''
  formData.request_date = r.request_date || ''
  formData.offer_deadline = r.offer_deadline || ''
  formData.notes = r.notes || ''
  formData.title = `Poptavka ${r.customer.company_name} - ${new Date().toLocaleDateString('cs-CZ')}`

  editableItems.length = 0
  r.items.forEach((item, idx) => {
    const drawingMatch = r.drawing_matches.find(m => m.item_index === idx)
    const analysis = drawingMatch != null ? r.drawing_analyses[drawingMatch.drawing_index] : null
    editableItems.push({
      article_number: item.article_number,
      drawing_number: item.drawing_number,
      name: item.name,
      quantity: item.quantity,
      notes: item.notes,
      part_id: item.part_id,
      part_exists: item.part_exists,
      drawing_index: drawingMatch?.drawing_index ?? null,
      estimation: analysis
        ? { part_type: analysis.part_type, complexity: analysis.complexity,
            estimated_time_min: analysis.estimated_time_min,
            max_diameter_mm: analysis.max_diameter_mm, max_length_mm: analysis.max_length_mm }
        : null,
      batch_match: item.batch_match
    })
  })
}, { immediate: true })

const isFormValid = computed(() =>
  formData.title.trim() !== '' && formData.customer.company_name.trim() !== ''
)

function handleConfirm() {
  if (!isFormValid.value) return
  const { partner_exists, partner_id } = props.review.customer
  const data: QuoteFromRequestCreateV2 = {
    title: formData.title,
    customer_request_number: formData.customer_request_number || null,
    request_date: formData.request_date || null,
    offer_deadline: formData.offer_deadline || null,
    valid_until: null,
    notes: formData.notes || null,
    discount_percent: formData.discount_percent,
    tax_percent: formData.tax_percent,
    partner_id: partner_exists ? partner_id : null,
    partner_data: partner_exists ? null : {
      company_name: formData.customer.company_name,
      contact_person: formData.customer.contact_person || null,
      email: formData.customer.email || null,
      phone: formData.customer.phone || null,
      ico: formData.customer.ico || null,
      dic: null, is_customer: true, is_supplier: false
    },
    items: editableItems.map(item => ({
      part_id: item.part_exists ? item.part_id : null,
      article_number: item.article_number, drawing_number: item.drawing_number,
      name: item.name, quantity: item.quantity, notes: item.notes,
      drawing_index: item.drawing_index, estimation: item.estimation
    }))
  }
  const referencedFiles: File[] = []
  const indexMap = new Map<number, number>()
  for (const item of editableItems) {
    if (item.drawing_index != null && !indexMap.has(item.drawing_index)) {
      const file = props.drawingFiles[item.drawing_index]
      if (file != null) {
        indexMap.set(item.drawing_index, referencedFiles.length)
        referencedFiles.push(file)
      }
    }
  }
  emit('confirm', data, referencedFiles)
}
</script>

<template>
  <div class="review-step">
    <QuoteSummarySection :summary="review.summary" />

    <QuoteCustomerSection
      :customer="formData.customer"
      :review-customer="review.customer"
      @update:customer="formData.customer = $event"
    />

    <div class="items-section">
      <h3>Polozky ({{ editableItems.length }})</h3>
      <div class="items-table-wrapper">
        <table class="items-table">
          <thead>
            <tr>
              <th>#</th><th>Artikl</th><th>Cislo vykresu</th><th>Nazev</th><th>Ks</th>
              <th>Vykres PDF</th><th>Typ</th><th>Stav</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in editableItems" :key="i">
              <td>{{ i + 1 }}</td>
              <td class="col-mono">{{ item.article_number }}</td>
              <td class="col-mono">{{ item.drawing_number || '—' }}</td>
              <td>{{ item.name }}</td>
              <td class="col-right">{{ item.quantity }}</td>
              <td>
                <span v-if="item.drawing_index != null" class="badge badge-ok">
                  <CheckCircle :size="ICON_SIZE.SMALL" /> Prirazen
                </span>
                <span v-else class="badge badge-warn">
                  <AlertCircle :size="ICON_SIZE.SMALL" /> Chybi
                </span>
              </td>
              <td>
                <span v-if="item.estimation" class="badge badge-info">
                  {{ item.estimation.part_type }} · {{ item.estimation.complexity }}
                </span>
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <span v-if="item.part_exists" class="badge badge-ok">Existuje</span>
                <span v-else class="badge badge-new">Novy</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <QuoteMetadataSection
      :metadata="{
        title: formData.title,
        customer_request_number: formData.customer_request_number,
        request_date: formData.request_date,
        offer_deadline: formData.offer_deadline,
        discount_percent: formData.discount_percent,
        tax_percent: formData.tax_percent,
        notes: formData.notes
      }"
      @update:metadata="Object.assign(formData, $event)"
    />

    <div class="actions">
      <button class="action-btn" @click="emit('back')">
        <ArrowLeft :size="ICON_SIZE.SMALL" /> Zpet
      </button>
      <button class="action-btn action-primary" :disabled="!isFormValid" @click="handleConfirm">
        <Check :size="ICON_SIZE.SMALL" /> Vytvorit nabidku
      </button>
    </div>
  </div>
</template>

<style scoped>
.review-step {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
.items-section h3 {
  margin: 0 0 var(--pad) 0;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}
.items-table-wrapper { overflow-x: auto; }
.items-table { width: 100%; border-collapse: collapse; }
.items-table th {
  background: var(--surface);
  font-size: var(--fs);
  color: var(--t3);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 6px var(--pad);
  text-align: left;
  border-bottom: 1px solid var(--b2);
}
.items-table td {
  font-size: var(--fs);
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b2);
}
.col-mono { font-family: var(--mono); font-weight: 600; }
.col-right { text-align: right; }
.text-muted { color: var(--t3); }
.badge-ok  { background: var(--raised);  color: var(--ok); }
.badge-warn{ background: var(--raised);  color: var(--warn); }
.badge-new { background: var(--raised);  color: var(--t3); }
.badge-info{ background: var(--raised);color: var(--t3); }
.actions {
  display: flex;
  justify-content: space-between;
  gap: var(--pad);
  padding-top: 12px;
}
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: transparent;
  color: var(--t2);
  font-weight: 500;
  cursor: pointer;
  font-size: var(--fs);
}
.action-btn:hover { background: var(--b1); }
.action-primary { border-color: var(--red); color: var(--red); }
.action-primary:hover:not(:disabled) { background: var(--red-10); }
.action-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
