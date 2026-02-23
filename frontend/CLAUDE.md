# Frontend Rules — Gestima

> Auto-načten při práci na `frontend/` souborech.
> Globální pravidla (workflow, architektura, git) viz root `CLAUDE.md`.

---

## Reusable Components — USE BEFORE CREATING NEW

**Před vytvořením JAKÉKOLI nové komponenty zkontroluj tento seznam. Duplicita = CRITICAL violation.**

### UI Components (`components/ui/`)

| Component | Purpose | Key Props |
|---|---|---|
| **Button.vue** | Multi-variant button | `variant` (primary/secondary/danger/ghost), `size`, `loading`, `disabled` |
| **Input.vue** | Text/number/password input with validation | `modelValue`, `label`, `type`, `error`, `hint`, `mono` |
| **Select.vue** | Native select dropdown | `modelValue`, `options` ({value,label}[]), `placeholder`, `error` |
| **Modal.vue** | Dialog modal (Teleport) | `modelValue`, `title`, `size` (sm/md/lg/xl), slots: header/default/footer |
| **FormTabs.vue** | Tab layout for forms | `tabs` (string[]), `modelValue` (active index), `vertical`, `keepAlive` |
| **DataTable.vue** | Full data grid (sort/select/paginate) | `data`, `columns` (Column[]), `loading`, `selectable`, `pagination` |
| **ColumnChooser.vue** | Column visibility toggle | `columns`, `storageKey` (localStorage persistence) |
| **AlertDialog.vue** | Alert modal (via useDialog) | Driven by `useDialog().alert()` — promise-based |
| **ConfirmDialog.vue** | Confirm modal (via useDialog) | Driven by `useDialog().confirm()` — returns boolean |
| **ToastContainer.vue** | Toast notifications | Driven by `useUiStore().showSuccess/Error/Warning()` |
| **Tooltip.vue** | Cursor-following tooltip | `text`, `delay` |
| **DragDropZone.vue** | File upload drag & drop | `accept`, `maxSize`, `label`, emits `upload` |
| **Spinner.vue** | Loading spinner | `size`, `text`, `inline` |
| **CuttingModeButtons.vue** | LOW/MID/HIGH toggle | `mode`, `disabled`, emits `change` |
| **CoopSettings.vue** | Subcontractor settings panel | `isCoop`, `coopPrice`, `coopDays`, `disabled` |
| **TypeAheadSelect.vue** | Autocomplete with keyboard | `options`, `modelValue`, `placeholder`, `maxVisible` |

### Composables (`composables/`)

| Composable | Purpose | Returns |
|---|---|---|
| **useDialog()** | Confirm/alert dialogs (promise-based) | `confirm(options)`, `alert(options)` |
| **useDarkMode()** | Theme toggle | `isDark`, `toggle()`, `setTheme()` |
| **useResizeHandle()** | Panel resize drag | `size`, `isDragging`, `startResize()`, `resetSize()` |
| **useResizablePanel()** | Split-pane resize | `panelWidth`, `isDragging`, `startResize()` |
| **useKeyboardShortcuts()** | Keyboard shortcut system | `registerShortcut()`, `unregisterAll()` |
| **usePartLayoutSettings()** | Horizontal/vertical layout | `layoutMode`, `toggleLayout()` |
| **useLinkedWindowOpener()** | Cross-module window linking | `openLinked(module, title)` |
| **usePrefetch()** | Background data preload | `prefetchAll()` |

### Utilities (`utils/`)

| Function | Purpose | Example |
|---|---|---|
| `formatCurrency(value)` | Czech currency format | `1 234,50 CZK` |
| `formatNumber(value)` | Czech number format | `1 234,5` |
| `formatDate(value)` | Czech date format | `21. 2. 2026` |
| `formatPrice(value)` | Price with 2 decimals | `1 234,50` |
| `partStatusLabel(status)` | Status → Czech label | `active` → `Aktivní` |
| `partSourceLabel(source)` | Source → Czech label | `manual` → `Manuální` |

### Directives

| Directive | Purpose | Usage |
|---|---|---|
| `v-select-on-focus` | Select all text on input focus | `<input v-select-on-focus />` |

