/**
 * GESTIMA API Types
 */

export interface ApiError {
  message: string
  status: number
  data?: any
}

export interface OptimisticLockError extends ApiError {
  status: 409
}

export interface ValidationError extends ApiError {
  status: 422
}
