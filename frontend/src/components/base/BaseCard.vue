<script setup lang="ts">
/**
 * BaseCard - Konsistentní card container
 *
 * Používá design system spacing a nikdy se "neusekne"
 *
 * Props:
 * - padding: 'none' | 'sm' | 'md' | 'lg' (default: 'md')
 * - noPadding: boolean (shortcut for padding="none")
 *
 * @example
 * <BaseCard padding="md">
 *   <template #header>Title</template>
 *   <p>Content here</p>
 * </BaseCard>
 */

interface Props {
  padding?: 'none' | 'sm' | 'md' | 'lg'
  noPadding?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  padding: 'md',
  noPadding: false
})

const paddingValue = props.noPadding ? 'none' : props.padding
</script>

<template>
  <div class="base-card" :data-padding="paddingValue">
    <div v-if="$slots.header" class="base-card__header">
      <slot name="header" />
    </div>

    <div class="base-card__content">
      <slot />
    </div>

    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
/**
 * DŮLEŽITÉ ANTI-PATTERN PREVENCE:
 *
 * ❌ NIKDY: height: 80px, min-height: 100px, max-height: 200px
 * ✅ VŽDY: height: 100%, flex: 1, overflow: auto (pokud potřeba)
 *
 * Widget má 100% výšku od WidgetWrapper → BaseCard musí být fluid!
 */

.base-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden; /* Prevent content overflow */
}

/* Padding variants */
.base-card[data-padding="none"] .base-card__content {
  padding: 0;
}

.base-card[data-padding="sm"] .base-card__content {
  padding: var(--space-2);
}

.base-card[data-padding="md"] .base-card__content {
  padding: var(--space-3);
}

.base-card[data-padding="lg"] .base-card__content {
  padding: var(--space-4);
}

/* Header */
.base-card__header {
  flex-shrink: 0;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

/* Content - KRITICKÉ: flex: 1 pro zabrání celé dostupné výšky */
.base-card__content {
  flex: 1;
  overflow: auto; /* Auto scroll if content overflows */
  /* Padding set via data-padding attribute */
}

/* Footer */
.base-card__footer {
  flex-shrink: 0;
  padding: var(--space-3);
  border-top: 1px solid var(--border-default);
}
</style>
