# HANDOFF: Tiling UI Rewrite (Option B)

> **Projekt:** GESTIMA -- CNC cost calculator
> **Stack:** FastAPI + Vue 3 + SQLite. Czech UI labels, English code.
> **Datum:** 2026-02-22
> **Rozhodnutí:** Complete new module rendering with tiling architecture (Option B)

---

## Kontext rozhodnutí

After 4 failed attempts at wrapping old floating-window components in new tiling shells, the user chose **Option B: complete rewrite of module UI rendering**. The fundamental problem is that old components (`OperationsDetailPanel`, `PricingDetailPanel`, etc.) carry their own styling inherited from the floating-window design. This clashes irreconcilably with the new tiling glassmorphism aesthetic.

**Option B means:**
- Rewrite all module UI rendering to match `tiling-preview-v2.html` exactly
- Keep all business logic -- API calls, Pinia stores, TypeScript types stay identical
- Create new self-contained panel components that render data directly using v2 CSS classes
- Old module components become unused and can be deleted once replacements are verified

---

## Vizuální reference

The **definitive** design reference is:

```
frontend/tiling-preview-v2.html   (871 lines, standalone HTML)
```

Open it in a browser to see the exact visual target. A v3 exists but is experimental -- v2 is THE approved design.

---

## Hotová infrastruktura (KEEP -- nemeknout)

These files are DONE and working. Do NOT modify them unless there is a specific bug:

### Typy a Store

| File | LOC | Purpose |
|------|-----|---------|
| `frontend/src/types/workspace.ts` | 40 | `LinkingGroup`, `WorkspaceType`, `LayoutPreset`, `PartDetailTab`, `SavedWorkspaceView` |
| `frontend/src/stores/workspace.ts` | 220 | Pinia store: activeWorkspace, layoutPreset, activePartTab, savedViews, localStorage persistence, migration from old windows store |

### Tiling komponenty

| File | LOC | Purpose |
|------|-----|---------|
| `frontend/src/components/tiling/TilingWorkspace.vue` | 166 | Main container. Renders active workspace. Boot sequence. FAB. Keyboard shortcuts Cmd+1-4. |
| `frontend/src/components/tiling/BootSequence.vue` | 363 | CNC boot animation (toolpath SVG traces, laser sweep, logo reveal) |
| `frontend/src/components/tiling/CncBackground.vue` | 332 | Animated CNC grid, breathing orbs, toolpath SVG, floating coordinates, grain texture |
| `frontend/src/components/tiling/FabButton.vue` | 237 | FAB + module picker popup. Switches workspace via emit. |
| `frontend/src/components/tiling/GlassPanel.vue` | 481 | Glassmorphism panel wrapper with corner marks, context stripes, inner backgrounds |
| `frontend/src/components/tiling/WorkspaceSwitcher.vue` | 76 | Horizontal tab strip for workspace switching (header) |
| `frontend/src/components/tiling/LayoutPresetSelector.vue` | 70 | Layout preset chips: Standardni/Porovnani/Horizontalni/Kompletni (header) |
| `frontend/src/components/tiling/PartWorkspace.vue` | 374 | CSS Grid with 4 presets, part list + detail coordination, dual context (red/green) |
| `frontend/src/components/tiling/PartDetailTabs.vue` | 1203 | Tab panel with header, ribbon, tab content. **THIS NEEDS REWRITE** -- currently wraps old module components |

### Layout komponenty

| File | Purpose |
|------|---------|
| `frontend/src/components/layout/AppHeader.vue` | 36px compact header with glassmorphism, WorkspaceSwitcher + LayoutPresetSelector |
| `frontend/src/components/layout/AppFooter.vue` | 22px status bar with glassmorphism, live clock, calendar popup |

### Routing

```typescript
// frontend/src/router/index.ts
{ path: '/', redirect: '/workspace' }
{ path: '/workspace', name: 'workspace', component: () => import('@/components/tiling/TilingWorkspace.vue') }
{ path: '/windows', redirect: '/workspace' }  // legacy redirect
```

