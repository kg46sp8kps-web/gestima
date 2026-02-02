<script setup lang="ts">
/**
 * ManufacturingItemActionsWidget - Action buttons for manufacturing items
 *
 * Actions:
 * - Edit, Operations, Materials, Pricing, Drawing
 *
 * Design: Flat buttons with red Lucide icons + text
 */

import { computed } from 'vue'
import { Edit, Settings, Package, DollarSign, FileText } from 'lucide-vue-next'
import type { Part } from '@/types/part'

interface Props {
  context?: {
    itemId?: number | null
    part?: Part | null
    disabled?: boolean
  }
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

const disabled = computed(() => props.context?.disabled || false)

const actions = computed(() => [
  {
    id: 'edit',
    label: 'Upravit',
    icon: Edit
  },
  {
    id: 'operations',
    label: 'Operace',
    icon: Settings
  },
  {
    id: 'materials',
    label: 'Materiály',
    icon: Package
  },
  {
    id: 'pricing',
    label: 'Kalkulace',
    icon: DollarSign
  },
  {
    id: 'drawing',
    label: 'Výkres',
    icon: FileText
  }
])

function handleAction(actionId: string) {
  emit('action', actionId, {
    itemId: props.context?.itemId,
    part: props.context?.part
  })
}

function handleDrawingRightClick(event: MouseEvent) {
  event.preventDefault()
  if (disabled.value) return
  emit('action', 'drawing-manage', {
    itemId: props.context?.itemId,
    part: props.context?.part
  })
}
</script>

<template>
  <div class="widget-root">
    <div class="action-grid">
      <button
        v-for="action in actions.slice(0, 4)"
        :key="action.id"
        class="action-btn"
        :disabled="disabled"
        @click="handleAction(action.id)"
      >
        <component :is="action.icon" :size="20" class="action-icon" />
        <span class="action-label">{{ action.label }}</span>
      </button>

      <!-- Drawing button with special right-click -->
      <button
        class="action-btn"
        :disabled="disabled"
        @click="handleAction('drawing')"
        @contextmenu="handleDrawingRightClick"
        title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
      >
        <component :is="FileText" :size="20" class="action-icon" />
        <span class="action-label">Výkres</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* CRITICAL: Widget root - sizeToContent compatible */
.widget-root {
  /* NO height: 100% - allows GridStack sizeToContent! */
  display: flex;
  flex-direction: column;
  /* Padding is in WidgetWrapper now */
  /* Container-type is in WidgetWrapper - use @container widget-content for breakpoints */
}

/* Action grid */
.action-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-content: flex-start;
}

/* Flat button design */
.action-btn {
  /* Layout */
  flex: 1 1 calc(33.333% - var(--space-2)); /* 3 columns */
  min-width: 100px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);

  /* Spacing */
  padding: var(--space-3);

  /* Style - FLAT design */
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);

  /* Typography */
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);

  /* Interaction */
  cursor: pointer;
  transition: var(--transition-fast);
}

.action-btn:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.action-btn:active:not(:disabled) {
  background: var(--state-active);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* RED Lucide icon */
.action-icon {
  color: var(--color-primary); /* Red (#991b1b) */
  flex-shrink: 0;
}

/* Text label */
.action-label {
  flex: 1;
  text-align: left;
}

/* Container queries: responsive columns */
/* Use widget-content container from WidgetWrapper */
@container widget-content (max-width: 400px) {
  .action-grid {
    gap: var(--space-2);
  }

  .action-btn {
    flex: 1 1 calc(50% - var(--space-2)); /* 2 columns */
  }
}

@container widget-content (max-width: 250px) {
  .action-btn {
    flex: 1 1 100%; /* 1 column */
  }
}
</style>
