<script setup lang="ts">
/**
 * Smooth Transition Wrapper
 * Subtle, fast transitions (150ms = responsive feel!)
 */

interface Props {
  name?: 'fade' | 'slide' | 'scale';
  duration?: number; // ms
  mode?: 'in-out' | 'out-in' | 'default';
}

const props = withDefaults(defineProps<Props>(), {
  name: 'fade',
  duration: 150,
  mode: 'default'
});
</script>

<template>
  <Transition
    :name="name"
    :mode="mode"
    :duration="duration"
  >
    <slot />
  </Transition>
</template>

<style>
/* ============================================================================
   FADE (most common, very subtle)
   ============================================================================ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ============================================================================
   SLIDE (panels, workspace modules)
   ============================================================================ */
.slide-enter-active,
.slide-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0, 0.2, 1),
              opacity 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-enter-from {
  transform: translateX(20px);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(-20px);
  opacity: 0;
}

/* ============================================================================
   SCALE (subtle pop, modals)
   ============================================================================ */
.scale-enter-active,
.scale-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0, 0.2, 1),
              opacity 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.scale-enter-from,
.scale-leave-to {
  transform: scale(0.97);
  opacity: 0;
}

/* ============================================================================
   LIST TRANSITIONS (for v-for items)
   ============================================================================ */
.list-enter-active,
.list-leave-active {
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Stagger items */
.list-move {
  transition: transform 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ============================================================================
   REDUCED MOTION SUPPORT
   ============================================================================ */
@media (prefers-reduced-motion: reduce) {
  .fade-enter-active,
  .fade-leave-active,
  .slide-enter-active,
  .slide-leave-active,
  .scale-enter-active,
  .scale-leave-active,
  .list-enter-active,
  .list-leave-active {
    transition: none;
    animation: none;
  }

  .slide-enter-from,
  .slide-leave-to,
  .scale-enter-from,
  .scale-leave-to,
  .list-enter-from,
  .list-leave-to {
    transform: none;
  }
}
</style>
