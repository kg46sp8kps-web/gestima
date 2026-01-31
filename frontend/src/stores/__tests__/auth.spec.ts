/**
 * GESTIMA Auth Store Tests
 *
 * Tests authentication state management, login/logout flows, and permissions.
 */

import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import { authApi } from '@/api/auth'
import type { User } from '@/types/auth'
import { UserRole } from '@/types/auth'

// Mock authApi
vi.mock('@/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    me: vi.fn()
  }
}))

// Helper to create valid User mock
function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    username: 'testuser',
    email: null,
    role: UserRole.OPERATOR,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    created_by: null,
    updated_at: null,
    updated_by: null,
    ...overrides
  }
}

describe('Auth Store', () => {
  beforeEach(() => {
    // Create fresh pinia instance for each test (isolation!)
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Reset console.log/warn/error spies
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  // ==========================================================================
  // INITIAL STATE
  // ==========================================================================

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const store = useAuthStore()

      expect(store.user).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.isAdmin).toBe(false)
      expect(store.isOperator).toBe(false)
      expect(store.isViewer).toBe(false)
      expect(store.currentRole).toBeNull()
    })
  })

  // ==========================================================================
  // LOGIN
  // ==========================================================================

  describe('Login', () => {
    const mockUser = createMockUser()

    it('should login successfully and fetch user', async () => {
      const store = useAuthStore()
      ;(authApi.login as Mock).mockResolvedValue({ username: 'testuser' })
      ;(authApi.me as Mock).mockResolvedValue(mockUser)

      await store.login({ username: 'testuser', password: 'password123' })

      expect(authApi.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      })
      expect(authApi.me).toHaveBeenCalled()
      expect(store.user).toEqual(mockUser)
      expect(store.isAuthenticated).toBe(true)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should set loading=true during login', async () => {
      const store = useAuthStore()
      ;(authApi.login as Mock).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ username: 'test' }), 100))
      )
      ;(authApi.me as Mock).mockResolvedValue(mockUser)

      const loginPromise = store.login({ username: 'test', password: 'test' })
      expect(store.loading).toBe(true)

      await loginPromise
      expect(store.loading).toBe(false)
    })

    it('should handle login failure', async () => {
      const store = useAuthStore()
      const error = new Error('Invalid credentials')
      ;(authApi.login as Mock).mockRejectedValue(error)

      await expect(
        store.login({ username: 'wrong', password: 'wrong' })
      ).rejects.toThrow('Invalid credentials')

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.loading).toBe(false)
      expect(store.error).toBe('Invalid credentials')
    })

    it('should handle login with network error', async () => {
      const store = useAuthStore()
      ;(authApi.login as Mock).mockRejectedValue(new Error('Network error'))

      await expect(
        store.login({ username: 'test', password: 'test' })
      ).rejects.toThrow()

      expect(store.error).toBe('Network error')
    })
  })

  // ==========================================================================
  // LOGOUT
  // ==========================================================================

  describe('Logout', () => {
    it('should logout successfully', async () => {
      const store = useAuthStore()
      store.user = createMockUser()
      ;(authApi.logout as Mock).mockResolvedValue(undefined)

      await store.logout()

      expect(authApi.logout).toHaveBeenCalled()
      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should force logout even if API call fails', async () => {
      const store = useAuthStore()
      store.user = createMockUser()
      ;(authApi.logout as Mock).mockRejectedValue(new Error('Server error'))

      await store.logout()

      expect(store.user).toBeNull()
      expect(console.error).toHaveBeenCalledWith('[Auth] Logout error:', expect.any(Error))
    })
  })

  // ==========================================================================
  // FETCH CURRENT USER
  // ==========================================================================

  describe('Fetch Current User', () => {
    const mockUser = createMockUser({ role: UserRole.ADMIN })

    it('should fetch current user successfully', async () => {
      const store = useAuthStore()
      ;(authApi.me as Mock).mockResolvedValue(mockUser)

      await store.fetchCurrentUser()

      expect(authApi.me).toHaveBeenCalled()
      expect(store.user).toEqual(mockUser)
      expect(store.isAuthenticated).toBe(true)
    })

    it('should handle fetch failure (401 Unauthorized)', async () => {
      const store = useAuthStore()
      ;(authApi.me as Mock).mockRejectedValue(new Error('Unauthorized'))

      await store.fetchCurrentUser()

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(console.warn).toHaveBeenCalledWith('[Auth] Not authenticated')
    })
  })

  // ==========================================================================
  // PERMISSIONS (ROLE-BASED)
  // ==========================================================================

  describe('Permissions', () => {
    it('should correctly identify admin role', () => {
      const store = useAuthStore()
      store.user = createMockUser({ username: 'admin', role: UserRole.ADMIN })

      expect(store.isAdmin).toBe(true)
      expect(store.isOperator).toBe(true) // admin >= operator
      expect(store.isViewer).toBe(true) // admin >= viewer
      expect(store.currentRole).toBe(UserRole.ADMIN)
    })

    it('should correctly identify operator role', () => {
      const store = useAuthStore()
      store.user = createMockUser({ username: 'operator', role: UserRole.OPERATOR })

      expect(store.isAdmin).toBe(false)
      expect(store.isOperator).toBe(true)
      expect(store.isViewer).toBe(true) // operator >= viewer
      expect(store.currentRole).toBe(UserRole.OPERATOR)
    })

    it('should correctly identify viewer role', () => {
      const store = useAuthStore()
      store.user = createMockUser({ username: 'viewer', role: UserRole.VIEWER })

      expect(store.isAdmin).toBe(false)
      expect(store.isOperator).toBe(false)
      expect(store.isViewer).toBe(true)
      expect(store.currentRole).toBe(UserRole.VIEWER)
    })

    it('should handle no user (unauthenticated)', () => {
      const store = useAuthStore()

      expect(store.isAdmin).toBe(false)
      expect(store.isOperator).toBe(false)
      expect(store.isViewer).toBe(false)
      expect(store.currentRole).toBeNull()
    })
  })

  // ==========================================================================
  // CLEAR AUTH
  // ==========================================================================

  describe('Clear Auth', () => {
    it('should clear auth state', () => {
      const store = useAuthStore()
      store.user = createMockUser({ username: 'test', role: UserRole.ADMIN })
      store.error = 'Some error'

      store.clearAuth()

      expect(store.user).toBeNull()
      expect(store.error).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })
  })
})
