<script setup lang="ts">
import { CheckCircle2, AlertCircle, User } from 'lucide-vue-next'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE } from '@/config/design'

interface Customer {
  company_name: string
  ico: string
  contact_person: string
  email: string
  phone: string
}

interface ReviewCustomer {
  partner_exists: boolean
  partner_number: string | null
}

interface Props {
  customer: Customer
  reviewCustomer: ReviewCustomer
}

interface Emits {
  (e: 'update:customer', customer: Customer): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

function updateField(field: keyof Customer, value: string) {
  emit('update:customer', { ...props.customer, [field]: value } as Customer)
}
</script>

<template>
  <div class="customer-section">
    <h2><User :size="ICON_SIZE.STANDARD" class="section-icon" /> Zákazník</h2>
    <div class="customer-info">
      <div class="form-row">
        <div class="form-field">
          <label>Firma</label>
          <Input :model-value="customer.company_name" @update:model-value="updateField('company_name', String($event))" placeholder="Název firmy" />
        </div>
        <div class="form-field">
          <label>IČO</label>
          <Input :model-value="customer.ico" @update:model-value="updateField('ico', String($event))" placeholder="12345678" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-field">
          <label>Kontaktní osoba</label>
          <Input :model-value="customer.contact_person" @update:model-value="updateField('contact_person', String($event))" placeholder="Jméno Příjmení" />
        </div>
        <div class="form-field">
          <label>Email</label>
          <Input :model-value="customer.email" @update:model-value="updateField('email', String($event))" type="email" placeholder="email@example.com" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-field">
          <label>Telefon</label>
          <Input :model-value="customer.phone" @update:model-value="updateField('phone', String($event))" placeholder="+420 123 456 789" />
        </div>
      </div>

      <div v-if="reviewCustomer.partner_exists" class="match-result success">
        <CheckCircle2 :size="ICON_SIZE.SMALL" />
        <span>Zákazník nalezen: {{ reviewCustomer.partner_number }}</span>
      </div>
      <div v-else class="match-result warning">
        <AlertCircle :size="ICON_SIZE.SMALL" />
        <span>Zákazník bude vytvořen jako nový partner</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.customer-section {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.customer-section h2 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.section-icon {
  display: inline;
  margin-right: var(--space-3);
}

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
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-body);
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
</style>
