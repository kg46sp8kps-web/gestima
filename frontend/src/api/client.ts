/**
 * GESTIMA API Client
 *
 * Centralized Axios instance with interceptors for:
 * - Request/response logging
 * - Global error handling
 * - Loading state management
 * - Auth redirects
 */

import axios, { AxiosError } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { ApiError, OptimisticLockError, ValidationError } from '@/types/api'

// Custom error classes
export class ApiErrorClass extends Error implements ApiError {
  constructor(
    message: string,
    public status: number,
    public data?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class OptimisticLockErrorClass extends ApiErrorClass {
  readonly status: 409 = 409

  constructor(data: Record<string, unknown>) {
    // Use server message if provided, fallback to generic optimistic lock message
    const message = (typeof data?.detail === 'string' ? data.detail : null) || 'Data byla změněna jiným uživatelem'
    super(message, 409, data)
    this.name = 'OptimisticLockError'
  }
}

export class ValidationErrorClass extends ApiErrorClass {
  readonly status: 422 = 422

  constructor(data: Record<string, unknown>) {
    super('Validation failed', 422, data)
    this.name = 'ValidationError'
  }
}

// Create axios instance for regular API routes
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true, // CRITICAL: HttpOnly cookies
  timeout: 30000, // 30s
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Create axios instance for admin routes (different base path)
export const adminClient = axios.create({
  baseURL: '/admin/api',
  withCredentials: true,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Guard against multiple 401 redirects firing at once
let isRedirectingToLogin = false

// Shared interceptor logic
const requestInterceptor = (config: InternalAxiosRequestConfig) => {
  return config
}

const requestErrorInterceptor = (error: unknown) => {
  console.error('[API] Request error:', error)
  return Promise.reject(error)
}

const responseInterceptor = (response: AxiosResponse) => {
  return response
}

const responseErrorInterceptor = (error: AxiosError) => {
  // Network error
  if (!error.response) {
    console.error('[API] Network error:', error.message)
    return Promise.reject(new ApiErrorClass('Chyba připojení k serveru', 0))
  }

  const { status, data } = error.response
  const url = error.config?.url || ''

  // Log error in dev (but skip expected 404s for module-defaults)
  if (import.meta.env.DEV) {
    const isExpected404 = status === 404 && url.includes('/api/module-defaults/')
    if (!isExpected404) {
      console.error(`[API] Error ${status}:`, data)
    }
  }

  // Handle specific status codes
  switch (status) {
    case 401: {
      // Skip redirect for auth endpoints (avoid loops)
      const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/me')
      if (!isAuthEndpoint && !isRedirectingToLogin) {
        isRedirectingToLogin = true
        // Dynamic imports to avoid circular dependencies
        Promise.all([
          import('@/stores/auth'),
          import('@/stores/ui'),
          import('@/router')
        ]).then(([{ useAuthStore }, { useUiStore }, { default: router }]) => {
          useAuthStore().clearAuth()
          useUiStore().showWarning('Session vypršela. Přihlaste se znovu.')
          router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
          // Reset guard after redirect completes
          setTimeout(() => { isRedirectingToLogin = false }, 1000)
        })
      }
      break
    }

    case 403:
      console.warn('[API] Forbidden - insufficient permissions')
      break

    case 404: {
      const isExpectedNotFound = url.includes('/module-defaults/')
      if (!isExpectedNotFound) {
        console.warn('[API] Not found:', url)
      }
      break
    }

    case 409:
      // Optimistic lock conflict
      throw new OptimisticLockErrorClass(data as Record<string, unknown>)

    case 422: {
      // Validation error - log details for debugging
      const responseData = data as Record<string, unknown>
      if (Array.isArray(responseData?.detail)) {
        const details = responseData.detail
        console.error('[API] Validation errors:', details)
        // Format Pydantic errors for better readability
        details.forEach((err: unknown, idx: number) => {
          const error = err as { loc?: string[]; msg?: string }
          console.error(`  [${idx + 1}] ${error.loc?.join('.')} - ${error.msg}`)
        })
      }
      throw new ValidationErrorClass(responseData)
    }

    case 500:
      console.error('[API] Server error')
      break
  }

  // Throw standardized error
  const responseData = data as Record<string, unknown>
  throw new ApiErrorClass(
    (typeof responseData?.detail === 'string' ? responseData.detail : null) || 'Unknown error',
    status,
    responseData
  )
}

// Apply interceptors to apiClient
apiClient.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
apiClient.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

// Apply interceptors to adminClient
adminClient.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
adminClient.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

export default apiClient