---

## Co je potreba prepsat (hlavni ukol)

### Problem: PartDetailTabs.vue

The current `PartDetailTabs.vue` (1203 LOC) has the correct header/ribbon/tab structure matching v2, BUT it imports and renders OLD module components in the tab content area:

```typescript
// Current imports in PartDetailTabs.vue that render OLD styling:
import OperationsDetailPanel from '@/components/modules/operations/OperationsDetailPanel.vue'
import MaterialInputSelectorV2 from '@/components/modules/operations/MaterialInputSelectorV2.vue'
import PricingDetailPanel from '@/components/modules/pricing/PricingDetailPanel.vue'
import PartDrawingWindow from '@/components/modules/parts/PartDrawingWindow.vue'
import ProductionHistoryPanel from '@/components/modules/production/ProductionHistoryPanel.vue'
```

These old components carry their own `<style scoped>` from the floating-window era, creating visual mismatches.

### Moduly k prepsani

For each module: create a NEW Vue component that renders data using v2 CSS classes. Keep ALL store/API calls identical -- only change the template and style.

| Module | Old Component | LOC | Store/API Dependencies | Priority |
|--------|--------------|-----|----------------------|----------|
| **Operations** | `OperationsDetailPanel.vue` | 545 | `operationsStore.loadOperations`, `operationsStore.updateOperation`, `operationsStore.addOperation`, `operationsStore.deleteOperation`, VueDraggable for reorder | P1 -- most visible |
| **Pricing** | `PricingDetailPanel.vue` | 1003 | `batchesStore.setPartContext`, `batchesStore.createBatch`, `batchesStore.deleteBatch`, `batchesStore.recalculateBatches` | P2 |
| **Parts List** | `PartListPanel.vue` | 608 | `partsStore.fetchParts`, `partsStore.fetchMore`, `partsStore.setSearchQuery`, virtual scroll | P3 |
| **Material** | `MaterialInputSelectorV2.vue` | 1276 | `materialsStore.loadMaterialInputs`, `materialsStore.createMaterialInput`, `parseMaterialDescription` API | P4 |
| **Drawing** | `PartDrawingWindow.vue` | 346 | `drawingsApi.getDrawingUrl`, `partsStore` | P5 |
| **Production** | `ProductionHistoryPanel.vue` | 389 | `getProductionRecords`, `createProductionRecord`, `deleteProductionRecord` APIs | P6 |
| **Material List** | `MaterialInputList.vue` | 447 | `materialsStore`, emit events to parent | P6 |

### Vyzadovane tiling features (nad ramec vizualniho prepisu)

The user explicitly wants these tiling capabilities:

1. **Resizable panels** -- drag dividers between panels to resize
2. **Independent panels** -- each panel has its own part context (not synchronized)
3. **Free module combination** -- user can put parts + quotes, pricing + drawing in one view
4. **Drag-and-drop tabs** between panels -- move Operations tab to another panel
5. **MasterAdmin and TimeVision as fullscreen modules only** (already implemented in TilingWorkspace.vue)

---

## v2 Design Tokens

From `tiling-preview-v2.html` `:root` -- these are the design tokens the new components must use:

