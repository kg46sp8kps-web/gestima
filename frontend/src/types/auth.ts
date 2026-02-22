export type UserRole = 'admin' | 'operator' | 'viewer'

export interface User {
  id: number
  username: string
  full_name: string | null
  role: UserRole
  is_active: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
