<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartnersStore } from '@/stores/partners'
import type { Quote, QuoteCreate } from '@/types/quote'
import { FileText } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  'close': []
  'created': [quote: Quote]
}>()

const quotesStore = useQuotesStore()
const partnersStore = usePartnersStore()

const isSubmitting = ref(false)

const form = reactive<QuoteCreate>({
  title: '',
  description: '',
  customer_request_number: null,
  partner_id: null,
  valid_until: null,
  discount_percent: 0,
  tax_percent: 21
})

function resetForm() {
  form.title = ''
  form.description = ''
  form.customer_request_number = null
  form.partner_id = null
  form.valid_until = null
  form.discount_percent = 0
  form.tax_percent = 21
}

watch(() => props.show, (visible) => {
  if (visible) {
    resetForm()
    partnersStore.fetchPartners()
  }
})

async function submit() {
  isSubmitting.value = true
  try {
    const quote = await quotesStore.createQuote({
      title: form.title,
      description: form.description || undefined,
      customer_request_number: form.customer_request_number || undefined,
      partner_id: form.partner_id,
      valid_until: form.valid_until,
      discount_percent: form.discount_percent,
      tax_percent: form.tax_percent
    })
    emit('created', quote)
    emit('close')
  } catch {
    // Error handled in store
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <FileText :size="ICON_SIZE.STANDARD" />
          <h3>Nová nabídka</h3>
        </div>

        <form @submit.prevent="submit" class="create-form">
          <div class="form-group">
            <label>Název</label>
            <input
              v-model="form.title"
              type="text"
              class="form-input"
              maxlength="200"
              placeholder="Název nabídky (volitelné)"
            />
          </div>

          <div class="form-group">
            <label>Popis</label>
            <textarea
              v-model="form.description"
              class="form-textarea"
              rows="3"
              maxlength="1000"
              placeholder="Popis nabídky"
            ></textarea>
          </div>

          <div class="form-group">
            <label>Číslo poptávky zákazníka</label>
            <input
              v-model="form.customer_request_number"
              type="text"
              class="form-input"
              maxlength="50"
              placeholder="P20971, RFQ-2026-001..."
            />
          </div>

          <div class="form-group">
            <label>Partner</label>
            <select v-model="form.partner_id" class="form-input">
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
              <input v-model="form.valid_until" type="date" class="form-input" />
            </div>
            <div class="form-group">
              <label>Sleva (%)</label>
              <input
                v-model.number="form.discount_percent"
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
                v-model.number="form.tax_percent"
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
            <button type="button" class="btn-secondary" @click="emit('close')">
              Zrušit
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="isSubmitting || !form.title"
            >
              {{ isSubmitting ? 'Vytvářím...' : 'Vytvořit' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>

.modal-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  color: var(--text-primary);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
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

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

</style>
