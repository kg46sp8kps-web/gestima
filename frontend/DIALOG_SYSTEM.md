# Global Dialog System

Promise-based API pro confirm/alert dialogy v GESTIMA.

## Použití

### Import
```ts
import { confirm, alert } from '@/composables/useDialog'
```

### Confirm Dialog
```ts
const confirmed = await confirm({
  title: 'Smazat nabídku?',
  message: 'Opravdu chcete smazat nabídku "ABC-123"?\n\nTato akce je nevratná!',
  type: 'danger',
  confirmText: 'Smazat',
  cancelText: 'Zrušit'
})

if (confirmed) {
  // User clicked confirm
  await deleteQuote()
} else {
  // User clicked cancel or ESC
}
```

### Alert Dialog
```ts
await alert({
  title: 'Úspěch',
  message: 'Nabídka byla úspěšně uložena',
  type: 'success'
})

// Continues after user clicks OK or ESC
```

## API

### `confirm(options: ConfirmOptions): Promise<boolean>`

**Options:**
- `title: string` - Dialog title (required)
- `message: string` - Dialog message (required, supports `\n` for line breaks)
- `type?: 'danger' | 'warning' | 'info' | 'success'` - Dialog type (default: 'warning')
- `confirmText?: string` - Confirm button text (default: 'Potvrdit')
- `cancelText?: string` - Cancel button text (default: 'Zrušit')

**Returns:** `Promise<boolean>`
- `true` if user clicked confirm
- `false` if user clicked cancel or pressed ESC

### `alert(options: AlertOptions): Promise<void>`

**Options:**
- `title: string` - Dialog title (required)
- `message: string` - Dialog message (required, supports `\n` for line breaks)
- `type?: 'error' | 'success' | 'info' | 'warning'` - Dialog type (default: 'info')
- `confirmText?: string` - OK button text (default: 'OK')

**Returns:** `Promise<void>` - resolves when user closes dialog

## Dialog Types & Icons

| Type | Icon | Color |
|------|------|-------|
| `danger` | Trash2 | Pink (#f43f5e) |
| `warning` | AlertTriangle | Orange (#d97706) |
| `info` | Info | Blue (#2563eb) |
| `success` | Check | Green (#059669) |
| `error` | XCircle | Pink (#f43f5e) |

## Keyboard Shortcuts

### Confirm Dialog
- **ENTER** - Confirm action
- **ESC** - Cancel action

### Alert Dialog
- **ENTER** - Close dialog
- **ESC** - Close dialog

## Real-World Examples

### Delete Confirmation
```ts
async function handleDelete(quote: Quote) {
  const confirmed = await confirm({
    title: 'Smazat nabídku?',
    message: `Opravdu chcete smazat nabídku "${quote.quote_number}"?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await quotesApi.delete(quote.id)
    await alert({
      title: 'Úspěch',
      message: 'Nabídka byla úspěšně smazána',
      type: 'success'
    })
  } catch (error) {
    await alert({
      title: 'Chyba',
      message: 'Nepodařilo se smazat nabídku',
      type: 'error'
    })
  }
}
```

### Unsaved Changes Warning
```ts
async function handleClose() {
  if (hasUnsavedChanges.value) {
    const confirmed = await confirm({
      title: 'Neuložené změny',
      message: 'Máte neuložené změny.\n\nOpravdu chcete zavřít bez uložení?',
      type: 'warning',
      confirmText: 'Zavřít bez uložení',
      cancelText: 'Zůstat'
    })

    if (!confirmed) return
  }

  closeWindow()
}
```

### Form Validation Error
```ts
async function handleSubmit() {
  if (!isValid()) {
    await alert({
      title: 'Neplatná data',
      message: 'Vyplňte prosím všechna povinná pole',
      type: 'error'
    })
    return
  }

  // Continue with submit...
}
```

## Implementation Details

### Architecture
- **Composable:** `/frontend/src/composables/useDialog.ts` - Global state & Promise API
- **Components:**
  - `/frontend/src/components/ui/ConfirmDialog.vue` - Confirm dialog with 2 buttons
  - `/frontend/src/components/ui/AlertDialog.vue` - Alert dialog with 1 button
- **Registration:** Components are globally mounted in `App.vue`

### Design System Compliance
- Uses existing `Modal.vue` component
- Follows `design-system.css` tokens
- Lucid icons (size: 20px)
- Auto-focus on primary button
- Keyboard navigation (ENTER/ESC)
- Smooth transitions

### State Management
- Single global reactive state
- Only one dialog can be open at a time
- Promise-based resolution (no event emitters)
- Automatic cleanup after dialog closes

## Migration from Old Pattern

### Before (v-model based)
```ts
// OLD - don't use!
const showDialog = ref(false)

<ConfirmDialog
  v-model="showDialog"
  @confirm="handleConfirm"
  @cancel="handleCancel"
/>
```

### After (Promise-based)
```ts
// NEW - use this!
const confirmed = await confirm({
  title: 'Delete?',
  message: 'Are you sure?',
  type: 'danger'
})

if (confirmed) {
  // handle confirm
}
```

## Technical Notes

- Auto-focus implementation uses `nextTick()` and `ref.focus()`
- Keyboard listeners are added/removed on dialog open/close
- ESC handler in Modal.vue is disabled (handled by dialog components)
- Backdrop clicks are disabled for safety
- Close button (X) is hidden - users must choose action