```css
/* Brand -- the ONE chromatic accent */
--red: #E53935;
--red-glow: rgba(229,57,53,0.15);
--red-dim: rgba(229,57,53,0.08);
--red-10: rgba(229,57,53,0.10);
--red-20: rgba(229,57,53,0.20);

/* Money/Pricing -- the only other chromatic color */
--green: #22c55e;
--green-10: rgba(34,197,94,0.10);
--green-15: rgba(34,197,94,0.15);

/* Surfaces -- pure neutral, no blue cast */
--base: #08080a;
--ground: #0e0e10;
--surface: rgba(18,18,20,0.88);
--raised: rgba(26,26,28,0.92);
--glass: rgba(20,20,22,0.65);

/* Text -- high contrast */
--t1: #ededf0;       /* primary text */
--t2: #cdcdd0;       /* body text */
--t3: #8e8e96;       /* secondary/label text */
--t4: #5c5c64;       /* muted/disabled text */

/* Borders */
--b1: rgba(255,255,255,0.06);
--b2: rgba(255,255,255,0.10);
--b3: rgba(255,255,255,0.15);

/* Status */
--ok: #34d399;
--warn: #fbbf24;
--err: #f87171;

/* Typography */
--font: 'DM Sans';
--mono: 'JetBrains Mono';
--fs: 12px;
--fsl: 11px;   /* font-size label */

/* Spacing */
--gap: 3px;    /* between panels */
--pad: 8px;    /* inner padding */
--r: 7px;      /* border-radius panel */
--rs: 4px;     /* border-radius small */
```

**IMPORTANT:** These v2 tokens need to be mapped to the existing `design-system.css` variables or added as new variables. The existing codebase uses variables like `--bg-surface`, `--text-primary`, `--brand-hover`, etc. The current tiling components already use the existing design-system variables (see GlassPanel.vue, PartDetailTabs.vue). New components should follow the same pattern -- use `design-system.css` variables, NOT hardcoded v2 tokens.

### Mapovani v2 tokenu na design-system.css

| v2 Token | design-system.css equivalent |
|----------|------------------------------|
| `--t1` | `var(--text-primary)` |
| `--t2` | `var(--text-body)` or `var(--text-secondary)` |
| `--t3` | `var(--text-tertiary)` |
| `--t4` | `var(--text-disabled)` |
| `--b1` | `rgba(255, 255, 255, 0.06)` or `var(--border-subtle)` |
| `--b2` | `rgba(255, 255, 255, 0.10)` or `var(--border-default)` |
| `--b3` | `rgba(255, 255, 255, 0.15)` |
| `--red` | `var(--brand-hover)` |
| `--green` | `var(--palette-success)` |
| `--ok` | `var(--status-ok)` |
| `--warn` | `var(--status-warn)` |
| `--err` | `var(--status-error)` |
| `--surface` | `var(--bg-surface)` with color-mix |
| `--raised` | `var(--bg-raised)` |
| `--base` | `var(--bg-base)` |
| `--mono` | `var(--font-mono)` |

---

## Klicove v2 CSS tridy (z preview)

These are the CSS classes/patterns from `tiling-preview-v2.html` that the new components should replicate:

### Panel structure
- `.pnl` -- panel container (glassmorphism, corner marks) -- already implemented as `GlassPanel.vue`
- `.ph` -- panel header 28px (title + tabs + maximize/close)
- `.ptab` -- tab buttons (10.5px, colored dot when active)
- `.pb` -- panel body (flex:1, overflow-y auto)

### Ribbon (info strip)
- `.rib` -- ribbon container (6px padding, subtle bg, bottom border)
- `.rib-r` -- ribbon row (flex, center, gap 10px)
- `.rib-i` -- ribbon info item (label + value)
- `.rib-l` -- ribbon label (10px, uppercase, t4)
- `.rib-v` -- ribbon value (12px, t1)
- `.rib-v.m` -- monospace variant
- `.bdg` -- badge (pill, 10px, b1 bg, dot + label)
- `.rib-kpis` -- KPI cards row
- `.rib-kpi` -- KPI card (padding 3px 7px, b1 bg, rounded)
- `.kl` / `.kv` / `.ku` -- KPI label/value/unit (value in green for money)
- `.acts` / `.act` -- action buttons (ghost, 10.5px, b1 border)
- `.act.brand` -- brand action (red border, red text)

