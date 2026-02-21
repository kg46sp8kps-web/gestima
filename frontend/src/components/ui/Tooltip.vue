<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { TOOLTIP_DELAY_MS } from '@/constants/ui'

interface Props {
  text: string
  delay?: number // Default from TOOLTIP_DELAY_MS constant
}

const props = withDefaults(defineProps<Props>(), {
  delay: TOOLTIP_DELAY_MS
})

const showTooltip = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
let timeoutId: ReturnType<typeof setTimeout> | null = null

function handleMouseEnter(event: MouseEvent) {
  // Save mouse position BEFORE setTimeout (event becomes null after handler)
  const mouseX = event.clientX
  const mouseY = event.clientY

  timeoutId = setTimeout(() => {
    // Position tooltip below cursor (with offset to avoid overlap)
    tooltipX.value = mouseX
    tooltipY.value = mouseY + 20
    showTooltip.value = true
  }, props.delay)
}

function handleMouseLeave() {
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
  showTooltip.value = false
}

onUnmounted(() => {
  if (timeoutId) {
    clearTimeout(timeoutId)
  }
})
</script>

<template>
  <div
    class="tooltip-wrapper"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <slot></slot>

    <Teleport to="body">
      <Transition name="tooltip-fade">
        <div
          v-if="showTooltip"
          class="tooltip"
          :style="{
            left: tooltipX + 'px',
            top: tooltipY + 'px'
          }"
        >
          {{ text }}
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.tooltip-wrapper {
  display: inline-flex;
}
</style>

<style>
/* Global styles for teleported tooltip */
.tooltip {
  position: fixed;
  transform: translateX(-50%);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  white-space: nowrap;
  pointer-events: none;
  z-index: 10005;
  box-shadow: var(--shadow-md);
}

.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
}
</style>
