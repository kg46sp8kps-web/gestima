<script setup lang="ts">
/**
 * Partner Header Component
 * Displays partner info summary and type badges
 */
import { computed } from 'vue'
import type { Partner } from '@/types/partner'

interface Props {
  partner: Partner | null
}

const props = defineProps<Props>()

const partnerType = computed(() => {
  if (!props.partner) return ''
  if (props.partner.is_customer && props.partner.is_supplier) return 'Zákazník & Dodavatel'
  if (props.partner.is_customer) return 'Zákazník'
  if (props.partner.is_supplier) return 'Dodavatel'
  return ''
})

const contactInfo = computed(() => {
  if (!props.partner) return ''
  const parts: string[] = []
  if (props.partner.email) parts.push(props.partner.email)
  if (props.partner.phone) parts.push(props.partner.phone)
  return parts.join(' • ')
})
</script>

<template>
  <div class="partner-header">
    <!-- Partner Info -->
    <div v-if="partner" class="partner-info">
      <div class="partner-main">
        <h2>{{ partner.company_name }}</h2>
        <span class="partner-badge">{{ partner.partner_number }}</span>
      </div>

      <!-- Type Badges -->
      <div class="partner-type">
        <span v-if="partner.is_customer" class="type-badge customer">
          👥 Zákazník
        </span>
        <span v-if="partner.is_supplier" class="type-badge supplier">
          🏭 Dodavatel
        </span>
      </div>

      <!-- Contact Info Summary -->
      <div v-if="contactInfo" class="contact-summary">
        <span class="contact-text">{{ contactInfo }}</span>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <span class="empty-text">Vyberte partnera ze seznamu</span>
    </div>
  </div>
</template>

<style scoped>
.partner-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
  min-height: 120px;
}

.partner-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.partner-main {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.partner-main h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.partner-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--palette-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.partner-type {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.type-badge {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.type-badge.customer {
  background: var(--palette-info);
  color: white;
}

.type-badge.supplier {
  background: var(--palette-secondary);
  color: white;
}

.contact-summary {
  display: flex;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.contact-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>
