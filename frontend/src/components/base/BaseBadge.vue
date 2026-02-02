<script setup lang="ts">
/**
 * BaseBadge - Status badge component
 *
 * @example
 * <BaseBadge variant="success">Active</BaseBadge>
 * <BaseBadge variant="danger">Error</BaseBadge>
 */

interface Props {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info'
  size?: 'sm' | 'md'
}

withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md'
})
</script>

<template>
  <span
    class="base-badge"
    :class="[
      `base-badge--${variant}`,
      `base-badge--${size}`
    ]"
  >
    <slot />
  </span>
</template>

<style scoped>
.base-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

/* Sizes */
.base-badge--sm {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
}

.base-badge--md {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
}

/* Variants */
.base-badge--primary {
  background: var(--color-primary);
  color: white;
}

.base-badge--secondary {
  background: var(--color-secondary);
  color: white;
}

.base-badge--success {
  background: var(--color-success);
  color: white;
}

.base-badge--danger {
  background: var(--color-danger);
  color: white;
}

.base-badge--warning {
  background: var(--color-warning);
  color: white;
}

.base-badge--info {
  background: var(--color-info);
  color: white;
}
</style>
