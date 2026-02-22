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
  gap: 4px;
}

.mode-btn {
  padding: 4px var(--pad);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--surface);
  color: var(--t3);
  font-size: var(--fs);
  font-weight: 600;
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.mode-btn:hover:not(:disabled) {
  background: var(--b1);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-btn.active {
  color: white;
}

.mode-btn.mode-low.active {
  background: var(--ok);
  border-color: var(--ok);
}

.mode-btn.mode-mid.active {
  background: var(--warn);
  border-color: var(--warn);
}

.mode-btn.mode-high.active {
  background: var(--err);
  border-color: var(--err);
}
</style>
