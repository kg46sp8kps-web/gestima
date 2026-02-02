<script setup lang="ts">
/**
 * PartActions.vue - Part action buttons widget
 *
 * Displays action buttons for Material, Operations, Pricing, and Drawing.
 * Drawing button supports both left-click (open) and right-click (manage).
 *
 * @example
 * ```vue
 * <PartActions
 *   :context="{ hasDrawing: true, disabled: false }"
 *   @action="handleAction"
 * />
 * ```
 */

import { computed } from 'vue'
import { Package, Settings, DollarSign, FileText } from 'lucide-vue-next'

interface Props {
  context?: {
    hasDrawing?: boolean
    disabled?: boolean
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

const disabled = computed(() => props.context?.disabled || false)
const hasDrawing = computed(() => props.context?.hasDrawing || false)

function handleMaterial() {
  if (disabled.value) return
  emit('action', 'action:material')
}

function handleOperations() {
  if (disabled.value) return
  emit('action', 'action:operations')
}

function handlePricing() {
  if (disabled.value) return
  emit('action', 'action:pricing')
}

function handleDrawingClick() {
  if (disabled.value) return
  emit('action', 'action:drawing')
}

function handleDrawingRightClick(event: MouseEvent) {
  event.preventDefault()
  if (disabled.value) return
  emit('action', 'action:drawing-manage')
}
</script>

<template>
  <div class="part-actions">
    <button
      class="action-button"
      :disabled="disabled"
      @click="handleMaterial"
      title="Materiál"
    >
      <Package :size="32" class="action-icon" />
      <span class="action-label">Materiál</span>
    </button>

    <button
      class="action-button"
      :disabled="disabled"
      @click="handleOperations"
      title="Operace"
    >
      <Settings :size="32" class="action-icon" />
      <span class="action-label">Operace</span>
    </button>

    <button
      class="action-button"
      :disabled="disabled"
      @click="handlePricing"
      title="Ceny"
    >
      <DollarSign :size="32" class="action-icon" />
      <span class="action-label">Ceny</span>
    </button>

    <button
      class="action-button"
      :disabled="disabled"
      @click="handleDrawingClick"
      @contextmenu="handleDrawingRightClick"
      title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
    >
      <FileText :size="32" class="action-icon" />
      <span class="action-label">Výkres</span>
    </button>
  </div>
</template>

<style scoped>
.part-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  height: 100%;
  align-content: start;
  padding: var(--space-2);
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

.action-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-icon {
  color: var(--color-primary);
}

.action-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

/* Responsive: 2 columns on narrow containers */
@container widget (max-width: 400px) {
  .part-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Responsive: 4 columns on wide containers */
@container widget (min-width: 600px) {
  .part-actions {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
