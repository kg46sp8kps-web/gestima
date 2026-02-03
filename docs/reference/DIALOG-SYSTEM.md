# Global Dialog System

**⚠️ MANDATORY:** Všechny informativní modály MUSÍ používat tento systém!

Promise-based API pro confirm/alert dialogy v GESTIMA s jednotným designem.

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

## Design Pattern (MANDATORY!)

### Layout
```
┌──────────────────────────┐
│ 🗑️ Smazat nabídku?       │ ← Icon (32x32) + Title in Header
├──────────────────────────┤
│ Opravdu chcete smazat... │ ← Message text only
│                          │
│                ❌  ✅    │ ← Icon-only action buttons
└──────────────────────────┘
```

### Features
- ✅ **Icon + Title in Header** - Compact, clean hierarchy
- ✅ **Icon-only Buttons** - X (cancel) + Check (confirm)
- ✅ **Auto-focus** - Primary button has immediate focus
- ✅ **ENTER support** - Confirms instantly (no mouse needed)
- ✅ **ESC support** - Cancels/closes dialog
- ✅ **Color-coded** - Semantic colors by dialog type

### Dialog Types & Icons

| Type | Header Icon | Color | Button Color |
|------|-------------|-------|--------------|
| `danger` | Trash2 | Pink (#f43f5e) | Pink confirm |
| `warning` | AlertTriangle | Orange (#d97706) | Orange confirm |
| `info` | Info | Blue (#2563eb) | Blue confirm |
| `success` | Check | Green (#059669) | Green confirm |
| `error` | XCircle | Pink (#f43f5e) | N/A (alert only) |

### Button Design
- **Cancel (X icon):** Gray, transparent background, hover effect
- **Confirm (Check icon):** Colored by type, hover with 15% opacity background
- **Size:** 40x40px
- **No text labels** - Icons only for clean minimal look

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
- Uses existing `Modal.vue` component as wrapper
- Follows `design-system.css` tokens (100% compliance)
- Lucid icons:
  - Header icons: 20px (ICON_SIZE.STANDARD)
  - Button icons: 24px (ICON_SIZE.LARGE)
- Icon backgrounds: 15% opacity colors (rgba)
- Auto-focus on primary button via `nextTick()` + `ref.focus()`
- Keyboard navigation (ENTER/ESC)
- Smooth transitions (inherited from Modal.vue)
- Typography: `--text-xl` for title, `--text-base` for message

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

### Implementation Details
- Auto-focus implementation uses `nextTick()` and `ref.focus()`
- Keyboard listeners are added/removed on dialog open/close
- ESC handler in Modal.vue is disabled (handled by dialog components)
- Backdrop clicks are disabled for safety
- Close button (X) is hidden - users must choose action explicitly

### When to Use
✅ **USE for:**
- Delete confirmations
- Unsaved changes warnings
- Form validation errors
- Success/error notifications
- Any yes/no question
- Any informational message

❌ **DON'T USE for:**
- Complex forms with multiple inputs → Create custom modal with `Modal.vue`
- Multi-step wizards → Use dedicated wizard component
- Content that needs scrolling → Custom modal
- File upload dialogs → Custom modal

### Custom Modals
If you need a custom modal (forms, complex content):
1. Use `Modal.vue` as base wrapper
2. Follow the same design pattern (icon + title in header if applicable)
3. Use icon-only buttons in footer where possible
4. Keep footer buttons consistent (secondary left, primary right)

Example:
```vue
<Modal v-model="show" size="md">
  <template #header>
    <div class="modal-header">
      <FileIcon :size="20" /> <!-- Optional icon -->
      <h3>Upload File</h3>
    </div>
  </template>

  <!-- Your custom content -->

  <template #footer>
    <button class="icon-btn" @click="cancel">
      <X :size="24" />
    </button>
    <button class="icon-btn icon-btn-primary" @click="submit">
      <Check :size="24" />
    </button>
  </template>
</Modal>
```

## Anti-Patterns (DON'T DO THIS!)

❌ **Creating custom confirm modals**
```vue
<!-- DON'T! -->
<DeleteConfirmModal v-model="showDelete" @confirm="handleDelete" />
```
✅ **Use global dialog instead:**
```ts
// DO!
const confirmed = await confirm({
  title: 'Delete?',
  message: '...',
  type: 'danger'
})
```

❌ **Using window.confirm() or alert()**
```ts
// DON'T!
if (window.confirm('Delete?')) { ... }
alert('Error!')
```

❌ **Text buttons in dialogs**
```vue
<!-- DON'T! -->
<button class="btn btn-primary">Smazat</button>
```
✅ **Use icon-only:**
```vue
<!-- DO! -->
<button class="icon-btn">
  <Check :size="24" />
</button>
```
