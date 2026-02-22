/** Base API error shape from FastAPI */
export interface ApiError {
  detail: string
}

/** Pagination params */
export interface PaginationParams {
  skip?: number
  limit?: number
}

/** Paginated response wrapper */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

/** Custom error classes for typed error handling */
export class OptimisticLockError extends Error {
  constructor(message = 'Data byla změněna jiným uživatelem. Obnovte stránku.') {
    super(message)
    this.name = 'OptimisticLockError'
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ValidationError'
  }
}

export class NotFoundError extends Error {
  constructor(message = 'Záznam nebyl nalezen.') {
    super(message)
    this.name = 'NotFoundError'
  }
}