### Parts list
- `.srch` -- search input with embedded magnifying glass SVG icon
- `.plist` -- parts list (ul, no list-style)
- `.pi` -- part item (flex, 28px min-height, bottom border)
- `.pi.sel` -- selected part (red-dim bg + 2px red left stripe via ::after)
- `.pn` -- part number (mono, 12px, t1)
- `.pm` -- part name (12px, t3, ellipsis)
- `.pd` -- status dot (5px, round)
- `.spark` -- sparkline SVG (30x11px, neutral t4 stroke)

### Operations table
- `.ot` -- operations table (full width, collapse)
- `.ot thead` -- sticky header (bg rgba(255,255,255,0.025))
- `.ot th` -- header cell (10px, uppercase, t4)
- `.ot td` -- body cell (12px)
- `.ot td.r` -- right-aligned mono cell
- `.ot tbody tr.sel td` -- selected row (red-dim bg)
- `.tb` -- time badge (pill, mono 10px, b1 bg, t2)
- `.tb .d` -- time badge dot (3px)
- `.tb.s .d` -- setup time dot (red)
- `.tb.o .d` -- operation time dot (green/ok)

### Pricing
- `.pr-w` -- pricing wrapper (padding, flex column, gap 7px)
- `.pr-row` -- pricing cards row
- `.prc` -- pricing card (b1 bg, rounded, label + value + unit)
- `.prc.price .v` -- price value in green
- `.ring-svg` -- ring chart (76x76 SVG with concentric arcs)
- `.ring-leg` / `.rli` / `.rld` / `.rlv` -- ring legend items
- `.bt` -- batch table (green-tinted header border)
- `.bt .c` -- currency cell (mono, right, green)

### Drawing
- `.drw` -- drawing container (subtle bg, b1 border, grid overlay, center crosshair circle)

### Grid layouts
```css
.tiles[data-l="std"] { grid-template-columns: 230px 1fr; }
.tiles[data-l="cmp"] { grid-template-columns: 210px 1fr 1fr 210px; }
.tiles[data-l="hor"] { grid-template-columns: 210px 1fr; grid-template-rows: 1fr 1fr; }
.tiles[data-l="qd"]  { grid-template-columns: 210px 1fr 1fr; grid-template-rows: 1fr 1fr; }
```

Already implemented in `PartWorkspace.vue` with `data-preset="standard|comparison|horizontal|complete"`.

---

## Backend -- BEZ ZMEN

The entire backend (FastAPI, models, routers, services, schemas) is unchanged. All API endpoints work. No backend changes needed for this task.

---

## Nemodifikovane frontend vrstvy

### Pinia Stores (all 14 files in `stores/`)

| Store | File | Used by |
|-------|------|---------|
| `usePartsStore` | `parts.ts` | Parts list, detail, operations |
| `useOperationsStore` | `operations.ts` | Operations table, AI estimation |
| `useBatchesStore` | `batches.ts` | Pricing, batch sets |
| `useMaterialsStore` | `materials.ts` | Material inputs, material list |
| `useQuotesStore` | `quotes.ts` | Quotes module |
| `usePartnersStore` | `partners.ts` | Partners module |
| `useFilesStore` | `files.ts` | Files module |
| `useTimeVisionStore` | `timeVision.ts` | TimeVision module |
| `useAuthStore` | `auth.ts` | Login, auth guards |
| `useUiStore` | `ui.ts` | Loading states, toasts |
| `useWindowContextStore` | `windowContext.ts` | Linking groups (imports LinkingGroup from types/workspace.ts) |
| `useWindowsStore` | `windows.ts` | OLD floating windows -- will be deleted in Phase 4 |
| `useWorkspaceStore` | `workspace.ts` | NEW tiling workspace state |

### API Modules (24 files in `api/`)

All API modules stay unchanged. Key ones for module rewrite:

| API Module | Used by |
|------------|---------|
| `parts.ts` | Parts list, detail |
| `operations.ts` | Operations CRUD |
| `batches.ts` | Pricing calculations |
| `materialInputs.ts` | Material inputs CRUD |
| `materials.ts` | Material catalog |
| `drawings.ts` | Drawing URLs |
| `productionRecords.ts` | Production history |
| `technology.ts` | AI technology generation |
| `time-vision.ts` | TimeVision estimations |

