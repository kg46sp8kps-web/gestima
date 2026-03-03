import axios from 'axios'
import { OptimisticLockError, ValidationError, NotFoundError } from '@/types/api'

/** Regular API client — uses HttpOnly cookie for auth (withCredentials) */
export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

/** Admin API client — for admin-only endpoints */
export const adminClient = axios.create({
  baseURL: '/admin/api',
  timeout: 30_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

/** Resolve login redirect path based on current page */
function getLoginPath(): string {
  const p = window.location.pathname
  return p.startsWith('/terminal') ? '/terminal/login' : '/login'
}

/** Is the user currently on a login page? */
function isOnLoginPage(): boolean {
  const p = window.location.pathname
  return p === '/login' || p === '/terminal/login'
}

// Debounce: prevent multiple concurrent redirects
let redirecting = false

function forceRedirectToLogin() {
  if (redirecting || isOnLoginPage()) return
  redirecting = true
  window.location.href = getLoginPath()
}

function attachResponseInterceptor(client: typeof apiClient) {
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (!error.response) {
        // Network error / server unreachable — propagate, session guard handles it
        return Promise.reject(error)
      }

      const { status, data } = error.response
      const detail: string = data?.detail ?? 'Neznámá chyba'

      if (status === 401) {
        const url = error.config?.url ?? ''
        const isLoginAttempt = url.includes('/auth/login') || url.includes('/auth/pin-login') || url.includes('/auth/me')
        if (!isLoginAttempt) {
          forceRedirectToLogin()
        }
        return Promise.reject(new Error('Relace vypršela. Přihlaste se znovu.'))
      }

      if (status === 409 || detail.toLowerCase().includes('version')) {
        return Promise.reject(new OptimisticLockError())
      }

      if (status === 422 || status === 400) {
        return Promise.reject(new ValidationError(detail))
      }

      if (status === 404) {
        return Promise.reject(new NotFoundError(detail))
      }

      return Promise.reject(new Error(detail))
    },
  )
}

attachResponseInterceptor(apiClient)
attachResponseInterceptor(adminClient)

/** Re-export error classes for convenience */
export { OptimisticLockError, ValidationError, NotFoundError }
