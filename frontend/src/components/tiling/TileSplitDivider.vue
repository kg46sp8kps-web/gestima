<script setup lang="ts">
import { ref } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'

interface Props {
  splitId: string
  direction: 'horizontal' | 'vertical'
  ratio: number
}

const props = defineProps<Props>()
const ws = useWorkspaceStore()
const active = ref(false)

function startResize(e: MouseEvent) {
  active.value = true
  const el = (e.target as HTMLElement).parentElement!
  const rect = el.getBoundingClientRect()

  const onMove = (ev: MouseEvent) => {
    let ratio: number
    if (props.direction === 'horizontal') {
      ratio = (ev.clientX - rect.left) / rect.width
    } else {
      ratio = (ev.clientY - rect.top) / rect.height
    }
    ws.setSplitRatio(props.splitId, Math.min(0.85, Math.max(0.15, ratio)))
  }

  const onUp = () => {
    active.value = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
  e.preventDefault()
}
</script>

<template>
  <div
    :class="['split-divider', direction === 'horizontal' ? 'h' : 'v', { active }]"
    @mousedown="startResize"
  />
</template>

<style scoped>
.split-divider {
  flex-shrink: 0;
  position: relative;
  z-index: 6;
  background: transparent;
  transition: background 0.12s;
}
.split-divider.h {
  width: 5px;
  cursor: col-resize;
}
.split-divider.v {
  height: 5px;
  cursor: row-resize;
}
.split-divider::after {
  content: '';
  position: absolute;
  background: var(--b3);
  border-radius: 99px;
  opacity: 0;
  transition: opacity 0.12s;
}
.split-divider.h::after {
  top: 20%;
  bottom: 20%;
  left: 50%;
  transform: translateX(-50%);
  width: 1px;
}
.split-divider.v::after {
  left: 20%;
  right: 20%;
  top: 50%;
  transform: translateY(-50%);
  height: 1px;
}
.split-divider:hover::after { opacity: 1; }
.split-divider:hover { background: var(--input-bg); }
.split-divider.active { background: var(--red-10); }
.split-divider.active::after { opacity: 1; background: var(--red); }
</style>
