# Global Dialog System v2.0

**MANDATORY:** Vse informativni modaly MUSI pouzivat tento system!

## Import & Usage

```ts
import { confirm, alert } from '@/composables/useDialog'

// Confirm
const ok = await confirm({ title: 'Smazat?', message: 'Tato akce je nevratna!', type: 'danger' })
if (ok) await deleteItem()

// Alert
await alert({ title: 'Uspech', message: 'Ulozeno', type: 'success' })
```

## API

### `confirm(options): Promise<boolean>`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | `string` | required | Dialog title |
| `message` | `string` | required | Supports `\n` line breaks |
| `type` | `'danger' \| 'warning' \| 'info' \| 'success'` | `'warning'` | Visual type |
| `confirmText` | `string` | `'Potvrdit'` | Confirm button label |
| `cancelText` | `string` | `'Zrusit'` | Cancel button label |

Returns `true` (confirmed) or `false` (cancelled / ESC).

### `alert(options): Promise<void>`

Same options as `confirm` except `type` adds `'error'`, no `cancelText`. Resolves on close.

## Dialog Types

| Type | Icon | Color |
|------|------|-------|
| `danger` | Trash2 | Pink #f43f5e |
| `warning` | AlertTriangle | Orange #d97706 |
| `info` | Info | Blue #2563eb |
| `success` | Check | Green #059669 |
| `error` | XCircle | Pink #f43f5e (alert only) |

## Keyboard

- **ENTER** — confirm / close
- **ESC** — cancel / close

## Architecture

- Composable: `frontend/src/composables/useDialog.ts` — global state + Promise API
- Components: `frontend/src/components/ui/ConfirmDialog.vue`, `AlertDialog.vue`
- Registered globally in `App.vue`
- One dialog open at a time, Promise-based (no event emitters), auto-cleanup

## When to Use

**USE:** delete confirmations, unsaved-changes warnings, form errors, success/error notifications.

**DON'T USE** (use `Modal.vue` directly): forms with inputs, multi-step wizards, scrollable content, file upload.

## Custom Modal Pattern

```vue
<Modal v-model="show" size="md">
  <template #header><FileIcon :size="20" /><h3>Title</h3></template>
  <!-- content -->
  <template #footer>
    <button class="icon-btn" @click="cancel"><X :size="24" /></button>
    <button class="icon-btn icon-btn-primary" @click="submit"><Check :size="24" /></button>
  </template>
</Modal>
```

## Anti-Patterns

```ts
// WRONG
if (window.confirm('Delete?')) { ... }
alert('Error!')
const showDialog = ref(false)  // v-model pattern

// CORRECT
const ok = await confirm({ title: 'Delete?', message: '...', type: 'danger' })
```
