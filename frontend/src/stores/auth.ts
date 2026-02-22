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

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const token = await authApi.login(username, password)
      localStorage.setItem('access_token', token.access_token)
      const me = await authApi.getMe()
      user.value = me
      await router.push('/')
      return true
    } catch {
      ui.showError('Neplatné přihlašovací údaje.')
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<void> {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      user.value = await authApi.getMe()
    } catch {
      localStorage.removeItem('access_token')
      user.value = null
    }
  }

  function logout() {
    localStorage.removeItem('access_token')
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
