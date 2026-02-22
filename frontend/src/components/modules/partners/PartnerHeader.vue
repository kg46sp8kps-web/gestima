<script setup lang="ts">
/**
 * Partner Header Component
 * Displays partner info summary and type badges
 */
import { computed } from 'vue'
import type { Partner } from '@/types/partner'
import { Users, Factory } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

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
          <Users :size="ICON_SIZE.STANDARD" class="badge-icon" />
          Zákazník
        </span>
        <span v-if="partner.is_supplier" class="type-badge supplier">
          <Factory :size="ICON_SIZE.STANDARD" class="badge-icon" />
          Dodavatel
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
  gap: var(--pad);
  padding: 12px;
  border-bottom: 1px solid var(--b2);
  background: var(--surface);
  min-height: 120px;
}

.partner-info {
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.partner-main {
  display: flex;
  align-items: center;
  gap: var(--pad);
  flex-wrap: wrap;
}

.partner-main h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.partner-badge {
  padding: 4px var(--pad);
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
  border: 1px solid var(--red);
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}

.partner-type {
  display: flex;
  align-items: center;
  gap: 6px;
}

.type-badge {
  padding: 4px var(--pad);
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.badge-icon {
  display: inline-block;
}

.type-badge.customer {
  background: var(--t3);
  color: white;
}

.type-badge.supplier {
  background: var(--t3);
  color: white;
}

.contact-summary {
  display: flex;
  align-items: center;
  padding: 6px var(--pad);
  background: var(--raised);
  border-radius: var(--r);
  border: 1px solid var(--b2);
}

.contact-text {
  font-size: var(--fs);
  color: var(--t3);
}

.empty-text {
  font-size: var(--fs);
  color: var(--t3);
}
</style>
