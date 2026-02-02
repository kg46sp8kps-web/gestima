<script setup lang="ts">
/**
 * InfoCard.vue - Generic information display widget
 *
 * Displays key-value pairs in a card format.
 * Useful for showing part details, quote info, etc.
 *
 * @example
 * ```vue
 * <InfoCard :context="{
 *   fields: [
 *     { label: 'Part Number', value: 'P-001' },
 *     { label: 'Name', value: 'Shaft' }
 *   ]
 * }" />
 * ```
 */

import { computed } from 'vue'

interface Field {
  label: string
  value: any
  format?: 'text' | 'date' | 'number' | 'currency'
}

interface Props {
  context?: {
    fields?: Field[]
    title?: string
    emptyMessage?: string
  }
}

const props = defineProps<Props>()

const fields = computed(() => props.context?.fields || [])
const title = computed(() => props.context?.title)
const emptyMessage = computed(() => props.context?.emptyMessage || 'No data available')

function formatValue(value: any, format?: string): string {
  if (value == null || value === '') return '—'

  switch (format) {
    case 'date':
      return new Date(value).toLocaleDateString('cs-CZ')
    case 'number':
      return value.toLocaleString('cs-CZ')
    case 'currency':
      return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK'
      }).format(value)
    default:
      return String(value)
  }
}
</script>

<template>
  <div class="info-card">
    <h3 v-if="title" class="info-card-title">{{ title }}</h3>

    <div v-if="fields.length === 0" class="empty-state">
      <p>{{ emptyMessage }}</p>
    </div>

    <div v-else class="fields">
      <div
        v-for="(field, index) in fields"
        :key="index"
        class="field"
      >
        <span class="field-label">{{ field.label }}:</span>
        <span class="field-value">{{ formatValue(field.value, field.format) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.info-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
}

.info-card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}

.fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.field-value {
  font-size: var(--text-base);
  color: var(--text-body);
  word-break: break-word;
}

/* Responsive: Horizontal layout on wide containers */
@container widget (min-width: 400px) {
  .field {
    flex-direction: row;
    align-items: baseline;
    gap: var(--space-2);
  }

  .field-label {
    min-width: 120px;
    flex-shrink: 0;
  }

  .field-value {
    flex: 1;
  }
}
</style>
