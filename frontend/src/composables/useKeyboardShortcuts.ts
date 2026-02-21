/**
 * useKeyboardShortcuts.ts — Reusable keyboard shortcut composable
 *
 * BUILDING BLOCK (L-039): Register/unregister keyboard shortcuts with scope awareness.
 * Prevents shortcuts from firing when user is typing in input fields.
 *
 * Usage:
 *   const { registerShortcut, unregisterAll } = useKeyboardShortcuts()
 *   registerShortcut({ key: 'n', ctrl: true, handler: () => addItem() })
 *   // Automatically cleaned up on component unmount
 */
import { onMounted, onBeforeUnmount } from 'vue'

export interface ShortcutConfig {
  /** The key to listen for (e.g. 'n', 'Enter', 'Delete') */
  key: string
  /** Require Ctrl/Cmd modifier */
  ctrl?: boolean
  /** Require Shift modifier */
  shift?: boolean
  /** Require Alt modifier */
  alt?: boolean
  /** Handler function */
  handler: (e: KeyboardEvent) => void
  /** If true, shortcut fires even when focused on input/textarea/select */
  allowInInput?: boolean
}

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export function useKeyboardShortcuts() {
  const shortcuts: ShortcutConfig[] = []

  function handleKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement
    const isInput = INPUT_TAGS.has(target.tagName) || target.isContentEditable

    for (const shortcut of shortcuts) {
      // Check modifiers
      if (shortcut.ctrl && !(e.ctrlKey || e.metaKey)) continue
      if (shortcut.shift && !e.shiftKey) continue
      if (shortcut.alt && !e.altKey) continue

      // Check key (case-insensitive)
      if (e.key.toLowerCase() !== shortcut.key.toLowerCase()) continue

      // Skip if in input and not allowed
      if (isInput && !shortcut.allowInInput) continue

      e.preventDefault()
      e.stopPropagation()
      shortcut.handler(e)
      return
    }
  }

  function registerShortcut(config: ShortcutConfig) {
    shortcuts.push(config)
  }

  function unregisterAll() {
    shortcuts.length = 0
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown, true)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown, true)
    unregisterAll()
  })

  return {
    registerShortcut,
    unregisterAll
  }
}
