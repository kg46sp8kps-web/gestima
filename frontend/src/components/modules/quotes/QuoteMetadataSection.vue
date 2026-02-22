<script setup lang="ts">
import { FileText } from 'lucide-vue-next'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE } from '@/config/design'

interface Metadata {
  title: string
  customer_request_number: string
  request_date: string
  offer_deadline: string
  discount_percent: number
  tax_percent: number
  notes: string
}

interface Props {
  metadata: Metadata
}

interface Emits {
  (e: 'update:metadata', metadata: Metadata): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

function updateField(field: keyof Metadata, value: string | number) {
  emit('update:metadata', { ...props.metadata, [field]: value } as Metadata)
}
</script>

<template>
  <div class="metadata-section">
    <h2><FileText :size="ICON_SIZE.STANDARD" class="section-icon" /> Detaily nabídky</h2>
    <div class="form-row">
      <div class="form-field">
        <label>Název nabídky *</label>
        <Input :model-value="metadata.title" @update:model-value="updateField('title', $event)" placeholder="Poptávka Q1/2026" />
      </div>
      <div class="form-field">
        <label>Číslo poptávky zákazníka</label>
        <Input :model-value="metadata.customer_request_number" @update:model-value="updateField('customer_request_number', $event)" placeholder="P20971, RFQ-2026-001..." />
      </div>
    </div>

    <div class="form-row">
      <div class="form-field">
        <label>Datum poptávky</label>
        <input
          :value="metadata.request_date"
          @input="updateField('request_date', ($event.target as HTMLInputElement).value)"
          type="date"
          class="form-input"
        />
      </div>
      <div class="form-field">
        <label>Deadline nabídky</label>
        <input
          :value="metadata.offer_deadline"
          @input="updateField('offer_deadline', ($event.target as HTMLInputElement).value)"
          type="date"
          class="form-input"
        />
      </div>
    </div>

    <div class="form-row">
      <div class="form-field">
        <label>Sleva (%)</label>
        <Input :model-value="metadata.discount_percent" @update:model-value="updateField('discount_percent', Number($event))" type="number" step="0.01" />
      </div>
      <div class="form-field">
        <label>DPH (%)</label>
        <Input :model-value="metadata.tax_percent" @update:model-value="updateField('tax_percent', Number($event))" type="number" step="0.01" />
      </div>
    </div>

    <div class="form-field">
      <label>Poznámky</label>
      <textarea
        :value="metadata.notes"
        @input="updateField('notes', ($event.target as HTMLTextAreaElement).value)"
        class="form-textarea"
        rows="3"
        placeholder="Termín dodání, speciální podmínky..."
      ></textarea>
    </div>
  </div>
</template>

<style scoped>
.metadata-section {
  padding: 12px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.metadata-section h2 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--t1);
}

.section-icon {
  display: inline;
  margin-right: var(--pad);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--pad);
  margin-bottom: var(--pad);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.form-textarea {
  width: 100%;
  padding: var(--pad);
  background: var(--b2);
  border: 1px solid var(--t3);
  border-radius: var(--rs);
  color: var(--t1);
  font-family: inherit;
  font-size: var(--fs);
}

.form-textarea {
  resize: vertical;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--t3);
}
</style>
