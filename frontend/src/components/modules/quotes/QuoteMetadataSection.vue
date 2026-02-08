<script setup lang="ts">
import { FileText } from 'lucide-vue-next'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE } from '@/config/design'

interface Metadata {
  title: string
  customer_request_number: string
  valid_until: string
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
    <h2><FileText :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: 8px;" /> Detaily nabídky</h2>
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
        <label>Platnost do</label>
        <input
          :value="metadata.valid_until"
          @input="updateField('valid_until', ($event.target as HTMLInputElement).value)"
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
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.metadata-section h2 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-3);
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
</style>
