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
  gap: 6px;
  font-family: var(--font);
  font-weight: 500;
  border-radius: var(--r);
  border: 1px solid transparent; /* Subtle borders */
  cursor: pointer;
  transition: all 100ms var(--ease);
  white-space: nowrap;
  user-select: none;
}

.btn:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* === SIZES === */
.btn-sm {
  padding: 4px 6px;
  font-size: var(--fs);
  height: 32px;
}

.btn-md {
  padding: 4px var(--pad);
  font-size: var(--fs);
  height: 36px;
}

.btn-lg {
  padding: 6px 12px;
  font-size: var(--fs);
  height: 44px;
}

/* === VARIANTS === */

/* Primary - Ghost with brand accent on hover */
.btn-primary {
  background: transparent;
  color: var(--t2);
  border-color: var(--b2);
}

.btn-primary:hover:not(:disabled) {
  background: var(--red-10);
  border-color: var(--red);
  color: rgba(229, 57, 53, 0.7);
}

.btn-primary:active:not(:disabled) {
  background: var(--red-20);
  border-color: var(--red);
  color: rgba(229, 57, 53, 0.7);
  transform: translateY(1px);
}

/* Secondary */
.btn-secondary {
  background: var(--raised);
  color: var(--t2);
  border-color: var(--b2);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--b1);
  border-color: var(--b3);
}

/* Danger - Ghost with red accent on hover */
.btn-danger {
  background: transparent;
  color: var(--t2);
  border-color: var(--b2);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(248,113,113,0.15);
  border-color: var(--err);
  color: var(--err);
}

/* Ghost */
.btn-ghost {
  background: transparent;
  color: var(--t3);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--b1);
  color: var(--t2);
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
  color: rgba(229, 57, 53, 0.7);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
