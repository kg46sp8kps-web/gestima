<script setup lang="ts">
/**
 * QuoteInfoTab — Tab 0: Základní info
 * Displays and edits core quote fields: partner, title, description,
 * customer request number, validity date, discount, tax.
 */
import type { QuoteWithItems } from '@/types/quote'
import type { Partner } from '@/types/partner'
import { Lock } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface EditForm {
  partner_id: number | null
  title: string
  description: string
  customer_request_number: string
  valid_until: string
  discount_percent: number
  tax_percent: number
}

const props = defineProps<{
  quote: QuoteWithItems
  isEditing: boolean
  canEdit: boolean
  editForm: EditForm
  partners: Partner[]
}>()
</script>

<template>
  <form class="info-form">
    <div class="form-group">
      <label>Partner</label>
      <select
        v-model="props.editForm.partner_id"
        class="form-input"
        :disabled="!isEditing"
      >
        <option :value="null">-- Bez partnera --</option>
        <option
          v-for="partner in partners"
          :key="partner.id"
          :value="partner.id"
        >
          {{ partner.company_name }} ({{ partner.partner_number }})
        </option>
      </select>
    </div>

    <div class="form-group">
      <label>Název <span class="required">*</span></label>
      <input
        v-model="props.editForm.title"
        type="text"
        class="form-input"
        :disabled="!isEditing"
        required
        maxlength="200"
      />
    </div>

    <div class="form-group">
      <label>Popis</label>
      <textarea
        v-model="props.editForm.description"
        class="form-textarea"
        :disabled="!isEditing"
        rows="3"
        maxlength="1000"
      ></textarea>
    </div>

    <div class="form-group">
      <label>Číslo poptávky zákazníka</label>
      <input
        v-model="props.editForm.customer_request_number"
        type="text"
        class="form-input"
        :disabled="!isEditing"
        maxlength="50"
        placeholder="P20971, RFQ-2026-001..."
      />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Platnost do</label>
        <input
          v-model="props.editForm.valid_until"
          type="date"
          class="form-input"
          :disabled="!isEditing"
        />
      </div>
      <div class="form-group">
        <label>Sleva (%)</label>
        <input
          v-model.number="props.editForm.discount_percent"
          type="number"
          class="form-input"
          :disabled="!isEditing"
          min="0"
          max="100"
          step="0.01"
          v-select-on-focus
        />
      </div>
      <div class="form-group">
        <label>DPH (%)</label>
        <input
          v-model.number="props.editForm.tax_percent"
          type="number"
          class="form-input"
          :disabled="!isEditing"
          min="0"
          max="100"
          step="0.01"
          v-select-on-focus
        />
      </div>
    </div>

    <div v-if="!canEdit" class="edit-lock-notice">
      <Lock :size="ICON_SIZE.SMALL" class="lock-icon" />
      <span>Nabídku lze editovat pouze ve stavu "Koncept"</span>
    </div>
  </form>
</template>

<style scoped>
.info-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
}

.required {
  color: var(--palette-danger);
}

.edit-lock-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(115, 115, 115, 0.1);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}
</style>
