/**
 * Global Dialog System
 * Promise-based API for confirm/alert dialogs
 *
 * Usage:
 *   const confirmed = await confirm({ title: 'Delete?', message: '...', type: 'danger' })
 *   await alert({ title: 'Error', message: '...', type: 'error' })
 */

import { reactive } from 'vue'

// Dialog types
export type DialogType = 'danger' | 'warning' | 'info' | 'success' | 'error'

// Confirm dialog options
export interface ConfirmOptions {
  title: string
  message: string
  type?: DialogType
  confirmText?: string
  cancelText?: string
}

// Alert dialog options
export interface AlertOptions {
  title: string
  message: string
  type?: DialogType
  confirmText?: string
}

// Dialog state
interface DialogState {
  confirm: {
    visible: boolean
    options: ConfirmOptions | null
    resolve: ((value: boolean) => void) | null
  }
  alert: {
    visible: boolean
    options: AlertOptions | null
    resolve: (() => void) | null
  }
}

// Global state
const state = reactive<DialogState>({
  confirm: {
    visible: false,
    options: null,
    resolve: null
  },
  alert: {
    visible: false,
    options: null,
    resolve: null
  }
})

/**
 * Show confirm dialog
 * Returns Promise<boolean> - true if confirmed, false if cancelled
 */
export function confirm(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    state.confirm.options = {
      type: 'warning',
      confirmText: 'Potvrdit',
      cancelText: 'Zrušit',
      ...options
    }
    state.confirm.resolve = resolve
    state.confirm.visible = true
  })
}

/**
 * Show alert dialog
 * Returns Promise<void> - resolves when user closes dialog
 */
export function alert(options: AlertOptions): Promise<void> {
  return new Promise((resolve) => {
    state.alert.options = {
      type: 'info',
      confirmText: 'OK',
      ...options
    }
    state.alert.resolve = resolve
    state.alert.visible = true
  })
}

/**
 * Internal: Close confirm dialog
 */
export function closeConfirm(result: boolean) {
  if (state.confirm.resolve) {
    state.confirm.resolve(result)
  }
  state.confirm.visible = false
  state.confirm.options = null
  state.confirm.resolve = null
}

/**
 * Internal: Close alert dialog
 */
export function closeAlert() {
  if (state.alert.resolve) {
    state.alert.resolve()
  }
  state.alert.visible = false
  state.alert.options = null
  state.alert.resolve = null
}

/**
 * Composable to access dialog state
 */
export function useDialog() {
  return {
    state,
    confirm,
    alert,
    closeConfirm,
    closeAlert
  }
}