---

## Design System v2 (design-system.css v6.0) — MANDATORY

**Source of truth:** `tiling-preview-v3.html` (visual) + `design-system.css` v6.0 (tokens)
**Font:** DM Sans (not Inter). Dark-only, no light mode.
**51 tokens total:** 35 v2 + 16 app-specific. NO legacy aliases.

```css
/* ═══ V2 TOKENS — this is EVERYTHING ═══ */

/* Brand */    --red  --red-glow  --red-dim  --red-10  --red-20
/* Money */    --green  --green-10  --green-15
/* Surfaces */ --base  --ground  --surface  --raised  --glass
/* Text */     --t1  --t2  --t3  --t4
/* Borders */  --b1  --b2  --b3
/* Status */   --ok  --warn  --err
/* Linking */  --la  --lb
/* Font */     --font ('DM Sans')  --mono ('JetBrains Mono')
/* Size */     --fs (12px)  --fsl (11px)
/* Spacing */  --gap (3px)  --pad (8px)  --r (7px)  --rs (4px)
/* Motion */   --ease  --spring

/* App-specific (charts + linking groups) */
--chart-material  --chart-machining  --chart-setup  --chart-cooperation
--chart-revenue  --chart-expenses  --chart-profit  --chart-wages
--chart-depreciation  --chart-energy  --chart-tools
--link-group-red  --link-group-blue  --link-group-green
--link-group-yellow  --link-group-neutral
```

**Co v2 NETOKENIZUJE (použij literál):**
- Font-weight: `400`, `420` (body), `500`, `600`, `700`
- Font-size — tokenizované: viz tabulka výše. Literály OK: `8px`, `8.5px`, `15px`, `16px`, `20px`, `24px`, `28px`, `48px` (one-off layout hodnoty)
- Spacing: `2px`, `4px`, `6px`, `8px`, `12px`, `16px`, `20px`, `24px`
- Shadows: `0 4px 12px rgba(0,0,0,0.5)`
- Transitions: `all 100ms var(--ease)`, `all 150ms var(--ease)`
- Radius (mimo --r/--rs): `8px`, `12px`, `99px`
- Focus: `rgba(255,255,255,0.5)` (outline), `rgba(255,255,255,0.03)` (bg)

**Pokud potřebuješ token který není v seznamu — ZEPTEJ SE, nevymýšlej.**

---

## Katalog UI prvků — MANDATORY

**Source of truth:** `frontend/tiling-preview-v3.html` → sekce `#styleguide`

### Pravidlo: Nový prvek = přidat do katalogu

Když vytváříš nový UI prvek nebo komponentu:
1. **Zkontroluj katalog** — prvek možná již existuje
2. **Použij existující vzor** — kopíruj HTML/CSS z `#styleguide` sekce
3. **Pokud prvek v katalogu chybí** — přidej ho do `tiling-preview-v3.html#styleguide`

Katalog obsahuje: Typography, Tables (.ot/.bt), Badges, Buttons, Inputs, Panel anatomy, KPI cards, Status indicators, Save actions.

### Save action vzor — JEDNOTA (SSoT)

**Vždy jedno řešení.** Pro uložení/potvrzení:
- Inline editace v tabulce → **ikona Check** (`.icon-btn` s `<Check />`)
- Formuláře/dialogy → **`.btn-primary` s textem "Uložit"**
- Nikdy míchat vzory na stejném místě

---

## Component Rules — ALWAYS

1. **`<script setup lang="ts">`** — žádné Options API, žádné class components
2. **`<style scoped>`** vždy
3. **Design tokeny only** — nikdy hardcode barvy:
   ```css
   /* SPRÁVNĚ */  color: var(--t1);  background: var(--surface);  border: 1px solid var(--b2);
   /* ŠPATNĚ */   color: #ffffff;  background: #1a1a1a;  color: var(--text-primary);
   ```
4. **`data-testid`** na každém interaktivním elementu — tlačítka, inputy, linky, řádky
5. **Ikony:** Lucide Vue Next, velikost přes `ICON_SIZE` konstantu (18px) z `config/design.ts`
6. **České popisky** — veškerý text viditelný uživateli v češtině
7. **Limity velikosti:** Atomic (<200 LOC), Molecular (<500 LOC), Organism (<1000 LOC)

