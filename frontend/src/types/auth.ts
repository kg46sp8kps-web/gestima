export type UserRole = 'admin' | 'operator' | 'viewer'

/** Mirrors backend UserResponse schema */
export interface User {
  id: number
  username: string
  email: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

/** Mirrors backend TokenResponse — returned by POST /auth/login */
export interface TokenResponse {
  status: string
  username: string
  role: UserRole
}
