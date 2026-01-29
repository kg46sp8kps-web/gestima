/**
 * GESTIMA Auth API
 */

import { apiClient } from './client'
import type { LoginRequest, LoginResponse, User } from '@/types/auth'

export const authApi = {
  /**
   * Login user with username and password
   * Sets HttpOnly cookie on success
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>('/auth/login', credentials)
    return data
  },

  /**
   * Logout current user
   * Clears HttpOnly cookie
   */
  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  },

  /**
   * Get current user info
   * Requires valid JWT cookie
   */
  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  }
}
