/**
 * GESTIMA UI Store
 *
 * Manages global UI state: toasts, loading indicators, modals, etc.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// ============================================================================
// TYPES
// ============================================================================

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  message: string
  type: ToastType
  duration: number
}

// ============================================================================
// STORE
// ============================================================================

export const useUiStore = defineStore('ui', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const loadingCounter = ref(0) // Counter for concurrent API requests
  const toasts = ref<Toast[]>([])
  let toastIdCounter = 0

  // ============================================================================
  // GETTERS
  // ============================================================================

  const isLoading = computed(() => loadingCounter.value > 0)

  // ============================================================================
  // ACTIONS - Loading
  // ============================================================================

  /**
   * Start loading (increment counter)
   * Can be called multiple times for concurrent requests
   */
  function startLoading(): void {
    loadingCounter.value++
  }

  /**
   * Stop loading (decrement counter)
   * Only shows not-loading when counter reaches 0
   */
  function stopLoading(): void {
    loadingCounter.value = Math.max(0, loadingCounter.value - 1)
  }

  /**
   * Force stop all loading
   * Use only in error recovery scenarios
   */
  function resetLoading(): void {
    loadingCounter.value = 0
  }

  // ============================================================================
  // ACTIONS - Toasts
  // ============================================================================

  /**
   * Show toast notification
   *
   * @param message - Message to display
   * @param type - Toast type (success, error, warning, info)
   * @param duration - Duration in ms (0 = infinite, requires manual dismiss)
   */
  function showToast(
    message: string,
    type: ToastType = 'info',
    duration = 3000
  ): void {
    const id = ++toastIdCounter
    const toast: Toast = { id, message, type, duration }

    toasts.value.push(toast)

    // Auto-remove after duration (unless duration = 0)
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }

  /**
   * Remove toast by ID
   */
  function removeToast(id: number): void {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  /**
   * Clear all toasts
   */
  function clearToasts(): void {
    toasts.value = []
  }

  // ============================================================================
  // CONVENIENCE METHODS
  // ============================================================================

  function showSuccess(message: string, duration = 3000): void {
    showToast(message, 'success', duration)
  }

  function showError(message: string, duration = 5000): void {
    showToast(message, 'error', duration)
  }

  function showWarning(message: string, duration = 4000): void {
    showToast(message, 'warning', duration)
  }

  function showInfo(message: string, duration = 3000): void {
    showToast(message, 'info', duration)
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    loadingCounter,
    toasts,

    // Getters
    isLoading,

    // Actions
    startLoading,
    stopLoading,
    resetLoading,
    showToast,
    removeToast,
    clearToasts,

    // Convenience
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
})
