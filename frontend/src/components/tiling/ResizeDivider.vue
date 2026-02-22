<script setup lang="ts">
/**
 * ResizeDivider — drag handle between panels for resizing columns
 * Emits resize delta on drag, double-click to reset
 */

import { ref } from 'vue'

interface Props {
  direction?: 'vertical' | 'horizontal'
}

withDefaults(defineProps<Props>(), {
  direction: 'vertical',
})

const emit = defineEmits<{
  'resize': [delta: number]
  'reset': []
}>()

const isDragging = ref(false)
let startPos = 0

function handleMouseDown(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true
  startPos = e.clientX

  const onMove = (moveEvent: MouseEvent) => {
    const delta = moveEvent.clientX - startPos
    if (Math.abs(delta) > 1) {
      emit('resize', delta)
      startPos = moveEvent.clientX
    }
  }

  const onUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function handleDoubleClick() {
  emit('reset')
}
</script>

<template>
  <div
    class="resize-divider"
    :class="[direction, { dragging: isDragging }]"
    @mousedown="handleMouseDown"
    @dblclick="handleDoubleClick"
    data-testid="resize-divider"
  >
    <div class="divider-line" />
  </div>
</template>

<style scoped>
.resize-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.resize-divider.vertical {
  width: 5px;
  cursor: col-resize;
}

.resize-divider.horizontal {
  height: 5px;
  cursor: row-resize;
}

.divider-line {
  border-radius: 1px;
  transition: background 0.1s;
}

.vertical .divider-line {
  width: 1px;
  height: 100%;
  background: var(--b1);
}

.horizontal .divider-line {
  height: 1px;
  width: 100%;
  background: var(--b1);
}

.resize-divider:hover .divider-line,
.resize-divider.dragging .divider-line {
  background: var(--b3);
}

.vertical:hover .divider-line,
.vertical.dragging .divider-line {
  width: 2px;
}

.horizontal:hover .divider-line,
.horizontal.dragging .divider-line {
  height: 2px;
}
</style>
