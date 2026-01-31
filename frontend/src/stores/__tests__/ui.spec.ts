/**
 * GESTIMA UI Store Tests
 *
 * Tests global UI state: loading indicators, toast notifications, etc.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '../ui'

describe('UI Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ==========================================================================
  // INITIAL STATE
  // ==========================================================================

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const store = useUiStore()

      expect(store.loadingCounter).toBe(0)
      expect(store.isLoading).toBe(false)
      expect(store.toasts).toEqual([])
    })
  })

  // ==========================================================================
  // LOADING COUNTER
  // ==========================================================================

  describe('Loading Counter', () => {
    it('should increment loading counter', () => {
      const store = useUiStore()

      store.startLoading()
      expect(store.loadingCounter).toBe(1)
      expect(store.isLoading).toBe(true)

      store.startLoading()
      expect(store.loadingCounter).toBe(2)
      expect(store.isLoading).toBe(true)
    })

    it('should decrement loading counter', () => {
      const store = useUiStore()
      store.startLoading()
      store.startLoading()

      store.stopLoading()
      expect(store.loadingCounter).toBe(1)
      expect(store.isLoading).toBe(true)

      store.stopLoading()
      expect(store.loadingCounter).toBe(0)
      expect(store.isLoading).toBe(false)
    })

    it('should not go below zero when stopping loading', () => {
      const store = useUiStore()

      store.stopLoading()
      expect(store.loadingCounter).toBe(0)

      store.stopLoading()
      expect(store.loadingCounter).toBe(0)
    })

    it('should reset loading counter', () => {
      const store = useUiStore()
      store.startLoading()
      store.startLoading()
      store.startLoading()

      expect(store.loadingCounter).toBe(3)

      store.resetLoading()
      expect(store.loadingCounter).toBe(0)
      expect(store.isLoading).toBe(false)
    })

    it('should handle concurrent requests', () => {
      const store = useUiStore()

      // Start 3 requests
      store.startLoading()
      store.startLoading()
      store.startLoading()
      expect(store.isLoading).toBe(true)

      // Complete 1 request
      store.stopLoading()
      expect(store.isLoading).toBe(true) // Still 2 pending

      // Complete 2nd request
      store.stopLoading()
      expect(store.isLoading).toBe(true) // Still 1 pending

      // Complete 3rd request
      store.stopLoading()
      expect(store.isLoading).toBe(false) // All done!
    })
  })

  // ==========================================================================
  // TOASTS
  // ==========================================================================

  describe('Toasts', () => {
    it('should show toast with correct properties', () => {
      const store = useUiStore()

      store.showToast('Test message', 'info', 3000)

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toMatchObject({
        message: 'Test message',
        type: 'info',
        duration: 3000
      })
      expect(store.toasts[0]!.id).toBeGreaterThan(0)
    })

    it('should auto-remove toast after duration', () => {
      const store = useUiStore()

      store.showToast('Test', 'info', 3000)
      expect(store.toasts).toHaveLength(1)

      // Fast-forward time by 3000ms
      vi.advanceTimersByTime(3000)

      expect(store.toasts).toHaveLength(0)
    })

    it('should NOT auto-remove toast with duration=0', () => {
      const store = useUiStore()

      store.showToast('Persistent', 'info', 0)
      expect(store.toasts).toHaveLength(1)

      vi.advanceTimersByTime(10000)
      expect(store.toasts).toHaveLength(1) // Still there!
    })

    it('should manually remove toast by ID', () => {
      const store = useUiStore()

      store.showToast('Toast 1', 'info', 0)
      store.showToast('Toast 2', 'info', 0)
      store.showToast('Toast 3', 'info', 0)

      expect(store.toasts).toHaveLength(3)

      const toastId = store.toasts[1]!.id
      store.removeToast(toastId)

      expect(store.toasts).toHaveLength(2)
      expect(store.toasts.find(t => t.id === toastId)).toBeUndefined()
    })

    it('should handle removing non-existent toast ID', () => {
      const store = useUiStore()

      store.showToast('Test', 'info', 0)
      expect(store.toasts).toHaveLength(1)

      store.removeToast(99999) // Non-existent ID
      expect(store.toasts).toHaveLength(1) // No change
    })

    it('should clear all toasts', () => {
      const store = useUiStore()

      store.showToast('Toast 1', 'info', 0)
      store.showToast('Toast 2', 'error', 0)
      store.showToast('Toast 3', 'success', 0)

      expect(store.toasts).toHaveLength(3)

      store.clearToasts()
      expect(store.toasts).toHaveLength(0)
    })

    it('should assign unique IDs to toasts', () => {
      const store = useUiStore()

      store.showToast('Toast 1', 'info', 0)
      store.showToast('Toast 2', 'info', 0)
      store.showToast('Toast 3', 'info', 0)

      const ids = store.toasts.map(t => t.id)
      const uniqueIds = new Set(ids)

      expect(uniqueIds.size).toBe(3) // All unique
    })
  })

  // ==========================================================================
  // CONVENIENCE METHODS
  // ==========================================================================

  describe('Convenience Methods', () => {
    it('should show success toast', () => {
      const store = useUiStore()

      store.showSuccess('Success message')

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toMatchObject({
        message: 'Success message',
        type: 'success',
        duration: 3000
      })
    })

    it('should show error toast with longer duration', () => {
      const store = useUiStore()

      store.showError('Error message')

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toMatchObject({
        message: 'Error message',
        type: 'error',
        duration: 5000 // Default 5s for errors
      })
    })

    it('should show warning toast', () => {
      const store = useUiStore()

      store.showWarning('Warning message')

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toMatchObject({
        message: 'Warning message',
        type: 'warning',
        duration: 4000
      })
    })

    it('should show info toast', () => {
      const store = useUiStore()

      store.showInfo('Info message')

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toMatchObject({
        message: 'Info message',
        type: 'info',
        duration: 3000
      })
    })

    it('should allow custom duration in convenience methods', () => {
      const store = useUiStore()

      store.showSuccess('Fast success', 1000)

      expect(store.toasts[0]!.duration).toBe(1000)
    })
  })

  // ==========================================================================
  // MULTIPLE TOASTS
  // ==========================================================================

  describe('Multiple Toasts', () => {
    it('should handle multiple toasts at once', () => {
      const store = useUiStore()

      store.showSuccess('Success')
      store.showError('Error')
      store.showWarning('Warning')
      store.showInfo('Info')

      expect(store.toasts).toHaveLength(4)
    })

    it('should remove toasts independently', () => {
      const store = useUiStore()

      store.showToast('Fast', 'info', 1000)
      store.showToast('Medium', 'info', 2000)
      store.showToast('Slow', 'info', 3000)

      expect(store.toasts).toHaveLength(3)

      vi.advanceTimersByTime(1000)
      expect(store.toasts).toHaveLength(2)

      vi.advanceTimersByTime(1000)
      expect(store.toasts).toHaveLength(1)

      vi.advanceTimersByTime(1000)
      expect(store.toasts).toHaveLength(0)
    })
  })
})
