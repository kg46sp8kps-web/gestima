<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  text: string
  delay?: number
}
withDefaults(defineProps<Props>(), {
  delay: 400,
})

const visible = ref(false)
const x = ref(0)
const y = ref(0)
let timer: ReturnType<typeof setTimeout>

function onEnter(e: MouseEvent) {
  timer = setTimeout(() => {
    x.value = e.clientX
    y.value = e.clientY
    visible.value = true
  }, 400)
}

function onMove(e: MouseEvent) {
  x.value = e.clientX
  y.value = e.clientY
}

function onLeave() {
  clearTimeout(timer)
  visible.value = false
}
</script>

<template>
  <span
    class="tooltip-trigger"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <slot />
    <Teleport to="body">
      <div
        v-if="visible"
        class="tooltip"
        :style="{ left: x + 10 + 'px', top: y + 14 + 'px' }"
      >
        {{ text }}
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.tooltip-trigger {
  display: inline-flex;
  align-items: center;
}
</style>

<style>
.tooltip {
  position: fixed;
  z-index: 9000;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  padding: 4px 8px;
  font-size: var(--fsl);
  color: var(--t1);
  pointer-events: none;
  white-space: nowrap;
  max-width: 280px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
</style>
