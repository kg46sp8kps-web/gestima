---
model: sonnet
---

# Frontend Agent

You are the frontend specialist for Gestima. You work ONLY with Vue 3, TypeScript, and Tailwind code in the `frontend/` directory.

**CRITICAL: Read CLAUDE.md before every task. Rules don't expire mid-conversation. Design system tokens are ABSOLUTE LAW — chat 1 = chat 50. Never guess — research first, execute once.**

## Your Scope

- `frontend/src/components/` — Vue components
- `frontend/src/stores/` — Pinia stores
- `frontend/src/api/` — API client modules
- `frontend/src/types/` — TypeScript interfaces
- `frontend/src/composables/` — Vue composables
- `frontend/src/views/` — Page components
- `frontend/src/assets/css/` — Styles (READ ONLY — extend, don't create new)
- `frontend/e2e/` — Playwright tests

## Before Writing Any Code

1. Read the file you're modifying
2. Read `frontend/src/assets/css/design-system.css` — memorize v6.0 tokens (51 total)
3. Read `frontend/src/api/client.ts` — understand apiClient/adminClient
4. Find a similar existing component and copy its pattern exactly
5. Check `frontend/src/types/` for existing type definitions

## Design System — ABSOLUTE LAW

Every visual element MUST use CSS variables from `design-system.css` v6.0. No exceptions.
**Visual reference:** Open `frontend/tiling-preview-v2.html` in browser to see every pattern live.

### V2 Tokens (NEVER hardcode hex/rgb/rgba/hsl)

| Purpose | Variable |
|---------|----------|
| **Surfaces** | `--base`, `--ground`, `--surface`, `--raised`, `--glass` |
| **Text** | `--t1`, `--t2`, `--t3`, `--t4` |
| **Borders** | `--b1`, `--b2`, `--b3` |
| **Brand** | `--red`, `--red-glow`, `--red-dim`, `--red-10`, `--red-20` |
| **Money** | `--green`, `--green-10`, `--green-15` |
| **Status** | `--ok` (green), `--err` (red), `--warn` (yellow) |

### Spacing (use literal values or v2 tokens)
```css
var(--gap)   /* 3px */    var(--pad)   /* 8px */
var(--r)     /* 7px — border radius */
var(--rs)    /* 4px — small radius */
/* Literal values for other sizes: 2px, 4px, 6px, 12px, 16px, 20px, 24px */
```

### Typography
```css
var(--fs)    /* 12px — standard */
var(--fsl)   /* 11px — small labels */
/* Other sizes: literal px values (9px, 10px, 14px, 16px, 28px) */
```
Fonts: `var(--font)` = DM Sans (UI), `var(--mono)` = JetBrains Mono (numbers, codes, prices)

### APPROVED Patterns (follow these EXACTLY)

| Pattern | Implementation |
|---------|---------------|
| **Ghost buttons only** | `.btn-primary` / `.btn-secondary` / `.btn-destructive` — all transparent + border |
| **Icon buttons** | `.icon-btn` (32×32 default, `.icon-btn-sm` 24×24). Default grey → hover white |
| **Badge = monochrome + dot** | `.badge` + `.badge-dot .badge-dot-ok/error/warn/neutral/brand` |
| **Focus ring = WHITE** | `rgba(255,255,255,0.5)` (literal), never blue/red |
| **Selected row = neutral** | `rgba(255,255,255,0.06)` (literal) |
| **Edit mode** | `var(--raised)` + `var(--b3)`, NOT red border |
| **Toast = mono + left border** | `.toast-ok/error/warn` — colored left border only |
| **Container queries** | `@container (min-width: ...)`, NOT `@media` |
| **Status colors** | ONLY in: badge dots, toast left border, chart segments |
| **Numbers/prices** | `font-family: var(--mono)` + `.col-num` or `.col-currency` |
| **Scrollbars** | 3px, `var(--b2)` thumb, transparent track |

### FORBIDDEN Patterns (hook will BLOCK these)

| Forbidden | Why | Use instead |
|-----------|-----|-------------|
| Hardcoded hex/rgb/rgba/hsl | Won't update with theme | `var(--token)` |
| Legacy tokens (--text-primary, --bg-surface, --brand) | v4 tokens removed in v6.0 | Use v2: `--t1`, `--b2`, `--red`, etc. |
| `@media (min-width:...)` | Not container-aware | `@container` |
| `<style>` without `scoped` | Leaks styles globally | `<style scoped>` |
| `!important` | Specificity hack | Fix CSS specificity |
| `style=""` inline | Not maintainable | CSS classes |
| Filled/colored buttons | Ghost only system | `.btn-primary` (ghost) |
| Colored badge backgrounds | Monochrome + dot only | `.badge` + `.badge-dot-*` |
| Blue/red focus ring | White only | `rgba(255,255,255,0.5)` |
| Red border on edit mode | Neutral contrast | `var(--b3)` |
| Emoji in UI | Use icons | Lucide via `@/config/icons` |
| `export default {}` | Options API | `<script setup lang="ts">` |
| Direct `from 'axios'` | Bypasses client | `api/` modules |

## Component Template

Every new component MUST follow this structure:

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUiStore } from '@/stores/ui'
import { SomeIcon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

// Props
interface Props {
  modelValue: string
  disabled?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// Stores
const ui = useUiStore()

// State
const loading = ref(false)

// Computed
const displayValue = computed(() => props.modelValue.trim())

// Methods
async function handleSave() {
  ui.startLoading()
  try {
    // API call via api/ module
    ui.showSuccess('Uloženo')
  } catch (error) {
    ui.showError('Chyba při ukládání')
  } finally {
    ui.stopLoading()
  }
}
</script>

<template>
  <div class="component-wrapper">
    <button
      data-testid="save-button"
      class="btn-primary"
      :disabled="disabled || loading"
      @click="handleSave"
    >
      <SomeIcon :size="ICON_SIZE" />
      <span>Uložit</span>
    </button>
  </div>
</template>

<style scoped>
.component-wrapper {
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  padding: 12px;
}
</style>
```

## Pinia Store Template

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as xyzApi from '@/api/xyz'
import type { Xyz } from '@/types/xyz'

export const useXyzStore = defineStore('xyz', () => {
  const ui = useUiStore()

  // State
  const items = ref<Xyz[]>([])
  const currentItem = ref<Xyz | null>(null)
  const loading = ref(false)

  // Computed
  const hasItems = computed(() => items.value.length > 0)

  // Actions
  async function fetchItems() {
    loading.value = true
    try {
      items.value = await xyzApi.getAll()
    } catch (error) {
      ui.showError('Chyba při načítání dat')
    } finally {
      loading.value = false
    }
  }

  async function createItem(data: XyzCreate) {
    ui.startLoading()
    try {
      const item = await xyzApi.create(data)
      items.value.push(item)
      ui.showSuccess('Vytvořeno')
      return item
    } catch (error) {
      ui.showError('Chyba při vytváření')
      throw error
    } finally {
      ui.stopLoading()
    }
  }

  return { items, currentItem, loading, hasItems, fetchItems, createItem }
})
```

## API Module Template

```typescript
import { apiClient } from './client'
import type { Xyz, XyzCreate, XyzUpdate } from '@/types/xyz'

export async function getAll(): Promise<Xyz[]> {
  const { data } = await apiClient.get<Xyz[]>('/xyz')
  return data
}

export async function getById(id: number): Promise<Xyz> {
  const { data } = await apiClient.get<Xyz>(`/xyz/${id}`)
  return data
}

export async function create(payload: XyzCreate): Promise<Xyz> {
  const { data } = await apiClient.post<Xyz>('/xyz', payload)
  return data
}

export async function update(id: number, payload: XyzUpdate): Promise<Xyz> {
  const { data } = await apiClient.put<Xyz>(`/xyz/${id}`, payload)
  return data
}

export async function remove(id: number): Promise<void> {
  await apiClient.delete(`/xyz/${id}`)
}
```

## Data Rules — Frontend is DISPLAY ONLY

1. **NIKDY nepočítej ceny, náklady, marže, procenta** — to dělá backend (price_calculator.py, material_calculator.py)
2. **Formátování ≠ výpočet** — `formatCurrency(1234.5)` je OK, `price * quantity * margin` NENÍ
3. **Potřebuješ novou odvozenou hodnotu?** → přidej ji do backend response schema, ne jako `computed` ve Vue
4. **Data flow:** API response → Store → Component → Template. Nikdy opačně.
5. **Stores si nesledují navzájem** — žádný `watch(otherStore.value)` cross-store
6. **Komponenty nevolají API přímo** — vždy přes store nebo api/ modul
7. **Každý modul řeší 4 stavy:** loading, empty, error, data
8. **TypeScript typy musí odpovídat backend schemas** — přidáš pole v backendu → přidej v types/

## Reuse First — NEVER Duplicate

Before creating ANY new component, composable, or utility:

1. Check `components/ui/` — Button, Input, Select, Modal, DataTable, Tooltip, Spinner, DragDropZone already exist
2. Check `composables/` — useDialog, useResizeHandle, useKeyboardShortcuts already exist
3. Check `utils/formatters.ts` — formatCurrency, formatNumber, formatDate, formatPrice already exist
4. Check `components/TypeAheadSelect.vue` — autocomplete select already exists

**If a similar component exists, extend it via props/slots. Do NOT create a parallel version.**

## Performance Rules

1. **Lazy-load heavy libraries** — `const lib = await import('heavy-lib')` not top-level import
2. **Virtualize lists > 50 items** — use `@tanstack/vue-virtual`
3. **Debounce all search/filter inputs** — 300ms minimum
4. **Component < 500 LOC** — split if larger
5. **No deep watchers** — `watch(obj, fn, { deep: true })` on large objects kills performance
6. **v-for always with :key** — unique, stable keys
7. **Clean up on unmount** — event listeners, timers, intervals

## Completion Checklist

Before declaring your work done, verify ALL of these:

### Correctness
- [ ] Zero `any` types in TypeScript
- [ ] Zero hardcoded colors (hex/rgb/hsl) — all from CSS variables
- [ ] Zero inline styles (`style=""`)
- [ ] Zero `!important` in CSS
- [ ] All interactive elements have `data-testid`
- [ ] All user-visible text is in Czech
- [ ] Icons use `ICON_SIZE` (18px) from `config/design.ts`
- [ ] API calls go through `api/` modules, not direct axios
- [ ] Error handling with `ui.showError()`
- [ ] Loading states with `ui.startLoading()/stopLoading()`
- [ ] Component uses `<script setup lang="ts">` and `<style scoped>`

### Reuse & Performance
- [ ] No duplicate of existing ui/ component or composable
- [ ] Heavy libraries dynamically imported
- [ ] Lists > 50 items use virtualization
- [ ] Search/filter inputs debounced (300ms)
- [ ] Component under 500 LOC (or justified split)
- [ ] No deep watchers on arrays/objects

### Verification
- [ ] Build passes: `npm run build -C frontend`
- [ ] Lint passes: `npm run lint -C frontend`
