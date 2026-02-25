<script setup lang="ts">
import { ref } from 'vue'
import * as quotesApi from '@/api/quotes'
import type { QuoteDetail } from '@/types/quote'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/ui/Modal.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'

interface Props {
  modelValue: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [quote: QuoteDetail]
}>()

const ui = useUiStore()

const form = ref({
  title: '',
  customer_request_number: '',
  offer_deadline: '',
  valid_until: '',
  delivery_terms: '',
  tax_percent: 21,
  discount_percent: 0,
  notes: '',
})

const saving = ref(false)

function close() {
  emit('update:modelValue', false)
}

async function onSubmit() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = {}
    if (form.value.title) payload.title = form.value.title
    if (form.value.customer_request_number) payload.customer_request_number = form.value.customer_request_number
    if (form.value.offer_deadline) payload.offer_deadline = form.value.offer_deadline
    if (form.value.valid_until) payload.valid_until = form.value.valid_until
    if (form.value.delivery_terms) payload.delivery_terms = form.value.delivery_terms
    if (form.value.notes) payload.notes = form.value.notes
    payload.tax_percent = form.value.tax_percent
    payload.discount_percent = form.value.discount_percent

    const created = await quotesApi.create(payload as Parameters<typeof quotesApi.create>[0])
    ui.showSuccess(`Nabídka ${created.quote_number} vytvořena`)
    emit('created', created)
    close()
    form.value = {
      title: '',
      customer_request_number: '',
      offer_deadline: '',
      valid_until: '',
      delivery_terms: '',
      tax_percent: 21,
      discount_percent: 0,
      notes: '',
    }
  } catch {
    ui.showError('Chyba při vytváření nabídky')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Modal :model-value="modelValue" title="Nová nabídka" size="sm" @update:model-value="close">
    <form class="nq-form" @submit.prevent="onSubmit">
      <Input
        v-model="form.title"
        label="Název nabídky"
        placeholder="Název nabídky…"
        testid="new-quote-title"
      />
      <Input
        v-model="form.customer_request_number"
        label="Číslo poptávky zákazníka"
        placeholder="RFQ-…"
        testid="new-quote-crn"
      />
      <div class="nq-row">
        <Input
          v-model="form.offer_deadline"
          label="Termín odevzdání"
          type="date"
          testid="new-quote-deadline"
        />
        <Input
          v-model="form.valid_until"
          label="Platnost nabídky"
          type="date"
          testid="new-quote-valid"
        />
      </div>
      <Input
        v-model="form.delivery_terms"
        label="Dodací podmínky"
        placeholder="EXW, DAP, …"
        testid="new-quote-delivery"
      />
      <div class="nq-row">
        <Input
          v-model.number="form.tax_percent"
          label="DPH %"
          type="number"
          testid="new-quote-tax"
        />
        <Input
          v-model.number="form.discount_percent"
          label="Sleva %"
          type="number"
          testid="new-quote-discount"
        />
      </div>
      <Textarea
        v-model="form.notes"
        label="Poznámky"
        placeholder="Doplňující informace…"
        :rows="3"
        testid="new-quote-notes"
      />
    </form>

    <template #footer>
      <button class="btn-secondary" data-testid="new-quote-cancel" type="button" @click="close">
        Zrušit
      </button>
      <button
        class="btn-primary"
        data-testid="new-quote-submit"
        type="button"
        :disabled="saving"
        @click="onSubmit"
      >
        {{ saving ? 'Ukládám…' : 'Vytvořit' }}
      </button>
    </template>
  </Modal>
</template>

<style scoped>
.nq-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.nq-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
</style>
