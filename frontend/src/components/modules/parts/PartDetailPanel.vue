<script setup lang="ts">
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
}>()

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="part-detail-panel">
    <div class="part-header">
      <h2 class="part-title">{{ part.name }}</h2>
      <span class="part-number-badge">{{ part.part_number }}</span>
    </div>

    <div class="part-details">
      <div class="detail-row" v-if="part.notes">
        <span class="detail-label">Popis:</span>
        <span class="detail-value">{{ part.notes }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Vytvořeno:</span>
        <span class="detail-value">{{ formatDate(part.created_at) }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Aktualizováno:</span>
        <span class="detail-value">{{ formatDate(part.updated_at) }}</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="actions-grid">
      <button class="action-button" @click="emit('open-material')">
        <span class="action-icon">📦</span>
        <span class="action-label">Materiál</span>
      </button>
      <button class="action-button" @click="emit('open-operations')">
        <span class="action-icon">⚙️</span>
        <span class="action-label">Operace</span>
      </button>
      <button class="action-button" @click="emit('open-pricing')">
        <span class="action-icon">💰</span>
        <span class="action-label">Ceny</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue DETAIL section */
.part-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.part-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.part-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.part-number-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.part-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.detail-row {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.detail-label {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  min-width: 120px;
}

.detail-value {
  color: var(--text-base);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-normal);
}

.action-button:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  font-size: 2rem;
}

.action-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-base);
}
</style>
