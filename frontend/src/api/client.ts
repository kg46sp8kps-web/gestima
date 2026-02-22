import axios from 'axios'
import { OptimisticLockError, ValidationError, NotFoundError } from '@/types/api'

/** Regular API client — uses JWT from localStorage */
export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

/** Admin API client — for admin-only endpoints */
export const adminClient = axios.create({
  baseURL: '/admin/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

function attachAuthInterceptor(client: typeof apiClient) {
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (!error.response) return Promise.reject(error)

      const { status, data } = error.response
      const detail: string = data?.detail ?? 'Neznámá chyba'

      if (status === 401) {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
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

attachAuthInterceptor(apiClient)
attachAuthInterceptor(adminClient)

/** Re-export error classes for convenience */
export { OptimisticLockError, ValidationError, NotFoundError }
