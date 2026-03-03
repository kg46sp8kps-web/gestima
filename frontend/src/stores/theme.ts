import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type Theme = 'dark' | 'light' | 'corporate'

const STORAGE_KEY = 'gestima.theme'
const VALID: Theme[] = ['dark', 'light', 'corporate']

export const useThemeStore = defineStore('theme', () => {
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null
  const theme = ref<Theme>(stored && VALID.includes(stored) ? stored : 'dark')

  function apply(t: Theme) {
    document.documentElement.setAttribute('data-theme', t)
  }

  watch(theme, (t) => {
    localStorage.setItem(STORAGE_KEY, t)
    apply(t)
  }, { immediate: true })

  return { theme }
})
