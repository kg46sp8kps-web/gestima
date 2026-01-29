/**
 * GESTIMA Auth Types
 */

export enum UserRole {
  ADMIN = 'admin',
  OPERATOR = 'operator',
  VIEWER = 'viewer'
}

export interface User {
  id: number
  username: string
  email: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  created_by: string | null
  updated_at: string | null
  updated_by: string | null
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  status: string
  username: string
  role: UserRole
}

export interface UserResponse {
  id: number
  username: string
  email: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}
