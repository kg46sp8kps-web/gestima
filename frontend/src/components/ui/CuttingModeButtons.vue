<script setup lang="ts">
/**
 * CuttingModeButtons - Generic reusable component
 * BUILDING BLOCKS (L-039): 1× napsat N× použít
 */

import type { CuttingMode } from '@/types/operation'

interface Props {
  mode: CuttingMode
  disabled?: boolean
}

interface Emits {
  (e: 'change', mode: CuttingMode): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<Emits>()
</script>

<template>
  <div class="mode-buttons">
    <button
      @click="emit('change', 'low')"
      :class="{ active: mode === 'low' }"
      class="mode-btn mode-low"
      :disabled="disabled"
      type="button"
    >
      LOW
    </button>
    <button
      @click="emit('change', 'mid')"
      :class="{ active: mode === 'mid' }"
      class="mode-btn mode-mid"
      :disabled="disabled"
      type="button"
    >
      MID
    </button>
    <button
      @click="emit('change', 'high')"
      :class="{ active: mode === 'high' }"
      class="mode-btn mode-high"
      :disabled="disabled"
      type="button"
    >
      HIGH
    </button>
  </div>
</template>

<style scoped>
.mode-buttons {
  display: flex;
  gap: var(--space-1);
}

.mode-btn {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: var(--transition-fast);
}

.mode-btn:hover:not(:disabled) {
  background: var(--state-hover);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-btn.active {
  color: white;
}

.mode-btn.mode-low.active {
  background: var(--color-success);
  border-color: var(--color-success);
}

.mode-btn.mode-mid.active {
  background: var(--color-warning);
  border-color: var(--color-warning);
}

.mode-btn.mode-high.active {
  background: var(--color-danger);
  border-color: var(--color-danger);
}
</style>
