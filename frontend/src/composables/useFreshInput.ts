/**
 * useFreshInput - Input Fresh Pattern
 *
 * Replicated from Alpine.js edit.html:
 * @focus="$el.dataset.fresh = 'true'"
 * @keydown="if(fresh) { $el.value = ''; fresh = false }"
 *
 * Behavior:
 * - When user focuses on number input, mark it as "fresh"
 * - On first keypress, clear the value (user can type new number from scratch)
 * - After first keypress, behaves normally
 *
 * Usage:
 * <input
 *   type="number"
 *   v-model.number="value"
 *   @focus="onFocus"
 *   @keydown="onKeydown"
 *   @blur="onBlur"
 * />
 */

import { ref } from 'vue'

export function useFreshInput() {
  const isFresh = ref(false)

  function onFocus(event: FocusEvent) {
    isFresh.value = true
  }

  function onKeydown(event: KeyboardEvent) {
    if (!isFresh.value) return

    const target = event.target as HTMLInputElement

    // Check if it's a regular character (not Ctrl/Meta combos, not special keys)
    if (
      event.key.length === 1 &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.altKey
    ) {
      // Clear the input value
      target.value = ''
      isFresh.value = false
    }
  }

  function onBlur() {
    isFresh.value = false
  }

  return {
    isFresh,
    onFocus,
    onKeydown,
    onBlur
  }
}
