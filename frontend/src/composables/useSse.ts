/**
 * Global SSE (Server-Sent Events) composable.
 *
 * Singleton EventSource na /api/events/stream.
 * Komponenty se přihlásí přes `onSseEvent(type, callback)`.
 * Auto-reconnect při výpadku, auto-cleanup při unmountu.
 */

import { onUnmounted } from 'vue'

type SseCallback = (data: unknown) => void

const listeners = new Map<string, Set<SseCallback>>()
let source: EventSource | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function ensureConnection() {
  if (source && source.readyState !== EventSource.CLOSED) return

  source = new EventSource('/api/events/stream')

  source.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      const type = msg.type as string
      const cbs = listeners.get(type)
      if (cbs) {
        for (const cb of cbs) cb(msg)
      }
    } catch { /* ignore parse errors */ }
  }

  source.onerror = () => {
    source?.close()
    source = null
    // Reconnect po 3s
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        if (listeners.size > 0) ensureConnection()
      }, 3000)
    }
  }
}

/**
 * Přihlásit se k SSE eventu. Auto-cleanup při onUnmounted.
 *
 * @example
 * onSseEvent('tier_change', (data) => {
 *   // data = { type: 'tier_change', job: '...', suffix: '0', tier: 'hot' }
 * })
 */
export function onSseEvent(type: string, callback: SseCallback) {
  if (!listeners.has(type)) listeners.set(type, new Set())
  listeners.get(type)!.add(callback)
  ensureConnection()

  // Auto-cleanup při unmountu komponenty
  onUnmounted(() => {
    const set = listeners.get(type)
    if (set) {
      set.delete(callback)
      if (set.size === 0) listeners.delete(type)
    }
    // Zavřít connection pokud nikdo neposlouchá
    if (listeners.size === 0 && source) {
      source.close()
      source = null
    }
  })
}
