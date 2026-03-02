export type UserRole = 'admin' | 'operator' | 'viewer' | 'mistr'

/** Mirrors backend UserResponse schema */
export interface User {
  id: number
  username: string
  email: string | null
  role: UserRole
  is_active: boolean
  has_pin: boolean
  infor_emp_num: string | null
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

/** Extended response from POST /auth/pin-login — includes user data to skip getMe() */
export interface PinLoginResponse extends TokenResponse {
  user: User
}
