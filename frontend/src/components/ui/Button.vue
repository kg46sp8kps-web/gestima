<script setup lang="ts">
import Spinner from './Spinner.vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}
withDefaults(defineProps<Props>(), {
  variant: 'secondary',
  size: 'md',
  loading: false,
  disabled: false,
  type: 'button',
})

defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="['btn', `btn-${variant}`, `btn-sz-${size}`, { 'btn-loading': loading }]"
    data-testid="button"
    @click="$emit('click', $event)"
  >
    <Spinner v-if="loading" size="sm" :inline="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border-radius: var(--rs);
  font-family: var(--font);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms var(--ease);
  white-space: nowrap;
  letter-spacing: 0.02em;
}
.btn:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Sizes */
.btn-sz-md { height: 26px; padding: 0 10px; font-size: var(--fsx); }
.btn-sz-sm { height: 24px; padding: 0 8px; font-size: var(--fsl); }

/* Variants */
.btn-primary { border: 1px solid var(--red); color: var(--red); }
.btn-primary:hover:not(:disabled) { background: var(--red-10); box-shadow: 0 0 0 1px var(--red); }

.btn-secondary { border: 1px solid var(--b3); color: var(--t2); }
.btn-secondary:hover:not(:disabled) { background: var(--b1); border-color: var(--b3); color: var(--t1); }

.btn-danger { border: 1px solid var(--err); color: var(--err); }
.btn-danger:hover:not(:disabled) { background: rgba(248,113,113,0.1); }

.btn-ghost { border: 1px solid transparent; color: var(--t3); }
.btn-ghost:hover:not(:disabled) { background: var(--b1); color: var(--t1); }
</style>
