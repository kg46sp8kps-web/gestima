<script setup lang="ts">
/**
 * BaseButton - Reusable button with variants
 *
 * Variants:
 * - primary (red)
 * - secondary (grey)
 * - danger (pink)
 * - success (green)
 * - ghost (transparent)
 *
 * Sizes: sm, md, lg
 *
 * @example
 * <BaseButton variant="primary" size="md" @click="save">Save</BaseButton>
 */

import { computed } from 'vue'
import type { Component } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  icon?: Component
  iconRight?: Component
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false
})

const buttonClasses = computed(() => {
  const base = 'base-button'
  const variant = `base-button--${props.variant}`
  const size = `base-button--${props.size}`
  const loading = props.loading ? 'base-button--loading' : ''
  const disabled = props.disabled ? 'base-button--disabled' : ''

  return [base, variant, size, loading, disabled].filter(Boolean).join(' ')
})

const isDisabled = computed(() => props.disabled || props.loading)
</script>

<template>
  <button
    :class="buttonClasses"
    :disabled="isDisabled"
    type="button"
  >
    <component
      v-if="icon && !loading"
      :is="icon"
      :size="size === 'sm' ? 14 : size === 'lg' ? 20 : 16"
      class="base-button__icon"
    />

    <span v-if="loading" class="base-button__spinner"></span>

    <span class="base-button__content">
      <slot />
    </span>

    <component
      v-if="iconRight && !loading"
      :is="iconRight"
      :size="size === 'sm' ? 14 : size === 'lg' ? 20 : 16"
      class="base-button__icon base-button__icon--right"
    />
  </button>
</template>

<style scoped>
/* Base button */
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-sans);
  font-weight: var(--font-medium);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
  user-select: none;
}

/* Sizes */
.base-button--sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  min-height: 24px;
}

.base-button--md {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  min-height: 32px;
}

.base-button--lg {
  padding: var(--space-3) var(--space-5);
  font-size: var(--text-base);
  min-height: 40px;
}

/* Variants — ALL ghost pattern (DS v4.0 Minimal Dark) */
.base-button--primary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.base-button--primary:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.base-button--secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.base-button--secondary:hover:not(:disabled) {
  background: var(--hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.base-button--danger {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.base-button--danger:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--status-error);
  color: var(--status-error);
}

.base-button--success {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-default);
}

.base-button--success:hover:not(:disabled) {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--status-ok);
  color: var(--status-ok);
}

.base-button--ghost {
  background: transparent;
  color: var(--text-body);
  border: 1px solid transparent;
}

.base-button--ghost:hover:not(:disabled) {
  background: var(--hover);
  border-color: var(--border-default);
  color: var(--text-primary);
}

/* States */
.base-button:disabled,
.base-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-button--loading {
  cursor: wait;
}

/* Icon */
.base-button__icon {
  flex-shrink: 0;
}

.base-button__icon--right {
  order: 2;
}

.base-button__content {
  flex: 0 0 auto;
}

/* Loading spinner */
.base-button__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
