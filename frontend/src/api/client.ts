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

function attachResponseInterceptor(client: typeof apiClient) {
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (!error.response) return Promise.reject(error)

      const { status, data } = error.response
      const detail: string = data?.detail ?? 'Neznámá chyba'

      if (status === 401) {
        // Don't redirect for login/pin-login attempts or operator terminal
        const url = error.config?.url ?? ''
        const isLoginAttempt = url.includes('/auth/login') || url.includes('/auth/pin-login') || url.includes('/auth/me')
        const isOperatorPage = window.location.pathname.startsWith('/operator')
        if (!isLoginAttempt && !isOperatorPage && window.location.pathname !== '/login') {
          window.location.href = '/login'
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
