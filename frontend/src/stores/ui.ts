import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

let nextId = 0

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<Toast[]>([])
  const loadingCount = ref(0)

  const isLoading = (): boolean => loadingCount.value > 0

  function startLoading() {
    loadingCount.value++
  }

  function stopLoading() {
    if (loadingCount.value > 0) loadingCount.value--
  }

  function showToast(type: ToastType, message: string, duration = 4000) {
    const id = ++nextId
    toasts.value.push({ id, type, message })
    setTimeout(() => removeToast(id), duration)
  }

  function removeToast(id: number) {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  function showSuccess(message: string) {
    showToast('success', message)
  }

  function showError(message: string) {
    showToast('error', message, 6000)
  }

  function showWarning(message: string) {
    showToast('warning', message)
  }

  function showInfo(message: string) {
    showToast('info', message)
  }

  return {
    toasts,
    loadingCount,
    isLoading,
    startLoading,
    stopLoading,
    showToast,
    removeToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  }
})
