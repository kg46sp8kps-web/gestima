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
  updated_at: string
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

export interface UserCreateRequest {
  username: string
  password: string
  email?: string | null
  role: UserRole
}

export interface UserUpdateRequest {
  email?: string | null
  role?: UserRole
  is_active?: boolean
  version: number
}

export interface PasswordChangeRequest {
  password: string
}
