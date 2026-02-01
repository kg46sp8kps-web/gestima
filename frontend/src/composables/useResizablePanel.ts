/**
 * useResizablePanel - Composable for resizable split-pane functionality
 *
 * Features:
 * - Drag to resize panel width
 * - Min/max width constraints
 * - localStorage persistence
 * - Visual feedback (hover, dragging states)
 * - Prevents text selection during drag
 */

import { ref, onMounted } from 'vue'

export interface ResizablePanelOptions {
  storageKey: string
  defaultWidth?: number
  minWidth?: number
  maxWidth?: number
}

export function useResizablePanel(options: ResizablePanelOptions) {
  const {
    storageKey,
    defaultWidth = 320,
    minWidth = 250,
    maxWidth = 600
  } = options

  const panelWidth = ref(defaultWidth)
  const isDragging = ref(false)

  // Load from localStorage on mount
  onMounted(() => {
    const stored = localStorage.getItem(storageKey)
    if (stored) {
      const width = parseInt(stored, 10)
      if (!isNaN(width) && width >= minWidth && width <= maxWidth) {
        panelWidth.value = width
      }
    }
  })

  function startResize(event: MouseEvent) {
    event.preventDefault()
    isDragging.value = true

    const startX = event.clientX
    const startWidth = panelWidth.value

    // Disable text selection during drag
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'

    function onMouseMove(e: MouseEvent) {
      const delta = e.clientX - startX
      const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + delta))
      panelWidth.value = newWidth
    }

    function onMouseUp() {
      isDragging.value = false

      // Re-enable text selection
      document.body.style.userSelect = ''
      document.body.style.cursor = ''

      // Save to localStorage
      localStorage.setItem(storageKey, panelWidth.value.toString())

      // Cleanup listeners
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  return {
    panelWidth,
    isDragging,
    startResize
  }
}
