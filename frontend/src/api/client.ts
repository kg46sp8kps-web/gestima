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
    public data?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class OptimisticLockErrorClass extends ApiErrorClass {
  readonly status: 409 = 409

  constructor(data: any) {
    super('Data byla změněna jiným uživatelem', 409, data)
    this.name = 'OptimisticLockError'
  }
}

export class ValidationErrorClass extends ApiErrorClass {
  readonly status: 422 = 422

  constructor(data: any) {
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

// Shared interceptor logic
const requestInterceptor = (config: InternalAxiosRequestConfig) => {
  // Log request in dev
  if (import.meta.env.DEV) {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
  }
  return config
}

const requestErrorInterceptor = (error: any) => {
  console.error('[API] Request error:', error)
  return Promise.reject(error)
}

const responseInterceptor = (response: AxiosResponse) => {
  // Log response in dev
  if (import.meta.env.DEV) {
    console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} → ${response.status}`)
  }
  return response
}

const responseErrorInterceptor = (error: AxiosError) => {
  // Network error
  if (!error.response) {
    console.error('[API] Network error:', error.message)
    return Promise.reject(new ApiErrorClass('Chyba připojení k serveru', 0))
  }

  const { status, data } = error.response

  // Log error in dev
  if (import.meta.env.DEV) {
    console.error(`[API] Error ${status}:`, data)
  }

  // Handle specific status codes
  switch (status) {
    case 401:
      // Unauthorized - will be handled by router guard
      console.warn('[API] Unauthorized - redirecting to login')
      break

    case 403:
      console.warn('[API] Forbidden - insufficient permissions')
      break

    case 404:
      console.warn('[API] Not found')
      break

    case 409:
      // Optimistic lock conflict
      throw new OptimisticLockErrorClass(data)

    case 422:
      // Validation error
      throw new ValidationErrorClass(data)

    case 500:
      console.error('[API] Server error')
      break
  }

  // Throw standardized error
  throw new ApiErrorClass(
    (data as any)?.detail || 'Unknown error',
    status,
    data
  )
}

// Apply interceptors to apiClient
apiClient.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
apiClient.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

// Apply interceptors to adminClient
adminClient.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
adminClient.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

export default apiClient
