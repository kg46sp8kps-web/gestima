import { onMounted, onUnmounted, type Ref } from 'vue'

/**
 * Detects horizontal swipe gestures on a container element.
 * Distinguishes horizontal swipe from vertical scroll (|dx| > |dy| * 1.5).
 * Uses passive touch listeners.
 */
export function useSwipeNavigation(
  containerRef: Ref<HTMLElement | null>,
  callbacks: {
    onSwipeLeft: () => void
    onSwipeRight: () => void
  },
  threshold = 50,
) {
  let startX = 0
  let startY = 0
  let tracking = false

  function onTouchStart(e: TouchEvent) {
    if (e.touches.length !== 1) return
    startX = e.touches[0]!.clientX
    startY = e.touches[0]!.clientY
    tracking = true
  }

  function onTouchEnd(e: TouchEvent) {
    if (!tracking) return
    tracking = false
    if (e.changedTouches.length === 0) return

    const dx = e.changedTouches[0]!.clientX - startX
    const dy = e.changedTouches[0]!.clientY - startY

    // Must be a deliberate horizontal swipe
    if (Math.abs(dx) < threshold) return
    if (Math.abs(dx) < Math.abs(dy) * 1.5) return

    if (dx < 0) callbacks.onSwipeLeft()
    else callbacks.onSwipeRight()
  }

  onMounted(() => {
    const el = containerRef.value
    if (!el) return
    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchend', onTouchEnd, { passive: true })
  })

  onUnmounted(() => {
    const el = containerRef.value
    if (!el) return
    el.removeEventListener('touchstart', onTouchStart)
    el.removeEventListener('touchend', onTouchEnd)
  })
}
