<script setup lang="ts">
/**
 * ActionBar.vue - Generic action buttons widget
 *
 * Displays a grid of action buttons with icons and labels.
 * Useful for Material, Operations, Pricing, Drawing buttons.
 *
 * @example
 * ```vue
 * <ActionBar :context="{
 *   actions: [
 *     { id: 'material', label: 'Material', icon: 'Package', color: '#059669' },
 *     { id: 'operations', label: 'Operations', icon: 'Settings', color: '#2563eb' }
 *   ]
 * }" @action="handleAction" />
 * ```
 */

import { computed } from 'vue'
import * as Icons from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Action {
  id: string
  label: string
  icon: string // Lucide icon name
  color?: string
  disabled?: boolean
}

interface Props {
  context?: {
    actions?: Action[]
    disabled?: boolean
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

const actions = computed(() => props.context?.actions || [])
const disabled = computed(() => props.context?.disabled || false)

function getIconComponent(iconName: string) {
  return (Icons as any)[iconName] || Icons.HelpCircle
}

function handleAction(actionId: string) {
  if (disabled.value) return
  emit('action', `action:${actionId}`)
}
</script>

<template>
  <div class="action-bar">
    <button
      v-for="action in actions"
      :key="action.id"
      @click="handleAction(action.id)"
      class="action-button"
      :disabled="disabled || action.disabled"
      :title="action.label"
    >
      <component
        :is="getIconComponent(action.icon)"
        :size="ICON_SIZE.LARGE"
        :color="action.color"
        class="action-icon"
      />
      <span class="action-label">{{ action.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.action-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: var(--space-2);
  height: 100%;
  align-content: start;
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  min-height: 80px;
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
  flex-shrink: 0;
}

.action-label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-body);
  text-align: center;
  word-break: break-word;
}

/* Responsive: More columns on wider containers */
@container widget (min-width: 400px) {
  .action-bar {
    grid-template-columns: repeat(2, 1fr);
  }
}

@container widget (min-width: 600px) {
  .action-bar {
    grid-template-columns: repeat(3, 1fr);
  }
}

@container widget (min-width: 800px) {
  .action-bar {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
