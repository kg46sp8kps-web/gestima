import { ref } from 'vue'

export interface DialogOptions {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  dangerous?: boolean
}

interface DialogState extends DialogOptions {
  resolve: (value: boolean) => void
}

interface AlertState {
  title: string
  message: string
  buttonLabel?: string
  resolve: () => void
}

const confirmDialog = ref<DialogState | null>(null)
const alertDialog = ref<AlertState | null>(null)

export function useDialog() {
  function confirm(options: DialogOptions): Promise<boolean> {
    return new Promise((resolve) => {
      confirmDialog.value = { ...options, resolve }
    })
  }

  function alert(options: { title: string; message: string; buttonLabel?: string }): Promise<void> {
    return new Promise((resolve) => {
      alertDialog.value = { ...options, resolve }
    })
  }

  function resolveConfirm(result: boolean) {
    confirmDialog.value?.resolve(result)
    confirmDialog.value = null
  }

  function resolveAlert() {
    alertDialog.value?.resolve()
    alertDialog.value = null
  }

  return {
    confirmDialog,
    alertDialog,
    confirm,
    alert,
    resolveConfirm,
    resolveAlert,
  }
}
