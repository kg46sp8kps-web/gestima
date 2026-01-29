/**
 * GESTIMA Auth Store
 *
 * Manages authentication state, login/logout, and user permissions.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest, UserRole } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ============================================================================
  // GETTERS
  // ============================================================================

  const isAuthenticated = computed(() => !!user.value)

  const isAdmin = computed(() => user.value?.role === 'admin')

  const isOperator = computed(() =>
    user.value?.role === 'admin' || user.value?.role === 'operator'
  )

  const isViewer = computed(() =>
    user.value?.role === 'admin' ||
    user.value?.role === 'operator' ||
    user.value?.role === 'viewer'
  )

  const currentRole = computed((): UserRole | null => user.value?.role || null)

  // ============================================================================
  // ACTIONS
  // ============================================================================

  /**
   * Login with username and password
   */
  async function login(credentials: LoginRequest): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login(credentials)

      // Fetch full user info after successful login
      await fetchCurrentUser()

      console.log(`[Auth] User logged in: ${response.username}`)
    } catch (err: any) {
      error.value = err.message || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Logout current user
   */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
      user.value = null
      console.log('[Auth] User logged out')
    } catch (err) {
      console.error('[Auth] Logout error:', err)
      // Force logout even if API call fails
      user.value = null
    }
  }

  /**
   * Fetch current user info
   * Used on app init and after login
   */
  async function fetchCurrentUser(): Promise<void> {
    try {
      user.value = await authApi.me()
      console.log(`[Auth] Current user: ${user.value.username}`)
    } catch (err) {
      console.warn('[Auth] Not authenticated')
      user.value = null
    }
  }

  /**
   * Clear auth state
   * Used when session expires or on 401 errors
   */
  function clearAuth(): void {
    user.value = null
    error.value = null
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    user,
    loading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    isOperator,
    isViewer,
    currentRole,

    // Actions
    login,
    logout,
    fetchCurrentUser,
    clearAuth
  }
})
