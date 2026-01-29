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

// Create axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true, // CRITICAL: HttpOnly cookies
  timeout: 30000, // 30s
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Log request in dev
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log response in dev
    if (import.meta.env.DEV) {
      console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} → ${response.status}`)
    }
    return response
  },
  (error: AxiosError) => {
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
)

export default apiClient
