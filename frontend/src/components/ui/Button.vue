<template>
  <button
    :class="buttonClasses"
    :disabled="disabled || loading"
    :type="type"
    @click="handleClick"
  >
    <span v-if="loading" class="btn-spinner"></span>
    <slot v-else></slot>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  type: 'button'
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const buttonClasses = computed(() => [
  'btn',
  `btn-${props.variant}`,
  `btn-${props.size}`,
  { 'btn-loading': props.loading }
]);

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event);
  }
};
</script>

<style scoped>
/* === BASE BUTTON (Refined & Subtle) === */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-sans);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  border: 1px solid transparent; /* Subtle borders */
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
  user-select: none;
}

.btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* === SIZES === */
.btn-sm {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  height: 32px;
}

.btn-md {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  height: 36px;
}

.btn-lg {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  height: 44px;
}

/* === VARIANTS === */

/* Primary - Ghost with brand accent on hover */
.btn-primary {
  background: transparent;
  color: var(--text-body);
  border-color: var(--border-default);
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.btn-primary:active:not(:disabled) {
  background: var(--brand-muted);
  border-color: var(--brand);
  color: var(--brand-text);
  transform: translateY(1px);
}

/* Secondary */
.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-body);
  border-color: var(--border-default);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

/* Danger - Ghost with red accent on hover */
.btn-danger {
  background: transparent;
  color: var(--text-body);
  border-color: var(--border-default);
}

.btn-danger:hover:not(:disabled) {
  background: var(--palette-danger-light);
  border-color: var(--status-error);
  color: var(--status-error);
}

/* Ghost */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--state-hover);
  color: var(--text-body);
}

/* === LOADING STATE === */
.btn-loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}

.btn-spinner {
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 0.6s linear infinite;
  color: var(--brand-text);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
