import { onMounted, onUnmounted } from 'vue'

export interface Shortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: (event: KeyboardEvent) => void
  description?: string
}

const globalShortcuts: Map<string, Shortcut> = new Map()

function getKey(shortcut: Shortcut): string {
  const parts: string[] = []
  if (shortcut.ctrl) parts.push('ctrl')
  if (shortcut.shift) parts.push('shift')
  if (shortcut.alt) parts.push('alt')
  if (shortcut.meta) parts.push('meta')
  parts.push(shortcut.key.toLowerCase())
  return parts.join('+')
}

function handleKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    // Allow Escape to propagate from inputs
    if (event.key !== 'Escape') return
  }

  const parts: string[] = []
  if (event.ctrlKey) parts.push('ctrl')
  if (event.shiftKey) parts.push('shift')
  if (event.altKey) parts.push('alt')
  if (event.metaKey) parts.push('meta')
  parts.push(event.key.toLowerCase())
  const key = parts.join('+')

  const shortcut = globalShortcuts.get(key)
  if (shortcut) {
    event.preventDefault()
    shortcut.handler(event)
  }
}

export function useKeyboardShortcuts() {
  const localKeys: string[] = []

  onMounted(() => {
    if (globalShortcuts.size === 0) {
      window.addEventListener('keydown', handleKeydown)
    }
  })

  onUnmounted(() => {
    localKeys.forEach((k) => globalShortcuts.delete(k))
    if (globalShortcuts.size === 0) {
      window.removeEventListener('keydown', handleKeydown)
    }
  })

  function registerShortcut(shortcut: Shortcut) {
    const key = getKey(shortcut)
    globalShortcuts.set(key, shortcut)
    localKeys.push(key)
  }

  function unregisterAll() {
    localKeys.forEach((k) => globalShortcuts.delete(k))
    localKeys.length = 0
  }

  return { registerShortcut, unregisterAll }
}
