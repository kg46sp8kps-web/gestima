<script setup lang="ts">
/**
 * Skeleton loader - prevents content flashing
 * Matches existing GESTIMA style (small, compact)
 */

interface Props {
  width?: string;
  height?: string;
  variant?: 'text' | 'rect' | 'circle' | 'row';
  animated?: boolean;
  count?: number; // For multiple skeletons
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '16px',
  variant: 'rect',
  animated: true,
  count: 1
});
</script>

<template>
  <div class="skeleton-container">
    <div
      v-for="i in count"
      :key="i"
      class="skeleton"
      :class="[
        `skeleton-${variant}`,
        { 'skeleton-animated': animated }
      ]"
      :style="{ width, height }"
      role="status"
      aria-label="Loading"
    />
  </div>
</template>

<style scoped>
.skeleton-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--skeleton-base) 25%,
    var(--skeleton-highlight) 50%,
    var(--skeleton-base) 75%
  );
  background-size: 200% 100%;
  border-radius: var(--radius-sm);
}

.skeleton-animated {
  animation: shimmer 1.5s ease-in-out infinite;
}

/* Text variant - inline, small height */
.skeleton-text {
  height: 1em;
  min-height: 12px;
  border-radius: var(--radius-sm);
}

/* Row variant - table row height (existing: 48px from specs) */
.skeleton-row {
  height: 48px;
  border-radius: 0; /* Rows = no radius */
  border-bottom: 1px solid var(--border-default);
}

/* Circle variant - avatar, icons */
.skeleton-circle {
  border-radius: var(--radius-full);
  width: var(--size, 32px);
  height: var(--size, 32px);
}

/* Shimmer animation (subtle!) */
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Reduce motion support */
@media (prefers-reduced-motion: reduce) {
  .skeleton-animated {
    animation: none;
    opacity: 0.6;
  }
}
</style>
