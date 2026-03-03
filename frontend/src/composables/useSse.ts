/**
 * Global SSE (Server-Sent Events) composable.
 *
 * Singleton EventSource na /api/events/stream.
 * Komponenty se přihlásí přes `onSseEvent(type, callback)`.
 * Auto-reconnect s backoff při výpadku.
 * Auth check po opakovaném selhání — redirect na login při 401.
 */

import { onUnmounted } from 'vue'

type SseCallback = (data: unknown) => void

const listeners = new Map<string, Set<SseCallback>>()
let source: EventSource | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let consecutiveFailures = 0
const MAX_FAILURES_BEFORE_AUTH_CHECK = 3

function getLoginPath(): string {
  const p = window.location.pathname
  return p.startsWith('/terminal') ? '/terminal/login' : '/login'
}

function isOnLoginPage(): boolean {
  const p = window.location.pathname
  return p === '/login' || p === '/terminal/login'
}

async function checkAuthAndRedirect(): Promise<boolean> {
  if (isOnLoginPage()) return false
  try {
    const resp = await fetch('/api/auth/me', { credentials: 'include' })
    if (resp.status === 401) {
      window.location.href = getLoginPath()
      return true
    }
    return false
  } catch {
    // Network error — server is down, redirect to login
    window.location.href = getLoginPath()
    return true
  }
}

function ensureConnection() {
  if (source && source.readyState !== EventSource.CLOSED) return

  source = new EventSource('/api/events/stream')

  source.onopen = () => {
    consecutiveFailures = 0
  }

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
    consecutiveFailures++

    if (consecutiveFailures >= MAX_FAILURES_BEFORE_AUTH_CHECK) {
      // Check if session is still valid before retrying
      checkAuthAndRedirect().then((redirected) => {
        if (!redirected) {
          // Auth is fine, server might be restarting — reset counter and retry
          consecutiveFailures = 0
          scheduleReconnect()
        }
      })
      return
    }

    scheduleReconnect()
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return
  // Backoff: 3s, 6s, 12s... max 30s
  const delay = Math.min(3000 * Math.pow(2, consecutiveFailures - 1), 30_000)
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    if (listeners.size > 0) ensureConnection()
  }, delay)
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