---

## CSS/Styling — ALWAYS

1. **Tailwind utilities** pro layout (flex, grid, gap, padding, margin)
2. **CSS variables** z design-system.css pro barvy, bordery, backgrounds
3. **Nikdy nové CSS soubory** — rozšiř existující
4. **Nikdy inline `style=""`** — použij třídy nebo CSS variables
5. **Button varianty:** `.btn-primary`, `.btn-secondary`, `.btn-destructive` (všechny ghost/transparent)
6. **Focus:** vždy viditelný — `:focus-visible { outline: 2px solid rgba(255,255,255,0.5) }` (BÍLÝ, nikdy modrý)
7. **`@container` queries** — nikdy `@media` v komponentách
8. **Font scale — VŽDY používej tokeny:**
   ```
   --fs  (12px)   standard body, table cells, module picker items
   --fsl (11px)   panel headers, DataTable th
   --fsx (10.5px) tabs, action buttons, status bar, login labels
   --fsm (10px)   table th (uppercase), ribbon labels, badges, KPI labels
   --fss (9px)    KPI units, shortcut keys, meta text, avatar
   --fsh (14px)   pricing values, section headers, modal titles
   ```
   NIKDY hardcoded px pro tyto velikosti — hook [ERROR 8] zastaví commit.

---

## Pinia Stores — ALWAYS

```typescript
export const useXyzStore = defineStore('xyz', () => {
  const items = ref<Xyz[]>([])
  const loading = ref(false)
  // ... actions and computeds
  return { items, loading, fetchItems, ... }
})
```

- **Loading state:** `useUiStore().startLoading()` / `stopLoading()` counter pattern
- **Error handling:** `try/catch` s `useUiStore().showError(message)`
- **Nikdy** nemutuj store state z komponent — vždy přes store actions

---

## API Calls — ALWAYS

- **Existující api/ moduly** — nikdy axios přímo z komponent
- **`apiClient`** (regular) nebo **`adminClient`** (admin) z `api/client.ts`

```typescript
try {
  const result = await partsApi.createPart(data)
  ui.showSuccess('Díl vytvořen')
} catch (error) {
  if (error instanceof OptimisticLockErrorClass) {
    ui.showError('Data byla změněna jiným uživatelem. Obnovte stránku.')
  } else {
    ui.showError('Chyba při vytváření dílu')
  }
}
```

---

## UI/UX Patterns — APPROVED (follow exactly)

**Visual reference:** `frontend/tiling-preview-v3.html` — otevři v browseru pro živý preview.

| Pattern | Pravidlo |
|---------|----------|
| **Buttons** | Ghost only. 3 varianty: `.btn-primary`, `.btn-secondary`, `.btn-destructive`. Žádná filled tlačítka. |
| **Icon buttons** | `.icon-btn` default grey → hover white. `.icon-btn-brand` pro add/edit, `.icon-btn-danger` pro delete. |
| **Badges** | Monochrome background + colored dot. `.badge` + `.badge-dot-ok/error/warn/neutral/brand`. |
| **Focus ring** | BÍLÝ (`rgba(255,255,255,0.5)`). Nikdy modrý, červený ani brand. |
| **Selected rows** | Neutral white overlay (`var(--b1)`). Nikdy brand-tinted. |
| **Edit mode** | `var(--raised)` + `var(--b3)`. NE červený border. |
| **Toasts** | Monochrome body + colored left border (`.toast-ok/error/warn`). |
| **Status colors** | POUZE v: badge dots, toast left borders, chart segments. Nikdy jako button/badge background. |
| **Numbers & prices** | `font-family: var(--mono);` + `.col-num` nebo `.col-currency` (right-align, nowrap). |
| **Layout** | `@container` queries, NE `@media`. Fluid heights, NE fixed px heights. |

---

## NEVER do this (Frontend)

