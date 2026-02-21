/**
 * v-select-on-focus directive
 *
 * Selects all text in input when focused.
 * Used for number inputs where user typically wants to replace the value.
 *
 * Usage:
 *   <input v-select-on-focus type="number" />
 *   <input v-select-on-focus />
 */
import type { Directive, DirectiveBinding } from 'vue'

interface SelectOnFocusElement extends HTMLInputElement {
  _selectOnFocusHandlers?: {
    mousedown: (e: MouseEvent) => void
    focus: () => void
  }
}

const selectOnFocus: Directive<HTMLInputElement> = {
  mounted(el: SelectOnFocusElement) {
    const handleMouseDown = (e: MouseEvent) => {
      // Always prevent default cursor positioning
      e.preventDefault()

      // Focus if not already focused
      if (document.activeElement !== el) {
        el.focus()
      }

      // Always select all after interaction completes
      requestAnimationFrame(() => {
        el.select()
      })
    }

    const handleFocus = () => {
      // Select all on focus (for keyboard navigation like Tab)
      requestAnimationFrame(() => {
        el.select()
      })
    }

    el.addEventListener('mousedown', handleMouseDown)
    el.addEventListener('focus', handleFocus)

    // Store handlers for cleanup
    el._selectOnFocusHandlers = {
      mousedown: handleMouseDown,
      focus: handleFocus
    }
  },

  unmounted(el: SelectOnFocusElement) {
    const handlers = el._selectOnFocusHandlers
    if (handlers) {
      el.removeEventListener('mousedown', handlers.mousedown)
      el.removeEventListener('focus', handlers.focus)
      delete el._selectOnFocusHandlers
    }
  }
}

export default selectOnFocus
