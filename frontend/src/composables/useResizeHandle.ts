import { ref, onUnmounted } from 'vue'

/** Draggable resize handle for panel splits */
export function useResizeHandle(
  direction: 'horizontal' | 'vertical',
  options: {
    min?: number
    max?: number
    initial?: number
    storageKey?: string
  } = {},
) {
  const { min = 150, max = 2000, initial = 300, storageKey } = options

  const savedSize = storageKey ? Number(localStorage.getItem(storageKey)) || initial : initial
  const size = ref(savedSize)
  const isDragging = ref(false)

  let startPos = 0
  let startSize = 0

  function startResize(event: MouseEvent) {
    isDragging.value = true
    startPos = direction === 'horizontal' ? event.clientX : event.clientY
    startSize = size.value
    event.preventDefault()

    const onMove = (e: MouseEvent) => {
      const delta =
        (direction === 'horizontal' ? e.clientX : e.clientY) - startPos
      const newSize = Math.min(max, Math.max(min, startSize + delta))
      size.value = newSize
      if (storageKey) localStorage.setItem(storageKey, String(newSize))
    }

    const onUp = () => {
      isDragging.value = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  function resetSize() {
    size.value = initial
    if (storageKey) localStorage.removeItem(storageKey)
  }

  onUnmounted(() => {
    // cleanup handled inside startResize closure
  })

  return { size, isDragging, startResize, resetSize }
}
