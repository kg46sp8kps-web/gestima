import { ref, watch, onUnmounted } from 'vue'
import type { Ref } from 'vue'

/**
 * Shared resize-drag logic for split-panel tile modules (catalog, quotes, etc.).
 *
 * @param layoutMode  reactive 'vertical' | 'horizontal' — determines drag axis
 * @param containerRef  ref to the root element of the split container
 * @param defaultPct  initial split percentage (default 40)
 */
export function useSplitResize(
  layoutMode: Ref<'vertical' | 'horizontal'>,
  containerRef: Ref<HTMLElement | null>,
  defaultPct = 40,
) {
  const splitPct = ref(defaultPct)
  const isDragging = ref(false)

  // Reset split when layout orientation changes
  watch(layoutMode, () => { splitPct.value = defaultPct })

  let cleanup: (() => void) | null = null

  function startResize(e: MouseEvent) {
    isDragging.value = true
    const startPct = splitPct.value
    const startPos = layoutMode.value === 'vertical' ? e.clientX : e.clientY

    function onMove(ev: MouseEvent) {
      const el = containerRef.value
      if (!el) return
      const total = layoutMode.value === 'vertical' ? el.offsetWidth : el.offsetHeight
      if (total === 0) return
      const pos = layoutMode.value === 'vertical' ? ev.clientX : ev.clientY
      const delta = ((pos - startPos) / total) * 100
      splitPct.value = Math.min(75, Math.max(20, startPct + delta))
    }

    function onUp() {
      isDragging.value = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      cleanup = null
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    cleanup = () => {
      isDragging.value = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }

  onUnmounted(() => cleanup?.())

  return { splitPct, isDragging, startResize }
}
