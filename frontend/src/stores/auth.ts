import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useRouter } from 'vue-router'
import * as authApi from '@/api/auth'
import { useUiStore } from './ui'
import type { User } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()
  const ui = useUiStore()

  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() =>
    user.value?.role === 'admin' || user.value?.role === 'operator',
  )

  /** Returns true on success — caller is responsible for navigation */
  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      // Server sets HttpOnly cookie; we call getMe() for full user data
      await authApi.login(username, password)
      user.value = await authApi.getMe()
      return true
    } catch {
      ui.showError('Neplatné přihlašovací údaje.')
      return false
    } finally {
      loading.value = false
    }
  }

  /** Try to restore session from existing cookie — silently fails if no cookie */
  async function fetchMe(): Promise<void> {
    try {
      user.value = await authApi.getMe()
    } catch {
      user.value = null
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // Ignore errors — always clear local state
    }
    user.value = null
    router.push('/login')
  }

  return {
    user,
    loading,
    isLoggedIn,
    isAdmin,
    isOperator,
    login,
    fetchMe,
    logout,
  }
})
