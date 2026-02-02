/**
 * useResizeHandle - Composable for drag-to-resize panels
 *
 * Provides standardized resize logic for split-pane layouts.
 * Replaces duplicated resize code across 5+ modules.
 *
 * Features:
 * - Mouse drag to resize
 * - Min/max size constraints
 * - localStorage persistence
 * - Vertical (side-by-side) or horizontal (stacked) support
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 * @example
 * ```typescript
 * const { size, isDragging, startResize } = useResizeHandle({
 *   storageKey: 'my-panel-size',
 *   defaultSize: 320,
 *   minSize: 250,
 *   maxSize: 1000,
 *   vertical: true
 * })
 * ```
 */

import { ref, computed, onMounted, type Ref, type ComputedRef } from 'vue'
import type { ResizeHandleOptions } from '@/types/layout'

interface UseResizeHandleReturn {
  /**
   * Current panel size in pixels
   */
  size: Ref<number>

  /**
   * Is user currently dragging?
   */
  isDragging: Ref<boolean>

  /**
   * Start resize operation (call on mousedown)
   */
  startResize: (event: MouseEvent) => void

  /**
   * Reset to default size
   */
  resetSize: () => void
}

export function useResizeHandle(options: ResizeHandleOptions | ComputedRef<ResizeHandleOptions>): UseResizeHandleReturn {
  // Handle both direct options and computed options
  const opts = computed(() => {
    return 'value' in options ? options.value : options
  })

  const size = ref(opts.value.defaultSize ?? 320)
  const isDragging = ref(false)

  /**
   * Load size from localStorage
   */
  function loadSize() {
    try {
      const stored = localStorage.getItem(opts.value.storageKey)
      if (stored) {
        const parsed = parseInt(stored, 10)
        const minSize = opts.value.minSize ?? 250
        const maxSize = opts.value.maxSize ?? 1000

        if (!isNaN(parsed) && parsed >= minSize && parsed <= maxSize) {
          size.value = parsed
        }
      }
    } catch (error) {
      console.warn('Failed to load resize size:', error)
    }
  }

  /**
   * Save size to localStorage
   */
  function saveSize() {
    try {
      localStorage.setItem(opts.value.storageKey, size.value.toString())
    } catch (error) {
      console.warn('Failed to save resize size:', error)
    }
  }

  /**
   * Start resize operation
   */
  function startResize(event: MouseEvent) {
    event.preventDefault()
    isDragging.value = true

    const vertical = opts.value.vertical ?? true
    const startPos = vertical ? event.clientX : event.clientY
    const startSize = size.value
    const minSize = opts.value.minSize ?? 250
    const maxSize = opts.value.maxSize ?? 1000

    // Disable text selection during drag
    document.body.style.userSelect = 'none'
    document.body.style.cursor = vertical ? 'col-resize' : 'row-resize'

    function onMouseMove(e: MouseEvent) {
      const currentPos = vertical ? e.clientX : e.clientY
      const delta = currentPos - startPos
      const newSize = Math.max(minSize, Math.min(maxSize, startSize + delta))
      size.value = newSize
    }

    function onMouseUp() {
      isDragging.value = false

      // Re-enable text selection
      document.body.style.userSelect = ''
      document.body.style.cursor = ''

      // Save to localStorage
      saveSize()

      // Cleanup listeners
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  /**
   * Reset to default size
   */
  function resetSize() {
    size.value = opts.value.defaultSize ?? 320
    saveSize()
  }

  // Load on mount
  onMounted(() => {
    loadSize()
  })

  return {
    size,
    isDragging,
    startResize,
    resetSize
  }
}