**ERRORS — validate-frontend-v2.sh blokuje edit:**
- ❌ Hardcoded hex barvy v .vue/.css [HOOK: ERROR 1]
- ❌ `any` typ v TypeScriptu [HOOK: ERROR 2]
- ❌ `!important` v CSS [HOOK: ERROR 3]
- ❌ `<style>` bez `scoped` [HOOK: ERROR 4]
- ❌ Options API (`export default {}`) [HOOK: ERROR 5]
- ❌ Legacy tokeny (`--bg-surface`, `--text-primary`, `--brand`, `--space-*`) [HOOK: ERROR 6]
- ❌ Hardcoded `font-size: NNpx` pro tokenizované hodnoty (9/10/10.5/11/12/12.5/13/14px) [HOOK: ERROR 8]

**WARNINGS — hook informuje, neblokuje:**
- ⚠️ `@media` queries v komponentách — prefer `@container` [HOOK: WARN 7]
- ⚠️ Inline `style=""` atributy [HOOK: WARN 8]
- ⚠️ Import axios přímo v komponentách [HOOK: WARN 9]
- ⚠️ Business výpočty na frontendu [HOOK: WARN 10]

**Další pravidla (bez hooku):**
- ❌ Vynechat `data-testid` na interaktivních elementech
- ❌ Vynechat error handling na API calls
- ❌ Ignorovat existující component patterns — kopíruj je
- ❌ Přidávat npm packages bez ptaní se
- ❌ Filled/colored buttons (ghost only)
- ❌ Colored badge backgrounds (monochrome + dot only)
- ❌ Modrý/červený focus ring (white only)
- ❌ Červený border na edit mode (použij `--b3`)
- ❌ Emoji v UI (použij Lucide ikony)

---

## Frontend Performance — MANDATORY

**Budgets:**
| Metrika | Limit |
|---|---|
| Frontend initial load (LCP) | < 2s |
| Vue component render | < 16ms (60fps) |
| Bundle chunk size | < 600KB |
| Component LOC | < 500 (split if larger) |

**Pravidla:**
1. **Lazy-load routes** — všechny routes: `() => import('@/views/...')`
2. **Lazy-load heavy modules** — `defineAsyncComponent()` pro těžké panel moduly
3. **Lazy-load heavy libraries** — PDF.js, Three.js via dynamic `import()`:
   ```typescript
   const pdfjsLib = await import('pdfjs-dist')  // ✅ SPRÁVNĚ
   import * as pdfjsLib from 'pdfjs-dist'        // ❌ ŠPATNĚ
   ```
4. **Virtualize long lists** — `@tanstack/vue-virtual` pro listy > 50 položek
5. **Debounce user input** — search, filters, resize: min 300ms
   ```typescript
   let timer: ReturnType<typeof setTimeout>
   function onSearch(query: string) {
     clearTimeout(timer)
     timer = setTimeout(() => store.fetchFiltered(query), 300)
   }
   ```
6. **v-for vždy s :key** — unikátní klíč na každém list renderu
7. **Cleanup watchers** — `onUnmounted()` nebo nechej `<script setup>` handle it
8. **No deep watchers** na velkých objektech — použij specifické property watchers

---

## Testing — E2E Patterns

```typescript
test('should create part', async ({ page }) => {
  await login(page)
  await setupWindowsView(page)
  await openModuleViaMenu(page, 'Part Main')
  await waitForModuleLoad(page)
  // ... assertions with data-testid selectors
})
```

- Selectory = `data-testid` (ne CSS classes)
- Použij helpers: `login`, `logout`, `generatePartData`, `openModuleViaMenu`, `waitForModuleLoad`, `setupWindowsView`

---

## Import Order (TypeScript/Vue)

```typescript
// 1. Vue core
import { ref, computed, watch, onMounted } from 'vue'
// 2. Third-party
import { useRouter } from 'vue-router'
import { SomeIcon } from 'lucide-vue-next'
// 3. Stores, composables
import { useUiStore } from '@/stores/ui'
import { useDialog } from '@/composables/useDialog'
// 4. API, types, utils
import * as partsApi from '@/api/parts'
import type { Part, PartCreate } from '@/types/part'
import { formatCurrency } from '@/utils/formatters'
// 5. Components
import Button from '@/components/ui/Button.vue'
// 6. Constants
import { ICON_SIZE } from '@/config/design'
```
