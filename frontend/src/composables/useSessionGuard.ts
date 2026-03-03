/**
 * Session guard — event-driven session validation.
 *
 * NO periodic polling. Session validity is detected by:
 * 1. SSE connection failures → auth check in useSse.ts
 * 2. 401 on any API call → interceptor in client.ts
 * 3. Tab visibility change → one-time /auth/me check when user returns
 *
 * Usage: call once in App.vue.
 */

import { onMounted, onUnmounted } from 'vue'

function getLoginPath(): string {
  const p = window.location.pathname
  return p.startsWith('/terminal') ? '/terminal/login' : '/login'
}

function isOnLoginPage(): boolean {
  const p = window.location.pathname
  return p === '/login' || p === '/terminal/login'
}

export function useSessionGuard() {
  let checking = false

  async function checkSession() {
    if (checking || isOnLoginPage()) return
    checking = true
    try {
      const resp = await fetch('/api/auth/me', { credentials: 'include' })
      if (resp.status === 401) {
        window.location.href = getLoginPath()
      }
    } catch {
      // Network error on visibility change — server might be down.
      // Don't redirect immediately; SSE reconnect will handle it.
    } finally {
      checking = false
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // User returned to tab — verify session is still alive
      checkSession()
    }
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })
}