### Type Definitions (23+ files in `types/`)

All type definitions stay unchanged. They mirror backend Pydantic schemas.

### UI Components (`components/ui/`)

All existing UI components (Button, DataTable, Modal, FormTabs, Select, Input, etc.) remain available and should be used where appropriate within the new module renderers.

### Composables

All composables stay unchanged except:
- `useLinkedWindowOpener.ts` -- can be deleted (old floating window linking)

### Modules that render fullscreen (no rewrite needed)

- `MasterAdminModule.vue` -- renders fullscreen via TilingWorkspace.vue
- `TimeVisionModule.vue` -- renders fullscreen via TilingWorkspace.vue

---

## Implementacni strategie

### Phase 1: New Panel System + Design Tokens

1. Add any missing v2 design tokens to `design-system.css` (if not already covered by existing variables)
2. Create a universal `TilePanel.vue` component that can hold any module -- with header, tabs, body
3. Consider a resizable split system (CSS resize handles or a lightweight library like `splitpanes`)
4. Wire up independent panel contexts (each panel tracks its own `partId`)

### Phase 2: Rewrite Module Rendering (one at a time)

For each module:

1. **Read the old component** to understand what store/API calls it makes and what data it renders
2. **Create new component** in `components/tiling/modules/` (e.g., `TileOperations.vue`)
3. **Copy the store/API logic** from the old component's `<script setup>` verbatim
4. **Write new template** using v2 CSS classes (`.ot`, `.tb`, `.prc`, `.drw`, etc.)
5. **Write new `<style scoped>`** matching the v2 preview visual exactly
6. **Verify:** `npm run build -C frontend` and `npm run lint -C frontend` must pass

**Suggested order:**
1. Operations (most visible, defines the pattern)
2. Pricing (second most complex, ring chart)
3. Parts List (search + virtual scroll)
4. Drawing (simplest visual)
5. Material Input
6. Production History

### Phase 3: Tiling Features

1. **Independent panel contexts** -- each work panel tracks its own `partId` via a context map
2. **Tab drag-and-drop** between panels -- HTML5 drag API
3. **Free module combination** -- any module can be placed in any panel
4. **Resizable dividers** between panels

### Phase 4: Cleanup

Delete old components that have been fully replaced:

```
frontend/src/components/windows/FloatingWindow.vue
frontend/src/components/windows/Taskbar.vue
frontend/src/stores/windows.ts
frontend/src/composables/useLinkedWindowOpener.ts
```

And any old module components that are no longer imported anywhere.

---

## Kriticka pravidla (z CLAUDE.md -- hook-enforced)

These rules are enforced by git hooks and Claude Code hooks. Violations will block commits:

| Rule | Enforcement |
|------|-------------|
| No hardcoded hex colors -- use CSS variables | Hook-enforced |
| No `any` type in TypeScript | Hook-enforced |
| No `!important` in CSS | Hook-enforced |
| No `@media` queries in components -- use `@container` | Hook-enforced |
| `<style scoped>` always | Hook-enforced |
| No inline `style=""` attributes | Hook-enforced |
| No direct axios imports -- use `api/` modules | Hook-enforced |
| No Options API (`export default {}`) | Hook-enforced |
| No hardcoded `font-size: Npx` -- use `var(--text-*)` | Hook-enforced |

### Additional mandatory rules (self-enforced)
- `data-testid` on all interactive elements
- `<script setup lang="ts">` always
- Error handling on all API calls
- Czech labels for all user-visible text
- Build must pass: `npm run build -C frontend`
- Lint must pass: `npm run lint -C frontend`

### Povolene rgba vzory (projdou hooky)

The hooks allow these rgba patterns (brand and semantic colors):

