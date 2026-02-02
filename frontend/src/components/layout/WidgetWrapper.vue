<script setup lang="ts">
/**
 * WidgetWrapper.vue - Widget container with chrome
 *
 * Provides consistent widget UI:
 * - Title bar (drag handle)
 * - Action menu (remove, configure)
 * - Content area
 * - Error handling
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 */

import { computed, defineAsyncComponent } from 'vue'
import { X, MoreVertical } from 'lucide-vue-next'
import type { WidgetDefinition } from '@/types/widget'

interface Props {
  /**
   * Widget definition (id, title, component, etc.)
   */
  definition: WidgetDefinition

  /**
   * Data context passed to widget
   */
  context?: Record<string, any>

  /**
   * Is edit mode enabled?
   */
  editMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  context: () => ({}),
  editMode: false
})

const emit = defineEmits<{
  'action': [action: string, payload?: any]
  'remove': []
  'configure': []
}>()

// Dynamically load widget component
const widgetComponent = computed(() => {
  try {
    return defineAsyncComponent(() =>
      import(`@/components/widgets/${props.definition.component}.vue`)
    )
  } catch (error) {
    console.error('Failed to load widget:', props.definition.component, error)
    return null
  }
})

function handleRemove() {
  if (!props.definition.removable) {
    console.warn('Widget is not removable:', props.definition.id)
    return
  }

  if (confirm(`Remove widget "${props.definition.title}"?`)) {
    emit('remove')
  }
}

function handleAction(action: string, payload?: any) {
  emit('action', action, payload)
}
</script>

<template>
  <div class="widget-wrapper">
    <!-- Title Bar (drag handle) -->
    <div class="widget-header">
      <span class="widget-title">{{ definition.title }}</span>

      <div class="widget-actions">
        <button
          v-if="editMode && !definition.required"
          @click="handleRemove"
          class="widget-btn"
          title="Remove widget"
        >
          <X :size="14" />
        </button>
      </div>
    </div>

    <!-- Widget Content -->
    <div class="widget-content">
      <Suspense>
        <component
          v-if="widgetComponent"
          :is="widgetComponent"
          :context="context"
          @action="handleAction"
        />

        <template #fallback>
          <div class="widget-loading">Loading...</div>
        </template>
      </Suspense>

      <div v-if="!widgetComponent" class="widget-error">
        <p>Widget not found: {{ definition.component }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
  cursor: move; /* Drag handle indicator */
  flex-shrink: 0;
  min-height: 32px;
}

.widget-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  user-select: none;
}

.widget-actions {
  display: flex;
  gap: var(--space-1);
}

.widget-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.widget-btn:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.widget-content {
  flex: 1;
  overflow: auto;
  padding: var(--space-3);
}

.widget-loading,
.widget-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.widget-error {
  color: var(--color-danger);
  text-align: center;
}
</style>