```
rgba(0, ...          -- black
rgba(255, ...        -- white
rgba(153, 27, 27, ...  -- brand red (existing design system)
rgba(239, 68, 68, ...  -- danger red
rgba(229, 57, 53, ...  -- v2 brand red
rgba(34, 197, 94, ...  -- green
rgba(248, 113, 113, ... -- error hover
```

---

## Verifikace

After every module rewrite, run:

```bash
npm run build -C frontend    # Must pass with zero errors
npm run lint -C frontend     # Must pass
python3 gestima.py test      # Backend tests (should not be affected)
```

### Wire trace checklist

For each rewritten module, verify the complete data path:

```
1. Component renders → reads data from store/computed
2. Store/computed → populated by store action (e.g., operationsStore.loadOperations)
3. Store action → calls API module (e.g., api/operations.ts)
4. API module → calls backend endpoint (e.g., GET /api/operations?part_id=X)
5. User interaction (click/drag/input) → calls handler in component
6. Handler → calls store action → calls API → updates store → component re-renders
```

---

## Souborova struktura (navrh)

```
frontend/src/components/tiling/
  TilingWorkspace.vue          # EXISTING -- main container
  BootSequence.vue             # EXISTING
  CncBackground.vue            # EXISTING
  FabButton.vue                # EXISTING
  GlassPanel.vue               # EXISTING
  WorkspaceSwitcher.vue        # EXISTING
  LayoutPresetSelector.vue     # EXISTING
  PartWorkspace.vue            # EXISTING -- CSS Grid + coordination
  PartDetailTabs.vue           # REWRITE -- replace old module imports with new ones
  modules/                     # NEW directory for tiling-native module renderers
    TileOperations.vue         # NEW -- operations table (v2 .ot styling)
    TilePricing.vue            # NEW -- pricing cards + ring chart + batch table
    TilePartsList.vue          # NEW -- parts list with search + virtual scroll (if needed, or keep PartListPanel if it works visually)
    TileDrawing.vue            # NEW -- drawing viewer
    TileMaterial.vue           # NEW -- material input + parsing
    TileProduction.vue         # NEW -- production history table
    TileAI.vue                 # NEW -- TimeVision + ML calibration
```

Alternatively, the rewrite can happen in-place by modifying `PartDetailTabs.vue` to inline the rendering logic instead of importing old components. The trade-off is component size vs. import count.

---

## Uzitecne prikazy

```bash
# Start dev servers
python3 gestima.py dev

# Frontend only
cd frontend && npm run dev

# Build check (TypeScript + Vite)
npm run build -C frontend

# Lint check
npm run lint -C frontend

# Backend tests
python3 gestima.py test

# E2E tests (requires running dev servers)
npm run test:e2e -C frontend

# Search for component usage
grep -r "ComponentName" frontend/src/ --include='*.vue' --include='*.ts'

# Check if a store action is used
grep -r "operationsStore\." frontend/src/ --include='*.vue' --include='*.ts'
```

---

## Znama rizika

1. **Virtual scroll compatibility** -- the old `PartListPanel.vue` uses `@tanstack/vue-virtual` for the parts list. The new tiling panel has variable height. Verify virtual scroll works in the new container.

2. **VueDraggable in operations** -- operations reorder uses `vuedraggable`. This must be preserved in the new operations component.

3. **PDF.js in drawing viewer** -- `PartDrawingWindow.vue` uses dynamic `import('pdfjs-dist')`. The new drawing component must maintain this lazy loading.

4. **Material parser** -- `MaterialInputSelectorV2.vue` (1276 LOC) is the most complex module. Consider splitting it into sub-components during rewrite.

5. **Hook false positives** -- Some rgba values in v2 CSS may trigger the color hooks. Use the allowed patterns listed above or map to existing CSS variables.

6. **Component size** -- PartDetailTabs.vue is already 1203 LOC. If modules are inlined, it will exceed the 500 LOC limit. Better to extract into separate tile module components.
